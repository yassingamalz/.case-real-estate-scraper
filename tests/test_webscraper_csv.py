"""Offline CSV import tests; no browser/network needed."""
import argparse
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import case
from case_csv import read_csv_records

ROOT = Path(__file__).resolve().parents[1]
CFG = {**case.DEFAULT, "min_price_eur": 20000, "max_price_eur": 80000,
       "min_area_m2": 30, "areas": ["Reggio Emilia"]}


class CSVImportTests(unittest.TestCase):
    def test_example_csv_mapping_and_filtering(self):
        source = ROOT / "examples" / "webscraper_export_example.csv"
        raw, headers = read_csv_records(source)
        self.assertEqual(len(raw), 3)
        self.assertIn("link-href", headers)
        self.assertEqual(raw[0]["price"], "€ 79.000")
        self.assertIn("annunci/12345678", raw[0]["url"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results"
            with patch.object(case, "settings", return_value=CFG), \
                 patch.object(case, "OUTPUT_DIR", output):
                case.import_webscraper_csv(argparse.Namespace(
                    input=str(source), area="Reggio Emilia", site="immobiliare.it",
                    **{key + "_column": None for key in (
                        "url", "title", "price", "area", "address", "description", "start_url")}
                ))
                with (output / "listings.csv").open(encoding="utf-8-sig", newline="") as fh:
                    rows = list(csv.DictReader(fh))
                self.assertEqual(len(rows), 2)
                self.assertEqual(sorted(x["price_eur"] for x in rows), ["68000", "79000"])
                self.assertEqual(sorted(x["area_m2"] for x in rows), ["65", "70"])
                self.assertEqual(json.loads((output / "summary.json").read_text())["unique_home_count"], 2)

    def test_unknown_mapping_gives_helpful_error(self):
        source = ROOT / "examples" / "webscraper_export_example.csv"
        with self.assertRaisesRegex(ValueError, "not found"):
            read_csv_records(source, {"url": "wrong_column"})

    def test_relative_urls_and_utf8_semicolon(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "source.csv"
            source.write_text(
                "web-scraper-start-url;link-href;titolo;prezzo;superficie\n"
                "https://www.immobiliare.it/vendita-case/reggio-emilia/;/annunci/1234/;Casa;79000;65\n", encoding="utf-8")
            rows, _ = read_csv_records(source)
            self.assertEqual(rows[0]["url"], "https://www.immobiliare.it/annunci/1234/")
            self.assertEqual(rows[0]["title"], "Casa")

    def test_import_keeps_existing_when_zero_valid_links(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            source = folder / "source.csv"
            source.write_text("link-href,price,area\nhttps://invalid.example/item,79000,65\n")
            with patch.object(case, "settings", return_value=CFG), \
                 patch.object(case, "OUTPUT_DIR", folder / "results"):
                case.import_webscraper_csv(argparse.Namespace(
                    input=str(source), area="Reggio Emilia", site="immobiliare.it",
                    **{key + "_column": None for key in (
                        "url", "title", "price", "area", "address", "description", "start_url")}
                ))
                self.assertFalse((folder / "results" / "listings.csv").exists())


if __name__ == "__main__":
    unittest.main()

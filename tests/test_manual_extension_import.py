"""Offline integration test: manually exported Chrome JSON -> filtered CSV/dedup."""
import argparse
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import case


class ManualExportTests(unittest.TestCase):
    def test_import_deduplicates_and_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "export.json"
            payload = {
                "format": "case-visible-listings-v1",
                "site": "immobiliare.it",
                "page_url": "https://www.immobiliare.it/vendita-case/reggio-emilia/?prezzoMinimo=20000&prezzoMassimo=80000",
                "items": [
                    {"url": "https://www.immobiliare.it/annunci/123456/",
                     "title": "Bilocale Via Roma 10", "text": "Via Roma 10 € 79.000 70 m²"},
                    {"url": "https://www.immobiliare.it/annunci/123456/",
                     "title": "Bilocale Via Roma 10", "text": "Via Roma 10 € 79.000 70 m²"},
                    {"url": "https://www.immobiliare.it/annunci/987654/",
                     "title": "Bilocale", "text": "Bilocale € 95.000 70 m²"},
                ]
            }
            source.write_text(json.dumps(payload), encoding="utf-8")
            cfg = {**case.DEFAULT, "min_price_eur": 20000, "max_price_eur": 80000,
                   "min_area_m2": 30, "areas": ["Reggio Emilia"]}
            with patch.object(case, "OUTPUT_DIR", folder / "results"), patch.object(
                    case, "settings", return_value=cfg):
                case.import_json(argparse.Namespace(input=str(source), area="Reggio Emilia"))
                with (folder / "results" / "listings.csv").open(encoding="utf-8-sig", newline="") as f:
                    rows = list(csv.DictReader(f))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["price_eur"], "79000")
                case.import_json(argparse.Namespace(input=str(source), area="Reggio Emilia"))
                with (folder / "results" / "listings.csv").open(encoding="utf-8-sig", newline="") as f:
                    self.assertEqual(len(list(csv.DictReader(f))), 1)

    def test_wrong_area_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_text(json.dumps({
                "format": "case-visible-listings-v1", "site": "immobiliare.it",
                "page_url": "https://www.immobiliare.it/vendita-case/reggiolo/?prezzoMinimo=20000&prezzoMassimo=80000",
                "items": []
            }), encoding="utf-8")
            with patch.object(case, "OUTPUT_DIR", Path(directory) / "out"), patch.object(
                    case, "settings", return_value={
                        **case.DEFAULT, "min_price_eur": 20000,
                        "areas": ["Reggio Emilia"]
                    }):
                with self.assertRaisesRegex(ValueError, "Wrong location"):
                    case.import_json(argparse.Namespace(input=str(path), area="Reggio Emilia"))


if __name__ == "__main__":
    unittest.main()

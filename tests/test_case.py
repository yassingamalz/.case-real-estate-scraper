"""Offline unit tests. No portal requests, login, or browser required."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import case

ROOT = Path(__file__).resolve().parents[1]


class CaseTests(unittest.TestCase):
    def test_default_settings_and_filter_changes(self):
        data = case.settings()
        self.assertEqual(data["max_price_eur"], 80000)
        self.assertIn("Reggio Emilia", data["areas"])
        self.assertEqual(case.areas_from("Modena; Prato, Modena"), ["Modena", "Prato"])
        old = case.snapshot(data)
        data["max_price_eur"] = 85000
        self.assertNotEqual(old, case.snapshot(data))
        with self.assertRaises(ValueError):
            case.validate({**data, "pause_seconds": 0})

    def test_trusted_url_patterns(self):
        self.assertTrue(case.valid_listing_url("https://www.casa.it/immobili/123/"))
        self.assertTrue(case.valid_listing_url("https://www.immobiliare.it/annunci/123/"))
        self.assertTrue(case.valid_listing_url("https://www.idealista.it/immobile/123/"))
        self.assertFalse(case.valid_listing_url("https://evil.example/immobile/123/"))
        self.assertFalse(case.valid_listing_url("https://www.idealista.it/vendita-case/"))

    def test_card_extraction(self):
        text = "Bilocale in Via Esempio 10 € 79.000 65 m² 2 locali"
        row = case.parse_card({
            "url": "https://www.casa.it/immobili/123/",
            "title": "Bilocale in Via Esempio 10",
            "text": text,
        }, "casa.it", "Reggio Emilia")
        self.assertEqual(row["price_eur"], "79000")
        self.assertEqual(row["area_m2"], "65")
        self.assertIn("Esempio", row["address"])
        self.assertEqual(case.price_from("Prezzo € 79.000,00"), 79000)

    def test_dedup_does_not_merge_same_price_different_address(self):
        with (ROOT / "examples/sample_listings.csv").open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(case.match(rows[0], rows[1])[0], "MATCH")
        self.assertEqual(case.match(rows[0], rows[2])[0], "NONE")
        with tempfile.TemporaryDirectory() as d:
            before = case.OUTPUT_DIR
            try:
                case.OUTPUT_DIR = Path(d)
                result = case.dedup_rows(rows)
                self.assertEqual(result["input_ad_count"], 3)
                self.assertEqual(result["unique_home_count"], 2)
                self.assertEqual(result["collapsed_duplicate_ads"], 1)
                self.assertTrue((Path(d)/"unique_properties.csv").exists())
            finally:
                case.OUTPUT_DIR = before

    def test_review_when_address_is_missing(self):
        a = dict(site="casa.it", url="https://www.casa.it/immobili/111/",
                 city="Modena", title="Bilocale centro Modena", address="",
                 price_eur="75000", area_m2="62")
        b = dict(a, site="idealista.it", url="https://www.idealista.it/immobile/222/")
        self.assertEqual(case.match(a, b)[0], "REVIEW")


if __name__ == "__main__":
    unittest.main()

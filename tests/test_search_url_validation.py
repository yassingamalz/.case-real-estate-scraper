"""Regression tests: reject mismatched saved search URL filters without browser/network."""
import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import case


class SearchValidationTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "max_price_eur": 80000, "min_price_eur": 20000,
            "min_area_m2": 30, "areas": ["Reggio Emilia"],
            "max_pages_per_search": 2, "pause_seconds": 6,
            "include_auctions": True,
        }

    def test_rejects_reggiolo_saved_as_reggio_emilia(self):
        url = "https://www.immobiliare.it/vendita-case/reggiolo/?prezzoMinimo=20000&prezzoMassimo=80000"
        with self.assertRaisesRegex(ValueError, "Wrong location"):
            case.validate_search_url("immobiliare.it", "Reggio Emilia", url, self.cfg)

    def test_rejects_wrong_minimum_and_maximum(self):
        for query in ("prezzoMinimo=2000&prezzoMassimo=80000",
                      "prezzoMinimo=20000&prezzoMassimo=90000"):
            with self.subTest(query=query), self.assertRaisesRegex(ValueError, "conflicts"):
                case.validate_search_url(
                    "immobiliare.it", "Reggio Emilia",
                    "https://www.immobiliare.it/vendita-case/reggio-emilia/?" + query,
                    self.cfg)

    def test_valid_url_and_unknown_filter_warning(self):
        result = case.validate_search_url(
            "immobiliare.it", "Reggio Emilia",
            "https://www.immobiliare.it/vendita-case/reggio-emilia/"
            "?prezzoMinimo=20000&prezzoMassimo=80000",
            self.cfg)
        self.assertTrue(any("area" in v for v in result))

    def test_setup_rejects_bad_url_before_saving(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "case_searches.json"
            args = argparse.Namespace(
                site="immobiliare.it", area="Reggio Emilia",
                url="https://www.immobiliare.it/vendita-case/reggiolo/?prezzoMassimo=90000"
            )
            with patch.object(case, "SEARCHES_FILE", dest), patch.object(case, "settings", return_value=self.cfg):
                with self.assertRaises(ValueError):
                    case.setup(args)
                self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()

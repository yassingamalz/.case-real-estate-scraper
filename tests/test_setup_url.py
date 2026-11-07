"""Test URL-only search setup without opening Chrome."""
import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import case


class SetupUrlTests(unittest.TestCase):
    def test_save_url_without_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "saved.json"
            args = argparse.Namespace(
                site="immobiliare.it",
                area="Reggio Emilia",
                url="https://www.immobiliare.it/vendita-case/reggio-emilia/?prezzoMinimo=20000&prezzoMassimo=80000",
            )
            with patch.object(case, "SEARCHES_FILE", path):
                case.setup(args)
                entries = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["city"], "Reggio Emilia")
            self.assertFalse(entries[0]["authorized"])

    def test_external_or_root_url_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "saved.json"
            for url in (
                "https://malicious.example/listings/",
                "http://www.immobiliare.it/vendita-case/reggio-emilia/",
                "https://www.immobiliare.it/",
            ):
                with self.subTest(url=url), patch.object(case, "SEARCHES_FILE", path):
                    args = argparse.Namespace(site="immobiliare.it", area="Reggio Emilia", url=url)
                    with self.assertRaises(ValueError):
                        case.setup(args)
                    self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()

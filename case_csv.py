"""Read a Web Scraper (webscraper.io) CSV without network or browser access.

CSV field names are user-defined in the Web Scraper sitemap. Recognize common
names and allow explicit --*-column overrides. Never infer the page URL as the
property URL or combine unrelated multiple-value selectors.
"""
from __future__ import annotations

import csv
from pathlib import Path
import re
from urllib.parse import urljoin


ALIASES = {
    "url": (
        "link-href", "listing-href", "annuncio-href", "immobile-href",
        "property-href", "url_annuncio", "listing_url", "property_url",
        "url_immobile", "annuncio_url", "url", "href", "link",
    ),
    "title": ("title", "titolo", "nome", "name", "heading", "annuncio"),
    "price": ("price", "prezzo", "prezzo_eur", "price_eur", "costo", "importo"),
    "area": ("surface", "superficie", "area", "area_m2", "metratura", "mq", "m2"),
    "address": ("address", "indirizzo", "street", "via", "location", "indirizzo_immobile"),
    "description": ("description", "descrizione", "card_text", "scheda", "details", "text", "testo"),
    "start_url": ("web-scraper-start-url", "start_url", "search_url", "pagina_ricerca"),
}
MAX_FILE_BYTES = 20_000_000
MAX_ROWS = 10000
MAX_CELL_CHARS = 5000


def normalize_column(value: str) -> str:
    return re.sub(r"[\s_-]+", "_", str(value).casefold().strip())


def _select_column(headers: list[str], key: str, override: str | None) -> str | None:
    if override:
        if override not in headers:
            raise ValueError(f"Column '{override}' not found; available columns: {', '.join(headers)}")
        return override
    lookup = {normalize_column(h): h for h in headers}
    for name in ALIASES[key]:
        if normalize_column(name) in lookup:
            return lookup[normalize_column(name)]
    return None


def read_csv_records(path: str | Path, column_overrides: dict[str, str | None] | None = None) -> tuple[list[dict], list[str]]:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise ValueError(f"CSV file not found: {file_path}")
    if file_path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("CSV file exceeds the 20 MB safety limit.")
    columns = column_overrides or {}
    with file_path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8192)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(stream, dialect=dialect)
        headers = reader.fieldnames or []
        if not headers:
            raise ValueError("CSV is empty or has no header row.")
        if len(headers) > 100:
            raise ValueError("Too many CSV columns")
        mapping = {key: _select_column(headers, key, columns.get(key))
                   for key in ALIASES}
        if not mapping["url"]:
            raise ValueError(
                "No property-link column found. In Web Scraper create a link "
                "Element Attribute selector (href), name it 'link', or pass --url-column."
            )
        rows = []
        for i, raw in enumerate(reader):
            if i >= MAX_ROWS:
                raise ValueError("CSV exceeds 10,000 rows; split it into smaller files.")
            if None in raw:
                raise ValueError(f"Malformed CSV line {i+2}: unexpected additional columns")
            if any(value and len(value) > MAX_CELL_CHARS for value in raw.values()):
                raise ValueError(f"CSV line {i+2} contains an oversized field.")
            values = {key: (raw.get(field) or "").strip() if field else ""
                      for key, field in mapping.items()}
            source = values["start_url"]
            link = values["url"]
            if link and source:
                link = urljoin(source, link)
            values["url"] = link
            rows.append(values)
    return rows, headers

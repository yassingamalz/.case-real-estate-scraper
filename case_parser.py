"""Offline Italian real-estate listing parsing and conservative cross-portal matching.

These are heuristics for public listing-card text, not authoritative property data.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import re
import unicodedata

# Prefix and suffix are found independently so a civic number such as "10 €"
# never consumes the euro symbol belonging to "€ 79.000".
EURO_PREFIX = re.compile(r"€\s*(\d{1,3}(?:[., ]\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)")
EURO_SUFFIX = re.compile(r"(?<![\w])(\d{1,3}(?:[., ]\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*€")
AREA_RX = re.compile(r"\b(\d{2,4})\s*(?:m²|mq|m2)\b", re.I)
STREET_HEAD = re.compile(r"\b(via|viale|piazza|piazzale|corso|largo|strada|vicolo)\s+", re.I)
STOP_ADDRESS = re.compile(
    r"\s(?:[-–—|]\s+|€|\b(?:prezzo|bilocale|trilocale|quadrilocale|"
    r"appartamento|locali|locale|piano|ascensore|bagni|camere|camera|"
    r"vendita|asta|rata|terrazzo|balcone|m²|mq|m2)\b)", re.I)
FLOOR = re.compile(r"(?:[,\s-]+(?:\d+[°º]\s*)?piano\b.*|[,\s-]+\d+[°º]\s*piano\b.*)$", re.I)
CIVIC = re.compile(r"^(?P<name>.*?)(?:\s*,?\s+|,\s*)(?P<civic>\d{1,4}\s*[a-zA-Z]?(?:/\d{1,4}[a-zA-Z]?)?)$", re.I)


def number(value: object) -> int | None:
    """Convert EU/CSV numbers, including '79000.0', without multiplying by 10."""
    if value is None or isinstance(value, bool):
        return None
    raw = str(value).strip().replace('\u00a0', '').replace(' ', '').replace('€', '')
    if not raw or not re.fullmatch(r'[+-]?\d[\d.,]*', raw):
        return None
    if raw[0] in '+-':
        sign, raw = raw[0], raw[1:]
    else:
        sign = ''
    if '.' in raw and ',' in raw:
        # Rightmost punctuation is the decimal separator.
        decimal_sep = '.' if raw.rfind('.') > raw.rfind(',') else ','
        thousands_sep = ',' if decimal_sep == '.' else '.'
        raw = raw.replace(thousands_sep, '').replace(decimal_sep, '.')
    elif '.' in raw or ',' in raw:
        sep = '.' if '.' in raw else ','
        groups = raw.split(sep)
        if len(groups) > 2 and all(len(x) == 3 for x in groups[1:]):
            raw = ''.join(groups)
        elif len(groups) == 2 and len(groups[1]) == 3 and len(groups[0]) <= 3:
            raw = ''.join(groups)  # 79.000 -> 79000
        elif len(groups) == 2:
            raw = '.'.join(groups)  # 79000.0 -> 79000
        else:
            return None
    try:
        val = Decimal(sign + raw)
        if not val.is_finite() or val < 0:
            return None
        return int(val)
    except InvalidOperation:
        return None


def _prices(text: str) -> list[tuple[int, int, int]]:
    found = []
    for rx in (EURO_PREFIX, EURO_SUFFIX):
        for m in rx.finditer(text):
            n = number(m.group(1))
            if n is None or not 10000 <= n <= 30000000:
                continue
            context = text[max(0, m.start()-25):m.start()].rsplit("€", 1)[-1]
            # Ignore monthly installments, fees and generic deposits.
            if re.search(r"\b(?:rata|mutuo|affitto|canone|spese|deposito|cauzione)\s*(?:da|di)?\s*$", context, re.I):
                continue
            if re.match(r"\s*(?:/\s*)?(?:mese|mensil[ei])\b", text[m.end():], re.I):
                continue
            found.append((m.start(), m.end(), n))
    return sorted(set(found), key=lambda x: x[0])


def price_from(text: str) -> int | None:
    candidates = _prices(text)
    if not candidates:
        return None
    # Only infer a discount when there is an explicit price-reduction cue.
    for idx in range(len(candidates)-1):
        a, b = candidates[idx], candidates[idx+1]
        between = text[a[1]:b[0]]
        preceding = text[max(0, a[0]-35):a[0]]
        if a[2] > b[2] and re.search(r"[→➜⇒]|(?:ribassat[oa]|scontat[oa]|ridott[oa])", between + preceding, re.I):
            return b[2]
    return candidates[0][2]


def size_from(text: str) -> int | None:
    for m in AREA_RX.finditer(text):
        n = int(m.group(1))
        if 10 <= n <= 3000:
            return n
    return None


def address_from(text: str) -> str:
    """Extract a street/civic, excluding adjacent price, area, and apartment facts."""
    if not text:
        return ''
    head = STREET_HEAD.search(text)
    if not head:
        return ''
    rest = text[head.start():head.start()+110]
    rest = re.split(r"\s*€|\s*\d{2,4}\s*(?:m²|mq|m2)\b", rest, maxsplit=1, flags=re.I)[0]
    stop = STOP_ADDRESS.search(rest)
    if stop:
        rest = rest[:stop.start()]
    rest = FLOOR.sub('', rest)
    # A comma starts a city/location except when followed by a house number.
    rest = re.split(r",\s+(?=[A-Za-z])", rest, maxsplit=1)[0]
    rest = re.split(r"\s+\d+\s+(?:locali|camere|bagni)\b", rest, maxsplit=1, flags=re.I)[0]
    return re.sub(r"[,\s.:-]+$", "", rest).strip()[:90]


def pick_address(title: str, card_text: str) -> str:
    """Prefer explicit house number, then the title's address."""
    from_title, from_text = address_from(title), address_from(card_text[:350])
    if from_title and from_text:
        a, b = address_parts(from_title), address_parts(from_text)
        if a and b and a[:2] == b[:2] and not a[2] and b[2]:
            return from_text
    return from_title or from_text


def plain(text: str) -> str:
    text = unicodedata.normalize('NFKD', str(text).casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def address_parts(address: str) -> tuple[str, str, str] | None:
    clean = address_from(address)
    m = STREET_HEAD.match(clean)
    if not m:
        return None
    road_type = plain(m.group(1))  # Important: via != viale!
    road = clean[m.end():].strip(' ,.-')
    m2 = CIVIC.fullmatch(road)
    civic = ''
    if m2:
        road = m2.group('name').strip(' ,.-')
        civic = plain(m2.group('civic')).replace(' ', '')
    road = plain(road)
    return (road_type, road, civic) if road else None


def match(a: dict, b: dict) -> tuple[str, float, str]:
    if a.get('url') and a.get('url') == b.get('url'):
        return 'MATCH', 1.0, 'SAME_URL'
    if plain(a.get('city', '')) != plain(b.get('city', '')):
        return 'NONE', 0.0, 'DIFFERENT_CITY'
    if a.get('site') == b.get('site'):
        return 'NONE', 0.0, 'SAME_SITE_DIFFERENT_AD'
    pa, pb = number(a.get('price_eur')), number(b.get('price_eur'))
    ma, mb = number(a.get('area_m2')), number(b.get('area_m2'))
    if any(v is None for v in (pa, pb, ma, mb)):
        return 'NONE', 0.0, 'INSUFFICIENT_DETAILS'
    pdiff = abs(pa-pb) / max(pa, pb, 1)
    mdiff = abs(ma-mb) / max(ma, mb, 1)
    aa, ab = address_parts(a.get('address', '')), address_parts(b.get('address', ''))
    if aa and ab:
        if aa[:2] != ab[:2]:
            return 'NONE', 0.0, 'DIFFERENT_STREET'
        if aa[2] and ab[2] and aa[2] != ab[2]:
            return 'NONE', 0.0, 'DIFFERENT_HOUSE_NUMBER'
        if aa[2] and ab[2]:
            if pdiff <= .05 and mdiff <= .15:
                return 'MATCH', .93, 'SAME_ADDRESS_PRICE_SIZE'
            if pdiff <= .08 and mdiff <= .35:
                return 'REVIEW', .70, 'SAME_ADDRESS_DIFFERENT_DETAILS'
            return 'NONE', 0.0, 'DIFFERENT_PROPERTY_DETAILS'
        # Same street without a complete civic is not enough to merge apartments.
        if pdiff <= .05 and mdiff <= .15:
            return 'REVIEW', .66, 'SAME_STREET_MISSING_CIVIC'
        return 'NONE', 0.0, 'INCOMPLETE_ADDRESS_AND_DIFFERENT_DETAILS'
    title_sim = SequenceMatcher(None, plain(a.get('title', '')),
                                plain(b.get('title', ''))).ratio()
    if pdiff <= .02 and mdiff <= .05 and title_sim >= .8:
        return 'REVIEW', .67, 'SIMILAR_TITLE_PRICE_SIZE_VERIFY_ADDRESS'
    return 'NONE', 0.0, 'INSUFFICIENT_EVIDENCE'

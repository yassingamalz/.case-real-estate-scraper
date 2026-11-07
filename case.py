#!/usr/bin/env python3
"""CASE — configurable, visible-browser property search and cautious deduplication.

Searches public pages of the actual portals ONLY where automation is permitted.
Never bypasses login, CAPTCHA, blocking, paywalls, or rate limits.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = ROOT / "settings.json"
SEARCHES_FILE = ROOT / "case_searches.json"
OUTPUT_DIR = ROOT / "results"
SITES = {
    "casa.it": "https://www.casa.it/",
    "immobiliare.it": "https://www.immobiliare.it/",
    "idealista.it": "https://www.idealista.it/",
}
DEFAULT = {
    "max_price_eur": 80000,
    "min_price_eur": 0,
    "min_area_m2": 55,
    "areas": ["Reggio Emilia", "Modena", "Bologna", "Prato"],
    "max_pages_per_search": 2,
    "pause_seconds": 6,
    "include_auctions": True,
}
FIELDS = [
    "site", "url", "city", "title", "address", "price_eur", "area_m2",
    "description", "listing_type", "source_checked_on", "notes"
]

# Use only the actual portal's hostname and actual listing path.
def site_of(url: str) -> str:
    try:
        u = urlsplit(url)
        host = (u.hostname or "").lower().removeprefix("www.")
        return host if u.scheme == "https" and host in SITES else ""
    except ValueError:
        return ""


def valid_listing_url(url: str) -> bool:
    site = site_of(url)
    path = urlsplit(url).path.lower()
    if site == "casa.it":
        return re.fullmatch(r"/immobili/\d+/?", path) is not None
    if site == "immobiliare.it":
        return re.fullmatch(r"/annunci/\d+/?", path) is not None
    if site == "idealista.it":
        return re.search(r"/immobile/\d+/?$", path) is not None
    return False


def validate(c: dict) -> None:
    for k in ("min_price_eur", "max_price_eur", "min_area_m2",
              "max_pages_per_search", "pause_seconds"):
        if isinstance(c.get(k), bool) or not isinstance(c.get(k), int):
            raise ValueError(f"{k} must be an integer")
    if not 0 <= c["min_price_eur"] <= c["max_price_eur"] <= 100000000:
        raise ValueError("Invalid price range")
    if not 0 <= c["min_area_m2"] <= 10000:
        raise ValueError("Invalid minimum area")
    if not 1 <= c["max_pages_per_search"] <= 10:
        raise ValueError("max_pages_per_search must be 1..10")
    if not 5 <= c["pause_seconds"] <= 3600:
        raise ValueError("pause_seconds must be 5..3600")
    if (not isinstance(c.get("areas"), list) or not c["areas"] or
        any(not isinstance(x, str) or not x.strip() for x in c["areas"])):
        raise ValueError("areas must be a nonempty list of names")
    if not isinstance(c.get("include_auctions"), bool):
        raise ValueError("include_auctions must be true/false")


def settings() -> dict:
    data = dict(DEFAULT)
    if SETTINGS_FILE.exists():
        data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    validate(data)
    return data


def snapshot(c: dict) -> dict:
    return {k: c[k] for k in
            ("max_price_eur", "min_price_eur", "min_area_m2", "include_auctions")}


def areas_from(text: str) -> list[str]:
    result = []
    for x in re.split(r"[,;]", text):
        x = x.strip()
        if x and x.casefold() not in [i.casefold() for i in result]:
            result.append(x)
    return result


def configure(args) -> None:
    c = settings()
    changed = any([
        args.max_price is not None, args.min_price is not None,
        args.min_area is not None, args.areas is not None, args.add_area,
        args.remove_area, args.pages is not None, args.delay is not None,
        args.auctions is not None,
    ])
    if args.interactive or not changed:
        print("CASE: press Enter to keep the current value.")
        for label, key in (
            ("Maximum price EUR", "max_price_eur"),
            ("Minimum price EUR", "min_price_eur"),
            ("Minimum area m2", "min_area_m2"),
        ):
            typed = input(f"{label} [{c[key]}]: ").strip()
            if typed:
                c[key] = int(typed)
        typed = input(f"Areas comma-separated [{', '.join(c['areas'])}]: ").strip()
        if typed:
            c["areas"] = areas_from(typed)
        typed = input("Include auctions? y/n [" +
                      ("y" if c["include_auctions"] else "n") + "]: ").strip().lower()
        if typed in ("y", "n"):
            c["include_auctions"] = typed == "y"
    for attr, key in (
        ("max_price", "max_price_eur"), ("min_price", "min_price_eur"),
        ("min_area", "min_area_m2"), ("pages", "max_pages_per_search"),
        ("delay", "pause_seconds"),
    ):
        value = getattr(args, attr)
        if value is not None:
            c[key] = value
    if args.areas is not None:
        c["areas"] = areas_from(args.areas)
    for x in args.add_area or []:
        if x.casefold() not in [a.casefold() for a in c["areas"]]:
            c["areas"].append(x)
    c["areas"] = [a for a in c["areas"]
                  if a.casefold() not in [x.casefold() for x in (args.remove_area or [])]]
    if args.auctions is not None:
        c["include_auctions"] = args.auctions == "yes"
    validate(c)
    SETTINGS_FILE.write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    print("Saved settings.json:\n" + json.dumps(c, indent=2, ensure_ascii=False))
    print("Remember: refresh saved portal URLs with 'setup' when changing filters.")


def load_searches() -> list[dict]:
    if not SEARCHES_FILE.exists():
        return []
    value = json.loads(SEARCHES_FILE.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("case_searches.json must contain a list")
    return value


def save_searches(items: list[dict]) -> None:
    SEARCHES_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


def show(_args) -> None:
    c = settings()
    print("SETTINGS\n" + json.dumps(c, ensure_ascii=False, indent=2))
    print("\nSAVED SEARCHES")
    for item in load_searches():
        problems = []
        if not item.get("authorized"):
            problems.append("NOT_APPROVED")
        if item.get("filters") != snapshot(c):
            problems.append("FILTERS_CHANGED")
        if item.get("city") not in c["areas"]:
            problems.append("AREA_REMOVED")
        print(item.get("site"), item.get("city"), item.get("url"),
              ", ".join(problems) if problems else "READY")
    if not load_searches():
        print("No searches saved yet. Use 'setup'.")


# Extract ONLY visible listing cards from the original portal results DOM.
EXTRACT_JS = r"""() => {
  function isAd(url) {
    try {
      const u = new URL(url, location.href);
      const h = u.hostname.replace(/^www\./, '');
      return (h === 'casa.it' && /^\/immobili\/\d+\/?$/.test(u.pathname))
        || (h === 'immobiliare.it' && /^\/annunci\/\d+\/?$/.test(u.pathname))
        || (h === 'idealista.it' && /\/immobile\/\d+\/?$/.test(u.pathname));
    } catch { return false; }
  }
  let seen = new Set(), items = [];
  for (const a of document.querySelectorAll('a[href]')) {
    let url;
    try {
      const u = new URL(a.getAttribute('href'), location.href);
      u.hash = ''; u.search = '';
      url = u.href;
    } catch { continue; }
    if (!isAd(url) || seen.has(url)) continue;
    let node = a.closest('article, li, [data-testid*="listing"], [class*="listing-card"], [class*="listingCard"]') || a.parentElement;
    for (let i = 0; i < 3 && node && (node.innerText || '').trim().length < 45; i++)
      node = node.parentElement;
    const text = (node?.innerText || a.innerText || '').replace(/\s+/g, ' ').trim();
    if (!text) continue;
    seen.add(url);
    items.push({url, title: (a.innerText || a.title || '').trim().slice(0, 240),
                text: text.slice(0, 2000)});
  }
  let next = document.querySelector('a[rel="next"]');
  if (!next) next = Array.from(document.querySelectorAll('a[href]')).find(
    a => /^(next|avanti|successiva|pagina successiva)\b/i.test(
      (a.getAttribute('aria-label') || a.innerText || '').trim()));
  let nextUrl = null;
  if (next) {try {nextUrl = new URL(next.getAttribute('href'), location.href).href} catch {}}
  return {items, next_url: nextUrl};
}"""

PRICE_RX = re.compile(r"€\s*([\d.,]+)|([\d.,]+)\s*€")
AREA_RX = re.compile(r"\b(\d{2,4})\s*(?:m²|mq|m2)\b", re.I)
STREET_RX = re.compile(r"\b(?:via|viale|piazza|piazzale|corso|largo|strada)\s+[^,;|]{3,65}", re.I)


def price_from(text: str) -> int | None:
    for m in PRICE_RX.finditer(text):
        s = (m.group(1) or m.group(2)).strip()
        try:
            n = float(s.replace(".", "").replace(",", ".")) if "," in s else float(s.replace(".", ""))
            if 10000 <= n <= 30000000:
                return int(n)
        except ValueError:
            continue
    return None


def size_from(text: str) -> int | None:
    for m in AREA_RX.finditer(text):
        n = int(m.group(1))
        if 10 <= n <= 3000:
            return n
    return None


def parse_card(item: dict, site: str, city: str) -> dict | None:
    url = item.get("url", "")
    if not valid_listing_url(url) or site_of(url) != site:
        return None
    text = item.get("text", "")
    title = item.get("title", "") or text[:120]
    address_match = STREET_RX.search(title)
    if address_match is None:
        address_match = STREET_RX.search(text[:200])
    addr = address_match.group(0).strip(" ,-.:") if address_match else ""
    price = price_from(text)
    area = size_from(text)
    return {
        "site": site, "url": url, "city": city, "title": title[:240],
        "address": addr, "price_eur": str(price) if price is not None else "",
        "area_m2": str(area) if area is not None else "",
        "description": text[:700],
        "listing_type": "asta" if re.search(r"\basta\b", text, re.I) else "vendita",
        "source_checked_on": date.today().isoformat(),
        "notes": "AUTOMATIC_CARD_PARSE; VERIFY_MANUALLY",
    }


def chrome_context(playwright):
    profile = ROOT / ".case_chrome_profile"
    try:
        return playwright.chromium.launch_persistent_context(
            str(profile), channel="chrome", headless=False,
            locale="it-IT", viewport={"width": 1280, "height": 900})
    except Exception:
        return playwright.chromium.launch_persistent_context(
            str(profile), headless=False,
            locale="it-IT", viewport={"width": 1280, "height": 900})


def setup(args) -> None:
    c = settings()
    if args.area not in c["areas"]:
        raise ValueError("Add area to settings.json first, or use configure --add-area")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as ex:
        raise SystemExit("Install requirements: python -m pip install -r requirements.txt") from ex
    with sync_playwright() as p:
        ctx = chrome_context(p)
        try:
            page = ctx.new_page()
            page.goto(SITES[args.site], wait_until="domcontentloaded", timeout=45000)
            print("In Chrome, select your area and apply ALL desired filters on the real portal.")
            input(f"Showing {args.site} for {args.area}. Press Enter here on the results page...")
            url = page.url
            if site_of(url) != args.site:
                raise ValueError("Browser is not on the expected portal. Nothing saved.")
            items = [x for x in load_searches()
                     if not (x.get("site") == args.site and x.get("city") == args.area)]
            items.append({"site": args.site, "city": args.area, "url": url,
                          "filters": snapshot(c), "authorized": False})
            save_searches(items)
            print("Search saved (disabled until explicit permission approval).", url)
        finally:
            ctx.close()


def approve(args) -> None:
    if not args.i_have_permission:
        raise ValueError("Check portal terms and confirm the required authorization explicitly.")
    c = settings()
    items = load_searches()
    count = 0
    for x in items:
        if x.get("site") == args.site and x.get("city") == args.area:
            if x.get("filters") != snapshot(c):
                raise ValueError("Filter settings changed: run setup again first")
            x["authorized"] = True
            count += 1
    if not count:
        raise ValueError("Saved search not found; run setup first")
    save_searches(items)
    print("Enabled permitted search:", args.site, args.area)


def write_csv(path: Path, items: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)


def collect(_args) -> None:
    c = settings()
    searches = [x for x in load_searches()
                if x.get("authorized") is True
                and x.get("site") in SITES
                and site_of(x.get("url", "")) == x.get("site")
                and x.get("city") in c["areas"]
                and x.get("filters") == snapshot(c)]
    if not searches:
        raise ValueError("No permitted, current searches. Run setup and approve.")
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
    except ImportError as ex:
        raise SystemExit("Install requirements: python -m pip install -r requirements.txt") from ex
    results, seen_urls = [], set()
    with sync_playwright() as p:
        ctx = chrome_context(p)
        try:
            page = ctx.new_page()
            for search in searches:
                url = search["url"]
                seen_pages = set()
                for i in range(c["max_pages_per_search"]):
                    if not url or url in seen_pages or site_of(url) != search["site"]:
                        break
                    seen_pages.add(url)
                    print(f"Scanning {search['site']} / {search['city']} — page {i+1}")
                    try:
                        response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(1800)
                    except BrowserTimeout:
                        print("Timeout; stopping this search")
                        break
                    if response and response.status in (401, 403, 429):
                        print("Site blocked or throttled automation; stopping search")
                        break
                    if any(x in page.title().casefold() for x in
                           ("captcha", "access denied", "just a moment", "verifica di sicurezza")):
                        print("Security challenge detected; stopping search")
                        break
                    payload = page.evaluate(EXTRACT_JS)
                    print("Listing links found:", len(payload.get("items", [])))
                    for item in payload.get("items", []):
                        row = parse_card(item, search["site"], search["city"])
                        if not row or row["url"] in seen_urls:
                            continue
                        seen_urls.add(row["url"])
                        pr = int(row["price_eur"]) if row["price_eur"] else None
                        sz = int(row["area_m2"]) if row["area_m2"] else None
                        if pr is not None and not c["min_price_eur"] <= pr <= c["max_price_eur"]:
                            continue
                        if sz is not None and sz < c["min_area_m2"]:
                            continue
                        if not c["include_auctions"] and row["listing_type"] == "asta":
                            continue
                        if pr is None or sz is None:
                            row["notes"] += "; MISSING_PRICE_OR_AREA"
                        results.append(row)
                    url = payload.get("next_url")
                    time.sleep(c["pause_seconds"])
        finally:
            ctx.close()
    output = OUTPUT_DIR / "listings.csv"
    write_csv(output, results, FIELDS)
    print(f"Saved {len(results)} candidates: {output}")
    dedup_rows(results)


def normal(text: str) -> str:
    s = unicodedata.normalize("NFKD", str(text).casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\b(via|viale|piazza|piazzale|corso|strada)\b", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def number(text: str) -> int | None:
    try:
        return int(float(str(text).replace(".", "").replace(",", ".")))
    except (ValueError, TypeError):
        return None


def match(a: dict, b: dict) -> tuple[str, float, str]:
    if a.get("url") == b.get("url"):
        return "MATCH", 1.0, "SAME_URL"
    if normal(a.get("city", "")) != normal(b.get("city", "")):
        return "NONE", 0.0, "DIFFERENT_CITY"
    if a.get("site") == b.get("site"):
        return "NONE", 0.0, "SAME_SITE_DIFFERENT_AD"
    pa, pb = number(a.get("price_eur")), number(b.get("price_eur"))
    ma, mb = number(a.get("area_m2")), number(b.get("area_m2"))
    if not all(v is not None for v in (pa, pb, ma, mb)):
        return "NONE", 0.0, "INSUFFICIENT_DETAILS"
    pdiff = abs(pa-pb) / max(pa, pb, 1)
    mdiff = abs(ma-mb) / max(ma, mb, 1)
    street_a, street_b = normal(a.get("address", "")), normal(b.get("address", ""))
    if street_a and street_b and street_a == street_b:
        if pdiff <= .05 and mdiff <= .15:
            return "MATCH", .93, "SAME_ADDRESS_PRICE_SIZE"
        if pdiff <= .08 and mdiff <= .35:
            return "REVIEW", .7, "ADDRESS_MATCH_BUT_DETAILS_CONFLICT"
        return "NONE", 0.0, "ADDRESS_SAME_BUT_DIFFERENT_PROPERTY"
    title_sim = SequenceMatcher(None, normal(a.get("title", "")),
                               normal(b.get("title", ""))).ratio()
    if pdiff <= .02 and mdiff <= .05 and title_sim >= .8:
        return "REVIEW", .67, "SIMILAR_TITLE_PRICE_SIZE_VERIFY_ADDRESS"
    return "NONE", 0.0, "INSUFFICIENT_EVIDENCE"


def dedup_rows(rows: list[dict]) -> dict:
    items = [{**{k: x.get(k, "") for k in FIELDS}, "ad_id": f"AD{i+1:04d}"}
             for i, x in enumerate(rows)]
    matches = []
    parent = list(range(len(items)))
    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i

    for i in range(len(items)):
        for j in range(i+1, len(items)):
            decision, conf, reason = match(items[i], items[j])
            if decision == "NONE":
                continue
            matches.append({"left_ad": items[i]["ad_id"], "right_ad": items[j]["ad_id"],
                            "decision": decision, "confidence": conf, "reason": reason})
            if decision == "MATCH":
                x, y = root(i), root(j)
                if x != y:
                    a_group = [v for v in range(len(items)) if root(v) == x]
                    b_group = [v for v in range(len(items)) if root(v) == y]
                    # Avoid transitive false positives from chain merges.
                    if all(match(items[a], items[b])[0] == "MATCH"
                           for a in a_group for b in b_group):
                        parent[y] = x
    homes = {}
    for idx, item in enumerate(items):
        homes.setdefault(root(idx), []).append(item)
    unique = []
    for n, group in enumerate(homes.values(), 1):
        home_id = f"HOME{n:04d}"
        for x in group:
            x["home_id"] = home_id
        prices = [number(x["price_eur"]) for x in group if number(x["price_eur"]) is not None]
        sizes = [number(x["area_m2"]) for x in group if number(x["area_m2"]) is not None]
        unique.append({
            "home_id": home_id,
            "city": group[0]["city"],
            "address": next((x["address"] for x in group if x["address"]), ""),
            "min_reported_price_eur": min(prices) if prices else "",
            "reported_areas_m2": "; ".join(map(str, sorted(set(sizes)))),
            "sites": "; ".join(sorted({x["site"] for x in group})),
            "ad_count": len(group),
            "urls": " | ".join(x["url"] for x in group),
            "needs_manual_verification": "YES",
        })
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR/"all_listings.csv", items, ["home_id", "ad_id"] + FIELDS)
    write_csv(OUTPUT_DIR/"matches.csv", matches,
              ["left_ad", "right_ad", "decision", "confidence", "reason"])
    write_csv(OUTPUT_DIR/"unique_properties.csv", unique, [
        "home_id", "city", "address", "min_reported_price_eur",
        "reported_areas_m2", "sites", "ad_count", "urls",
        "needs_manual_verification",
    ])
    summary = {
        "input_ad_count": len(items),
        "unique_home_count": len(unique),
        "collapsed_duplicate_ads": len(items)-len(unique),
        "candidate_review_pairs": sum(x["decision"] == "REVIEW" for x in matches),
    }
    (OUTPUT_DIR/"summary.json").write_text(json.dumps(summary, indent=2)+"\n",
                                           encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def dedup(args) -> None:
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    dedup_rows(rows)


def main() -> None:
    cli = argparse.ArgumentParser(description="CASE real-estate visible Chrome collector")
    sub = cli.add_subparsers(dest="command", required=True)
    c = sub.add_parser("configure", help="Edit prices, regions, sizes, auction setting")
    c.add_argument("--interactive", action="store_true")
    c.add_argument("--max-price", type=int)
    c.add_argument("--min-price", type=int)
    c.add_argument("--min-area", type=int)
    c.add_argument("--areas")
    c.add_argument("--add-area", action="append")
    c.add_argument("--remove-area", action="append")
    c.add_argument("--pages", type=int)
    c.add_argument("--delay", type=int)
    c.add_argument("--auctions", choices=["yes", "no"])
    c.set_defaults(fn=configure)
    sub.add_parser("show").set_defaults(fn=show)
    s = sub.add_parser("setup", help="Save browser search URL for one portal and area")
    s.add_argument("--site", required=True, choices=sorted(SITES))
    s.add_argument("--area", required=True)
    s.set_defaults(fn=setup)
    a = sub.add_parser("approve", help="Explicitly enable a search if permitted")
    a.add_argument("--site", required=True, choices=sorted(SITES))
    a.add_argument("--area", required=True)
    a.add_argument("--i-have-permission", action="store_true")
    a.set_defaults(fn=approve)
    sub.add_parser("collect", help="Visit permitted saved searches in real Chrome").set_defaults(fn=collect)
    d = sub.add_parser("dedup", help="Deduplicate an existing CSV offline")
    d.add_argument("--input", default="examples/sample_listings.csv")
    d.set_defaults(fn=dedup)
    args = cli.parse_args()
    try:
        args.fn(args)
    except (ValueError, json.JSONDecodeError) as ex:
        cli.error(str(ex))


if __name__ == "__main__":
    main()

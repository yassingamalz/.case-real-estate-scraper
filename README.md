# CASE — Italian Real Estate Listing Collector

## Recommended workflow: existing Web Scraper extension → CSV → CASE

**For Immobiliare.it, start with Web Scraper CSV imports, not `python case.py collect`.** The site has rejected automated Playwright collection in the user's tests.

1. Install [Web Scraper Chrome extension](https://chromewebstore.google.com/detail/jnhgnonknehpejjnehehllkliplmbmhn).
2. Follow **[WEB_SCRAPER_GUIDE_IT.md](WEB_SCRAPER_GUIDE_IT.md)** to configure one listing card and export a permitted single-page CSV.
3. Set the filters (personal settings are saved to `settings.local.json`, which Git ignores):

~~~bash
python case.py configure --min-price 20000 --max-price 80000 --min-area 30 --areas "Reggio Emilia"
~~~

4. Import your CSV with no browser automation:

~~~bash
python case.py import-webscraper --input "/c/Users/YassinSohim/Downloads/annunci.csv" --area "Reggio Emilia"
~~~

5. Check `results/unique_properties.csv` and `results/matches.csv`. Keep source evidence and manually check each match.

**Legacy modes:** The custom `chrome_extension/` and `collect` commands remain available for compatibility, but are not the recommended route. The local CSV import works without Chrome automation. An extension is **not** authorization to scrape; respect each website's current terms, stop on access blocks and never bypass them.

## Updating an existing checkout with personalized settings

Older versions wrote changes directly into tracked `settings.json`. Back them up before pulling:

~~~bash
cp settings.json settings.backup.json
git status
git stash push -m "my old CASE settings" -- settings.json
git pull --ff-only
cp settings.backup.json settings.local.json
python case.py show
~~~

The new `configure` command writes `settings.local.json`, so subsequent pulls leave your preferences alone. The backup is not ignored by default: do **not** commit or push it.

---

## Legacy browser collection documentation

Personal research tool for **Casa.it**, **Immobiliare.it**, and **Idealista.it**. Opens **real Chrome** via Playwright, collects links and public listing-card details from saved search-result pages *when permitted*, applies your filters, and flags likely duplicate advertisements across the three portals. **No Brave Search API. No web app.**

> IMPORTANT: Browser automation is not permission to extract data. Check each portal's current terms and get any required authorization before using automated collection. Do not use this tool to bypass CAPTCHA, authentication, rate limits, or access restrictions. This project does not assert that any portal has authorized scraping.

## Install

Python 3.10+ and Chrome (or Playwright Chromium) required.

~~~bash
git clone https://github.com/yassingamalz/.case-real-estate-scraper.git
cd .case-real-estate-scraper
python -m pip install -r requirements.txt
python -m playwright install chromium
~~~

## 1. Change search filters — whenever you like

Edit **settings.json** directly, or use the built-in wizard:

~~~bash
python case.py configure
~~~

Noninteractive examples:

~~~bash
python case.py configure --max-price 85000 --min-area 60
python case.py configure --areas "Reggio Emilia, Modena, Bologna, Prato"
python case.py configure --add-area "Carpi"
python case.py configure --remove-area "Prato"
python case.py configure --auctions no
python case.py show
~~~

Defaults: **€80,000 maximum**, 55 m² minimum, Reggio Emilia / Modena / Bologna / Prato, 2 result pages per search, 6 seconds between pages. Auctions can be included or excluded.

## 2. Save real search URLs (one time per area and portal)

~~~bash
python case.py setup --site casa.it --area "Reggio Emilia"
python case.py setup --site immobiliare.it --area "Reggio Emilia"
python case.py setup --site idealista.it --area "Reggio Emilia"
~~~

Chrome opens the **real portal**. In the browser, choose the desired area and apply the **same filters as settings.json**. When the results page is visible, press Enter in the terminal to save the URL. Repeat for additional areas. Configuration is saved to case_searches.json (gitignored).

**Important limitation:** Each site uses its own search filter/UI and URL scheme. Thus this release has a **manual browser setup step** for each site/area, rather than fragile undocumented automatic form-clicking. Subsequent scans are automated. **When you change a location/price/size/auction filter, refresh saved site searches using setup again**; post-extraction filtering alone cannot recover listings excluded by an old portal search URL.

### Permission gate
The saved URLs default to disabled for automated collection. After verifying you have the right to automate a specific portal, explicitly activate each saved search:

~~~bash
python case.py approve --site casa.it --area "Reggio Emilia" --i-have-permission
~~~

Do **not** approve a site whose terms require permission that you do not have.

### If the automated Chrome window stays on a blank/new tab

Use the **normal Chrome browser** to open the real portal, apply the filters and confirm that results are displayed. Copy the **complete address bar URL** (including query parameters), then save it directly:

~~~bash
python case.py setup --site immobiliare.it --area "Reggio Emilia" --url "https://www.immobiliare.it/vendita-case/reggio-emilia/?prezzoMinimo=20000&prezzoMassimo=80000"
~~~

This example URL is illustrative: paste the URL that actually works for you, and verify it shows **Reggio Emilia**, not the different town **Reggiolo**, and the intended €20,000 minimum (not €2,000). This avoids the **browser-based setup step**, but `collect` still uses Playwright and may be blocked by portal restrictions. Saving a URL is not permission to scrape.

## 3. Collect and deduplicate

~~~bash
python case.py collect
~~~

This opens actual Chrome/Chromium and scans the saved permitted results. Output under the gitignored **results/** directory:

- **listings.csv** — collected candidate ads, links, visible prices/areas, and extraction notes.
- **unique_properties.csv** — cautiously grouped homes, one row per group.
- **matches.csv** — matches and *review* candidates, including confidence and reasons.
- **summary.json** — counts.

You can also deduplicate an existing CSV without opening the browser:

~~~bash
python case.py dedup --input examples/sample_listings.csv
~~~

## Quality and limits

- The extracted info comes from **visible result cards**, not a certified live inventory. Prices, m² and address may be missing or parsed incorrectly. You should manually verify every shortlisted property.
- No guarantee of covering all listings, perfect cross-site matching or current availability. If an address/agency reference is absent, matching is conservative and often flagged **REVIEW** rather than merged automatically.
- Some portals may prevent automated access or change HTML. The script stops on common block responses; it does not bypass challenges.
- No credentials, saved cookies, browser profiles, or generated results are published to GitHub.
- Legal/title, occupancy, renovations, energy certificate and 100% mortgage eligibility require separate checks.

## Tests

~~~bash
python -m unittest discover -s tests -v
~~~

## Quick Italian / Egyptian Arabic note

تقدر تغيّر السعر والمناطق في أي وقت من \`python case.py configure\` أو \`settings.json\`. بعد تغيير الفلاتر لازم تحدّث روابط البحث لكل موقع عشان النتائج الجديدة تكون كاملة. السكريبت بيفتح Chrome الحقيقي، مش Brave، ويجمع الإعلانات المسموح باستخراجها ويقارن الإعلانات المتشابهة، مع قائمة مراجعة لأي تطابق غير مؤكد.

## License
MIT.
# CASE – Manual Chrome Export (Immobiliare.it only)

This optional **Manifest V3 Chrome extension** is a *manual capture* tool.
It does not automate searches, paginate pages, bypass anti-bot checks, or read credentials or cookies.

## Install unpacked extension

1. In Chrome open \`chrome://extensions\`.
2. Enable **Developer mode** (top right).
3. Click **Load unpacked / Carica estensione non pacchettizzata**.
4. Select the **chrome_extension** folder in your local project checkout.

## Export one visible results page

1. In your **normal Chrome** open Immobiliare.it. Choose the **actual** location and filters.
2. Ensure listing cards have loaded and you can see them.
3. Click the **CASE** extension icon, then **Esporta annunci visibili (.json)**.
4. A JSON is saved to your Downloads folder (no transfer to any server).
5. Go to the project's Git Bash terminal:

~~~bash
python case.py import-json --input "/c/Users/YassinSohim/Downloads/case-immobiliare-...json" --area "Reggio Emilia"
~~~

Replace the path with your real downloaded file path. The command verifies URL/city/price filters, parses the cards, and produces \`results/listings.csv\` and \`results/unique_properties.csv\`. Additional imports will add new listings to the existing CSV and rerun dedup.

**Limitations:** Each click exports only the currently visible listing cards (not all search results). The extension uses visible DOM text so extraction is best-effort: verify address, price and size manually. Only use collection permitted by the portal's terms; loading in a normal browser is **not** permission to bulk extract data. Do not share full page HTML, browser profiles or cookies. The extension does not need login data.

/* CASE Chrome MV3: one-click, user-initiated export from the active tab only.
   No background process, pagination, network calls, cookies or credential access.
*/
const button = document.getElementById("export");
const status = document.getElementById("status");

function visibleCards() {
  const host = location.hostname.toLowerCase().replace(/^www\./, "");
  if (host !== "immobiliare.it") {
    return { error: "Questa versione funziona solo su Immobiliare.it." };
  }
  const items = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/annunci/"]')) {
    if (a.getClientRects().length === 0) continue;
    let url;
    try {
      const u = new URL(a.getAttribute("href"), location.href);
      if (u.protocol !== "https:" ||
          u.hostname.toLowerCase().replace(/^www\./, "") !== "immobiliare.it" ||
          !/^\/annunci\/\d+\/?$/.test(u.pathname)) continue;
      u.hash = "";
      u.search = "";
      url = u.toString();
    } catch {
      continue;
    }
    if (seen.has(url)) continue;
    let node = a.closest('article, li, [data-testid*="listing"], [class*="listing-card"], [class*="in-listing"]');
    if (!node) node = a.parentElement;
    // Never export entire page content or account/sidebar information.
    let text = (node?.innerText || "").replace(/\s+/g, " ").trim();
    if (text.length < 30 || text.length > 1800) {
      const alternative = (a.parentElement?.innerText || "").replace(/\s+/g, " ").trim();
      text = alternative.length < 1800 ? alternative : "";
    }
    if (!text || text.length > 1800) continue;
    const title = (a.innerText || a.getAttribute("title") || "").replace(/\s+/g, " ").trim().slice(0, 240);
    items.push({url, title, text: text.slice(0, 1800)});
    seen.add(url);
  }
  return {
    format: "case-visible-listings-v1",
    site: "immobiliare.it",
    page_url: location.href,
    exported_at: new Date().toISOString(),
    items
  };
}

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "Lettura della pagina corrente…";
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab || !/^https:\/\/(www\.)?immobiliare\.it\//i.test(tab.url || "")) {
      throw new Error("Apri prima Immobiliare.it nel tab attivo.");
    }
    const response = await chrome.scripting.executeScript({
      target: {tabId: tab.id},
      func: visibleCards
    });
    const result = response?.[0]?.result;
    if (!result || result.error) throw new Error(result?.error || "Nessun risultato.");
    if (!result.items.length) {
      status.textContent = "Nessun annuncio visibile trovato. Controlla che la pagina mostri le schede immobiliari.";
      return;
    }
    const blob = new Blob([JSON.stringify(result, null, 2)], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "case-immobiliare-" + new Date().toISOString().replace(/[.:]/g, "-") + ".json";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 15000);
    status.textContent = result.items.length + " annunci esportati. Il file è nella cartella Download.";
  } catch (error) {
    status.textContent = String(error?.message || error);
  } finally {
    button.disabled = false;
  }
});

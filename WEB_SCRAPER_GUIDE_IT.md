# CASE — import CSV da Web Scraper (Immobiliare.it)

Questo è il flusso consigliato per iniziare: **Web Scraper (estensione Chrome) → CSV → \`python case.py import-webscraper\` → risultati senza duplicati**.

**Attenzione:** Web Scraper non rende automaticamente consentita la raccolta dati. Prima di avviare una sessione di estrazione automatizzata, verifica le condizioni d'uso del sito e ottieni eventuali autorizzazioni. Non aggirare CAPTCHA, blocchi o limiti. L'uso dell'estensione può essere soggetto agli stessi limiti di Playwright.

## 1. Preparare il PC

- In Git Bash, nella cartella del repository, esegui \`git pull --ff-only\`.
- I tuoi filtri personali sono in \`settings.json\`. Per esempio \`python case.py configure --max-price 80000 --min-price 20000 --min-area 30 --areas "Reggio Emilia"\`.
- Installa l'estensione **Web Scraper** da https://chromewebstore.google.com/detail/web-scraper-free-web-scrap/jnhgnonknehpejjnehehllkliplmbmhn.
- Per la prima prova usa soltanto **Immobiliare.it** e una singola pagina. Verifica che i suoi termini permettano il metodo scelto.

## 2. Preparare la sitemap nell'estensione

1. In Chrome normale apri **Immobiliare.it**, vai alla pagina risultati corretta di **Reggio Emilia** e applica i filtri di prezzo e metratura.
2. Premi \`F12\` e cerca la scheda **Web Scraper** in DevTools (potrebbe essere sotto \`>>\`).
3. Crea una sitemap chiamata \`case_immobiliare_reggio\` e imposta **Start URL** all'URL *effettivo* della ricerca. Non usare una pagina Reggiolo etichettandola come Reggio Emilia.
4. In \`_root\` aggiungi un selettore **Element** chiamato \`listing\`. Con lo strumento visuale seleziona il *contenitore intero* di un annuncio; abilita **Multiple**, verificando che venga selezionata una scheda per ciascun immobile.
5. Come **figli** del selettore \`listing\`, crea i seguenti campi. Usa **First Record Only** (non Multiple) per i campi testuali; i selettori CSS sotto sono da individuare sulla pagina effettiva, non sono nomi di classi promessi dal portale:

| Campo | Tipo Web Scraper | Target da selezionare |
| --- | --- | --- |
| \`link\` | Element Attribute | L'elemento \`a[href*="/annunci/"]\` dentro ogni scheda, **attributo \`href\`** |
| \`title\` | Text | Titolo dell'immobile |
| \`price\` | Text | Prezzo attuale dell'immobile |
| \`area\` | Text | Superficie dell'immobile |
| \`address\` | Text | Via e civico, se esposti |
| \`description\` | Text | Testo descrittivo (facoltativo) |

Nota: Se Web Scraper esporta il campo link come \`link\` anziché \`link-href\`, il nostro importatore supporta entrambi. Se la pagina non espone un civico, lascialo vuoto: il programma segnalerà come possibili duplicati gli annunci con prova insufficiente.

6. Usa **Selector Preview / Data Preview** per verificare che ogni record abbia URL annuncio, prezzo e superficie coerenti. Non aggiungere ancora una selezione per paginazione o dettagli, per evitare raccolte non intenzionali.
7. **Solo se autorizzato dal portale**, usa \`Scrape\` nel menu della sitemap e poi \`Export Data → CSV\`. Se la sessione è bloccata, fermati.

Documentazione ufficiale:
- https://webscraper.io/documentation/selectors/element-selector
- https://webscraper.io/documentation/selectors/element-attribute-selector
- https://webscraper.io/documentation/local-scraping

## 3. Importare il CSV in CASE

Da Git Bash:

~~~bash
python case.py import-webscraper --input "/c/Users/YassinSohim/Downloads/NOME_DEL_FILE.csv" --area "Reggio Emilia" --site immobiliare.it
~~~

Il comando non apre alcun sito. Applica **i filtri di \`settings.json\`** ai valori presenti nel CSV, deduplica gli URL già importati e rigenera:
- \`results/listings.csv\`: dati importati e filtrati.
- \`results/all_listings.csv\`: annunci con ID.
- \`results/unique_properties.csv\`: singoli immobili rilevati.
- \`results/matches.csv\`: duplicati e possibili duplicati da verificare.
- \`results/summary.json\`: riepilogo.

Se le colonne esportate hanno nomi diversi:

~~~bash
python case.py import-webscraper --input "/c/Users/YassinSohim/Downloads/annunci.csv" \
  --area "Reggio Emilia" --url-column "annuncio-href" --title-column "titolo" \
  --price-column "prezzo" --area-column "superficie" --address-column "indirizzo"
~~~

Verifica sempre i risultati. L'importatore scarta link fuori dal portale e filtra prezzo/metri quadri dove disponibili. I record con prezzo o superficie mancanti vengono conservati con una segnalazione; non vanno trattati come verificati.

Per testare l'importatore senza alcun accesso a siti:

~~~bash
python -m unittest discover -s tests -v
python case.py import-webscraper --input examples/webscraper_export_example.csv --area "Reggio Emilia"
~~~

Il file di esempio contiene **annunci inventati per i test**, non case in vendita.

## Limiti noti

- Gli scraper possono essere bloccati anche come estensioni; non garantiamo l'accesso.
- Un URL di ricerca salvato nel vecchio \`case_searches.json\` non viene utilizzato dal nuovo importatore CSV.
- Non si può dedurre se un annuncio sia ancora disponibile da un CSV. Confermare disponibilità, stato occupazionale, vincoli e finanziabilità attraverso le fonti originali.
- Evita di condividere credenziali, cookie, profili Chrome o HTML completi.

# Confidențialitate

Pe scurt: site-ul nu vă urmărește. Nu setează niciun cookie, nu rulează niciun
instrument de analiză sau de măsurare a audienței, nu are conturi și nu are formulare.

## Cine operează site-ul

Cristian Nichifor, autorul proiectului. Pentru orice întrebare despre această pagină
sau despre date, deschideți un *issue*:
https://github.com/CristianNichifor/open-procurement/issues

## Ce rulează în browserul dumneavoastră

- **Niciun cookie și nicio stocare locală.** Pagina nu scrie nimic în browser în afara
  memoriei cache obișnuite, pe care browserul o gestionează singur.
- **Niciun instrument de analiză.** Nu există scripturi de statistici, pixeli sau
  servicii de măsurare a traficului.
- **Căutarea rulează local.** Interogările se execută în browser, cu DuckDB-Wasm, peste
  fișiere de date publice. Ce căutați nu este trimis nicăieri.

## Cine primește cererile tehnice

Orice pagină web ajunge la dumneavoastră printr-un server, care primește datele tehnice
pe care le poartă orice cerere: adresa IP, tipul browserului și adresa paginii cerute.

- **Găzduire:** Cloudflare Pages (projects.cristian-nichifor.com). Adresa mai veche a
  proiectului, cristiannichifor.github.io/open-procurement/, este servită de GitHub
  Pages.
- **CDN:** motorul de interogare DuckDB-Wasm se descarcă de la cdn.jsdelivr.net, iar
  cele două extensii ale lui care citesc fișierele de date (parquet, httpfs) de la
  extensions.duckdb.org. Acestea sunt singurele cereri către terți pe care le face
  pagina.

Codul site-ului nu înregistrează nimic despre vizitatori.

## Legături externe

Linkurile către data.gov.ro, GitHub sau alte site-uri duc la servicii cu propriile
reguli de confidențialitate și sunt accesate doar dacă dați clic pe ele.

## Datele publicate

Datele provin din surse oficiale publice și numesc autorități și firme. Dacă o
înregistrare este greșită sau vă privește și doriți să răspundeți, vedeți
[dreptul la replică](CORRECTIONS.md).

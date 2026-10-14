# Metodologia, pe scurt

Acesta este un rezumat în limba română. Documentul complet, cu toate verificările și
corecturile, este versiunea în engleză (butonul **EN** de mai sus) și este cel care
decide în caz de neconcordanță.

## Principii

1. **Observație, nu acuzație.** Proiectul raportează prețuri și poziții statistice. Nu
   afirmă că s-a încălcat legea. Un preț mare are multe explicații nevinovate: urgență,
   volum mic, livrare la distanță, altă specificație, servicii incluse.
2. **Niciun număr fără numitorul lui.** Orice agregat este publicat cu `n`. Grupurile sub
   pragul minim de eșantion sunt suprimate, nu afișate ca valoare.
3. **Mai bine necomparabil decât greșit.** Acolo unde datele nu susțin o comparație,
   rândul este marcat și exclus, nu forțat într-un număr.
4. **Totul se poate urmări până la sursă.** Fiecare rând păstrează `ocid`, adresa sursei
   și versiunea parserului.

## Prețul unitar

Pentru achizițiile directe din SEAP, prețul unitar este `itemClosingPrice`, preluat ca
atare. **Nu** calculăm niciodată un preț unitar împărțind un total la o cantitate atunci
când totalul este singura cifră disponibilă: rezultatul ar fi o medie de pachet.

## Reguli de comparabilitate

Un rând este marcat `comparabil = false` când lipsește prețul sau cantitatea, când
unitatea de măsură nu este recunoscută (nu o ghicim), sau când unitatea ori descrierea
indică un pachet fără mărime cunoscută („set”, „pachet”, „cutie”). Un „set” al unei
autorități nu se poate compara cu „setul” alteia.

## Agregare

- Doar rânduri comparabile; valorile extreme (sub percentila 1 și peste 99) sunt tăiate.
- **Mediana, nu media**: prețurile din achiziții sunt puternic asimetrice.
- Minimum `n = 5` pentru a publica un grup.
- Sumele sunt nominale; deflatorul este publicat alături, ca orice an să poată fi
  exprimat în banii altui an.

## Indicatori de risc

Fiecare indicator declară temeiul legal (Legea 98/2016), ce tipar urmărește, la ce se
aplică și perioada în care regula este valabilă. Toți sunt calcule deterministe peste
câmpuri publice, fără modele de limbaj, ca autoritatea numită să poată verifica exact
rezultatul.

Un indicator înseamnă **„merită verificat”**, niciodată „este fraudă”. Concentrarea sub
un plafon poate reflecta un buget real, o atribuire fără anunț este legală în cazurile
prevăzute de art. 104, iar o pondere de 90% poate însemna o singură firmă calificată în
zonă.

## Comparații invalide

Nu agregăm niciodată peste coduri CPV diferite: mediana tuturor produselor măsurate în
„buc” arată *ce a cumpărat* un județ, nu *cât a plătit*. Orice comparație ține constante
cel puțin codul CPV, unitatea de măsură și mărimea pachetului.

## Limite cunoscute

- Sunt acoperite doar achizițiile directe; licitațiile deschise încă nu.
- Anul 2026 nu poate fi ajustat la inflație până nu publică Eurostat indicele.
- Județul este cel al sediului autorității, nu neapărat locul livrării.
- Tratamentul TVA nu este încă stabilit în datele sursă.

## Corectări

Erorile sunt așteptate. Procedura completă este pe pagina
[dreptul la replică](CORRECTIONS.md).

# Schedulazione turni Dalmine — V1

Applicazione Python/Streamlit che trasforma l'Excel esportato dal foglio delle risposte Google Forms in una proposta mensile verificabile. L'organizzatore carica il file, seleziona mese e anno e preme **Genera calendario**.

## Regole implementate

- un medico può essere assegnato soltanto a una disponibilità dichiarata;
- se le disponibilità sono insufficienti, vengono assegnati tutti i medici compatibili e gli altri posti restano esplicitamente scoperti;
- non sono consentiti turni sovrapposti;
- devono trascorrere almeno 11 ore tra la fine di un turno e l'inizio del successivo;
- capacità: SER 7, NOT 5, DIU 7, MAT 8, POM 8;
- priorità: Bergamo Ovest, poi Bergamo Est, poi PG23/SPEDALI/GARDA/FRANCIA allo stesso livello;
- a parità di priorità viene applicata un'estrazione casuale riproducibile tramite il codice estrazione;
- se un medico compila più volte il modulo, viene usata la risposta più recente per email;
- le informazioni contrattuali e i minimi non influenzano l'assegnazione nella V1.

Le intestazioni del modulo determinano quali turni esistono in ogni data. Le colonne `festivi, prefestivi, sabati, domeniche` generano MAT, POM, DIU, SER e NOT anche quando la data cade in settimana. Le colonne `feriali` generano SER e NOT. In questo modo sono visibili anche i turni completamente scoperti.

## Dashboard

La dashboard contiene:

- sintesi immediata di copertura, posizioni richieste, assegnate e scoperte;
- elenco dei turni critici con il motivo della scopertura;
- vista calendario per mese, settimana o giorno;
- ricerca di un medico nel calendario;
- riepilogo e dettaglio dei turni per medico;
- ricerca turni per intervallo, fascia e stato di copertura;
- controlli sul file e codice dell'estrazione;
- export completo e delle singole viste in Excel e PDF.

## Input

Usare il file `.xlsx` scaricato dal Google Sheet collegato al modulo. Il parser riconosce:

- Timestamp;
- Email o Indirizzo email;
- COGNOME e NOME;
- ASST DI APPARTENENZA;
- colonne delle griglie `festivi, prefestivi, sabati, domeniche [...]` e `feriali [...]`;
- informazione sul contratto e note, conservate solo a titolo informativo.

Mappatura turni:

| Opzione del modulo | Codice | Orario | Capacità |
|---|---|---|---:|
| 8-14 | MAT | 08:00-14:00 | 8 |
| 14-20 | POM | 14:00-20:00 | 8 |
| 8-20 | DIU | 08:00-20:00 | 7 |
| 19-00 | SER | 19:00-00:00 | 7 |
| 20-8 | NOT | 20:00-08:00 | 5 |

## Avvio durante lo sviluppo

Richiede Python 3.11 o successivo.

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Utilizzo senza Python o terminale

Il progetto include una pipeline GitHub Actions che produce:

- Windows 64 bit: `AVVIA TURNI.exe` dentro uno ZIP;
- macOS Apple Silicon: `AVVIA TURNI.app` dentro uno ZIP;
- macOS Intel: `AVVIA TURNI.app` dentro uno ZIP.

L'utente estrae lo ZIP e apre l'app con un doppio clic. Il browser si apre automaticamente e il server resta accessibile solo dal computer locale. I pacchetti non firmati possono mostrare SmartScreen o Gatekeeper al primo avvio; eliminare questi avvisi richiede certificati di firma del codice.

Le istruzioni per pubblicazione web e compilazione desktop sono in `DEPLOYMENT.md`.

## Verifica automatica

La cartella `tests` controlla le regole principali: disponibilità, scoperture, riposo di 11 ore, sovrapposizioni, priorità territoriali, riproducibilità dell'estrazione, ultima risposta e lettura dei giorni festivi infrasettimanali. Il workflow esegue i test prima di creare i pacchetti desktop.

## Limiti della V1

- il riposo è verificato solo rispetto ai turni presenti nel file; eventuali turni periferici esterni non sono disponibili al sistema;
- il confine con il mese precedente e successivo non può essere controllato senza i relativi turni;
- non sono previsti minimi contrattuali, modifiche manuali, blocchi o notifiche;
- il calendario prodotto è una proposta da verificare prima della pubblicazione.

Le ipotesi su V2 e V3 restano sospese e non fanno parte di questa versione.

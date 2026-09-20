# Distribuzione della V1

## Opzione web

1. Pubblicare questa cartella in un repository GitHub senza caricare file reali con dati dei medici.
2. Creare una nuova applicazione Streamlit indicando `app.py` come file principale.
3. Condividere l'indirizzo dell'applicazione con l'organizzatore.

L'organizzatore userà soltanto il browser: carica l'Excel, genera il calendario e scarica i report. Prima di usare un servizio cloud con dati reali è necessario verificare le regole privacy dell'organizzazione e del servizio scelto.

## Opzione desktop senza Python

Il workflow `.github/workflows/build-desktop.yml` crea tre pacchetti autonomi:

- Windows 64 bit;
- macOS Apple Silicon;
- macOS Intel.

Da GitHub aprire **Actions**, selezionare **Build applicazioni desktop**, scegliere **Run workflow** e scaricare gli artifact al termine. Consegnare all'utente lo ZIP corrispondente al suo computer. L'utente deve soltanto estrarlo e aprire `AVVIA TURNI`.

I pacchetti non sono firmati. Windows SmartScreen e macOS Gatekeeper possono quindi richiedere una conferma al primo avvio.

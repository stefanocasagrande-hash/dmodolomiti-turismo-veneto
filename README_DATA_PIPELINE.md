# Pipeline dati Regione Veneto

Questa pipeline elimina il passaggio manuale di download, pulizia e caricamento dei
dati turistici ufficiali. La dashboard Streamlit legge direttamente il dataset
validato pubblicato dalla pipeline.

## Fonti acquisite

- Provincia di Belluno: arrivi e presenze mensili, italiani e stranieri;
- STL Dolomiti;
- STL Belluno - Feltre - Alpago;
- Comuni della provincia di Belluno: arrivi e presenze mensili;
- ultimo Excel riepilogativo pubblicato dalla Regione Veneto.

I CSV e gli Excel originali sono conservati in `data/raw/regione_veneto/`. Il file
`manifest.json` registra URL ufficiale, impronta SHA-256 e data della prima
acquisizione di ogni versione.

## Dataset normalizzato

`data/processed/movimento_turistico.csv` usa uno schema unico:

| Campo | Significato |
|---|---|
| `anno`, `mese_num`, `mese` | periodo di riferimento |
| `ambito` | Provincia, STL o Comune |
| `territorio_codice`, `territorio` | identificativo e nome del territorio |
| `provenienza` | Italiani, Stranieri o Totale |
| `arrivi`, `presenze` | metriche ufficiali |
| `stato_dato` | provvisorio o definitivo |
| `fonte_url`, `source_file` | tracciabilità della fonte |
| `data_acquisizione_utc` | acquisizione della versione corrente |

I mesi futuri pubblicati dalla Regione come zeri tecnici vengono esclusi. In
questo modo uno zero non disponibile non entra in confronti, medie, trend o
modelli predittivi.

## Controlli bloccanti

Prima della pubblicazione vengono verificati:

- schema e chiavi univoche;
- assenza di valori mancanti o negativi;
- continuità dei mesi disponibili;
- italiani + stranieri = totale;
- STL Dolomiti + STL Belluno = Provincia di Belluno;
- disponibilità di tutti i file attesi.

Le variazioni superiori al 200%, con scarto assoluto maggiore di 1.000, vengono
segnalate nel report ma non bloccano automaticamente l'aggiornamento. Il risultato
è scritto in `data/processed/validation_report.json`.

Se la struttura regionale cambia o un controllo fallisce, il comando termina con
errore e il workflow non pubblica alcun dato.

## Esecuzione

Aggiornamento ordinario (anno corrente e precedente):

```bash
python scripts/update_regione_veneto.py
```

Prima acquisizione o ricostruzione storica:

```bash
python scripts/update_regione_veneto.py --years 2021 2022 2023 2024 2025 2026
```

Solo test locali:

```bash
python -m unittest discover -s tests -v
```

## Automazione GitHub

Il workflow `.github/workflows/update-turismo.yml` viene eseguito ogni martedì
alle 05:17 UTC e può essere avviato manualmente. Effettua download,
normalizzazione e test; crea un commit soltanto quando i file ufficiali sono
cambiati e tutti i controlli sono superati.

Sulle pull request esegue l'intera pipeline senza effettuare commit. Questo serve
anche a verificare che i server della Regione accettino le richieste provenienti
da GitHub Actions prima dell'integrazione nel branch principale.

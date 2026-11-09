# Changelog

## 0.7.0 (novembre 2026)

### Carico sull'ESP8266
- Polling a più livelli: **CaricaDatiImp** (temperatura, allarmi, messaggio di stato) resta ogni 2 minuti; **Home** (System Problem) passa a 10 minuti e **Consumielettrici** (energia) a 30 minuti. Da 90 a circa 38 richieste l'ora, con la pagina più pesante (Home) letta un sesto delle volte.
- La Home viene comunque riletta subito se cambiano il messaggio di stato o i contatori degli allarmi, così System Problem resta reattivo sugli eventi reali.
- Intervalli configurabili in minuti dalle opzioni dell'integrazione (*Configura*); Home ed energia non possono essere letti più spesso del ciclo base.
- Tenuta del dato proporzionale all'intervallo della pagina (3 volte l'intervallo, minimo 10 minuti): energia e System Problem non diventano "Non disponibile" tra una lettura e l'altra.

### Compatibilità
- unique_id, nomi e unità invariati: storico e automazioni restano validi. Le installazioni esistenti usano i nuovi intervalli predefiniti senza interventi.

### Test
- Nuovi test: polling a livelli, rilettura della Home al cambio di stato, intervalli da opzioni.

## 0.6.0 (novembre 2026)

### Allarme manutenzione
- Il pulsante "Reset Allarmi" diventa **"Rinvio allarme manutenzione (7 giorni)"**, con icona `mdi:wrench-clock`: il comando `ResAllSET` della centralina rinvia l'allarme manutenzione di 7 giorni e non azzera i contatori degli allarmi temperatura e fusibile, quindi il nome precedente era fuorviante.
- Il pulsante è spostato tra i controlli di configurazione del dispositivo (`entity_category: config`) per evitare pressioni accidentali; resta utilizzabile da automazioni e script.
- Nuovo sensore **"Riattivazione allarme manutenzione"** (giorni), letto dalla pagina ResAll alle 00:01 e subito dopo ogni rinvio.
- Dopo la pressione vengono aggiornati sia lo stato dell'impianto sia i giorni alla riattivazione.

### Affidabilità
- Lettura giornaliera a pagine indipendenti: se TipoImpianto o ResAll non risponde restano validi gli ultimi valori e viene pianificato un nuovo tentativo.

### Compatibilità
- unique_id del pulsante invariato: entity_id e automazioni esistenti restano validi (cambia solo il nome mostrato).
- Il servizio `update_datetime` è invariato: il formato inviato coincide con quello del pulsante *Invia* della pagina di diagnostica.

### Documentazione
- Esempio di automazione giornaliera per la sincronizzazione dell'orario.

## 0.5.0 (novembre 2026)

### Affidabilità
- I sensori non passano più a "Sconosciuto" per errori sporadici dell'ESP: viene mantenuto l'ultimo valore valido per massimo 10 minuti (`STALE_MAX`), poi l'entità diventa "Non disponibile".
- Ogni pagina viene ritentata una volta prima di considerarla fallita; le pagine troncate vengono riconosciute e scartate.
- Tutte le richieste all'ESP (polling, pulsante, servizio, recupero wifi) sono serializzate e distanziate di almeno 2 secondi.
- Connessione HTTP nuova per ogni richiesta (niente keep-alive), per evitare gli errori di disconnessione tipici dell'ESP8266.
- Decodifica tollerante delle pagine: un carattere non valido non fa più perdere la lettura.
- Il setup non fallisce più se la pagina TipoImpianto non risponde: modello e seriale arrivano al primo tentativo riuscito (retry ogni 30 minuti).
- Log meno rumoroso: warning solo dopo 3 cicli falliti consecutivi su una pagina, e messaggio di ripristino quando torna leggibile.

### Correzioni
- Il trigger notturno delle 00:01 non si duplicava più a ogni modifica delle opzioni (veniva aggiunto a ogni reload e mai rimosso).
- Sessione HTTP chiusa anche quando il setup fallisce.
- Il servizio `update_datetime` usa il fuso orario di Home Assistant invece di quello del sistema/container.
- Modello, seriale e versione del dispositivo si aggiornano dopo ogni lettura notturna.
- Pulsante e servizio mostrano un errore in interfaccia se il dispositivo non risponde.

### Configurazione
- Validazione di gateway e subnet; avviso se i parametri wifi per il recupero sono incompleti.
- Traduzione inglese.
- `manifest.json`: rimosso il requisito superfluo `aiohttp`, aggiunti `integration_type` e `issue_tracker`.
- `hacs.json`: versione minima Home Assistant 2024.11.

### Test
- Test automatici in `tests/` su un'istanza Home Assistant reale: setup, tenuta del valore, scadenza, reload senza trigger duplicati, pulsante, servizio, config flow e options flow (`pip install -r requirements_test.txt`, poi `pytest`).

### Compatibilità
- unique_id, nomi e unità dei sensori invariati: lo storico e le statistiche esistenti restano collegati.

## 0.4 (ottobre 2026)
Recupero automatico wifi, fix piattaforme, struttura HACS.

## 0.3 (luglio 2026)
Ottimizzazioni prestazioni.

## 0.2
Versione iniziale.

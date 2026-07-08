# Kalko Tronic Integration v0.3

**Ottimizzazioni v0.3:**
- Sessione HTTP persistente (riduce overhead di connessione)
- **Fetch combinato** dei dati frequenti (una sola tornata di richieste parallele invece di 3 separate ogni 2 minuti)
- Cleanup risorse corretto
- Riduzione significativa del carico sul webserver ESP8266
- Logging migliorato

Questa integrazione permette di monitorare un addolcitore d'acqua Kalkotronic tramite scraping del webserver ESP integrato.

## Changelog
- **0.3** (luglio 2026): Ottimizzazioni prestazioni
- **0.2**: Versione iniziale

Per dettagli vedi il codice sorgente.

Sito produttore: https://www.kalkotronic.com/
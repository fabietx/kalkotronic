# Kalko Tronic Integration v0.4

**Ottimizzazioni v0.3:**
- Sessione HTTP persistente (riduce overhead di connessione)
- **Fetch combinato** dei dati frequenti (una sola tornata di richieste parallele invece di 3 separate ogni 2 minuti)
- Cleanup risorse corretto
- Riduzione significativa del carico sul webserver ESP8266
- Logging migliorato

Questa integrazione permette di monitorare un addolcitore d'acqua Kalkotronic tramite scraping del webserver ESP integrato.

**Novità v0.4:**
- Recupero automatico del wifi: se dopo alcuni giorni l'ESP risponde con la pagina di configurazione invece dei dati, l'integrazione reinvia SSID, password, IP e gateway (impostabili in Configura)
- Struttura HACS completa in `custom_components/kalkotronic/`
- Corretti binary sensor e pulsante di reset (rotti dalla 0.3)
- Richieste all'ESP di nuovo in sequenza con pausa

## Changelog
- **0.4** (ottobre 2026): Recupero automatico wifi, fix piattaforme, struttura HACS
- **0.3** (luglio 2026): Ottimizzazioni prestazioni
- **0.2**: Versione iniziale

Per dettagli vedi il codice sorgente.

Sito produttore: https://www.kalkotronic.com/
# Kalko Tronic Integration v0.5

Integrazione custom per Home Assistant che monitora un addolcitore d'acqua Kalkotronic tramite il webserver ESP8266 integrato (scraping delle pagine locali, nessun cloud).

## Funzionalità
- **Sensori**: temperatura impianto, efficienza, giorni di lavoro, giorni alla manutenzione, ritardo manutenzione, allarmi temperatura e fusibile, messaggio di stato, energia consumata.
- **Sensore binario** "System Problem" basato sull'indicatore di stato della home page.
- **Pulsante** "Reset Allarmi".
- **Servizio** `kalkotronic.update_datetime` per sincronizzare data e ora del dispositivo (che non supporta NTP).
- **Recupero automatico del wifi**: se l'ESP torna alla pagina di configurazione, l'integrazione reinvia SSID, password, IP e gateway impostati in *Configura*.

## Aggiornamento dei dati
- Dati dell'impianto: ogni 2 minuti, leggendo le pagine una alla volta.
- Modello, seriale e versioni: ogni notte alle 00:01; se la lettura fallisce, nuovo tentativo dopo 30 minuti.
- In caso di errore sporadico dell'ESP i sensori mantengono l'ultimo valore valido per massimo 10 minuti; oltre, diventano "Non disponibile".

## Installazione
Tramite HACS come repository personalizzato (tipo *Integration*), oppure copiando `custom_components/kalkotronic/` nella cartella `config/custom_components/` di Home Assistant. Riavviare e aggiungere l'integrazione da *Impostazioni > Dispositivi e servizi*.

Richiede Home Assistant 2024.11 o successivo.

## Diagnostica
Per il log dettagliato aggiungere a `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.kalkotronic: debug
```

## Changelog
Vedi [CHANGELOG.md](CHANGELOG.md).

Sito produttore: https://www.kalkotronic.com/

# Kalko Tronic Integration v0.7

Integrazione custom per Home Assistant che monitora un addolcitore d'acqua Kalkotronic tramite il webserver ESP8266 integrato (scraping delle pagine locali, nessun cloud).

## Funzionalità
- **Sensori**: temperatura impianto, efficienza, giorni di lavoro, giorni alla manutenzione, ritardo manutenzione, allarmi temperatura e fusibile, messaggio di stato, energia consumata.
- **Sensore binario** "System Problem" basato sull'indicatore di stato della home page.
- **Sensore** "Riattivazione allarme manutenzione": giorni mancanti alla riattivazione dell'allarme manutenzione dopo un rinvio.
- **Pulsante** "Rinvio allarme manutenzione (7 giorni)", tra i controlli di configurazione del dispositivo: equivale a *RESET ALLARME MANUTENZIONE* della pagina di diagnostica. Silenzia l'allarme manutenzione per 7 giorni (dopo 180 giorni di ritardo l'impianto si blocca comunque) e **non** azzera i contatori degli allarmi temperatura e fusibile.
- **Servizio** `kalkotronic.update_datetime` per sincronizzare data e ora del dispositivo (che non supporta NTP).
- **Recupero automatico del wifi**: se l'ESP torna alla pagina di configurazione, l'integrazione reinvia SSID, password, IP e gateway impostati in *Configura*.

## Aggiornamento dei dati
Il webserver dell'ESP8266 è il punto debole dell'impianto: troppe richieste lo portano a riavviarsi e a perdere il wifi. Per questo le pagine sono lette a intervalli diversi, una alla volta e con almeno 2 secondi di pausa.

| Pagina | Dati | Intervallo predefinito |
|---|---|---|
| CaricaDatiImp | temperatura, allarmi temperatura e fusibile, messaggio di stato, efficienza, giorni di lavoro, giorni alla manutenzione, ritardo manutenzione | 2 minuti |
| Home | System Problem | 10 minuti, più una rilettura immediata se cambiano messaggio di stato o contatori allarmi |
| Consumielettrici | energia consumata | 30 minuti |
| TipoImpianto, ResAll | modello, seriale, versioni, giorni alla riattivazione dell'allarme manutenzione | ogni notte alle 00:01 e dopo ogni rinvio; se una pagina non risponde, nuovo tentativo dopo 30 minuti |

Con i valori predefiniti si passa da 90 a circa 38 richieste l'ora rispetto alla v0.6. Gli intervalli si regolano da *Impostazioni > Dispositivi e servizi > Kalkotronic > Configura*: Home ed energia non vengono mai letti più spesso del ciclo base.

In caso di errore sporadico dell'ESP ogni sensore mantiene l'ultimo valore valido per tre volte l'intervallo della sua pagina (minimo 10 minuti); oltre, diventa "Non disponibile".

## Sincronizzazione dell'orario
Il dispositivo non supporta NTP. Il servizio `kalkotronic.update_datetime` invia data e ora di Home Assistant con lo stesso formato del pulsante *Invia* della pagina di diagnostica (`gg.mm.aaaa hh:mm`). Esempio di automazione giornaliera:

```yaml
automation:
  - alias: "Kalkotronic - sincronizza orario"
    triggers:
      - trigger: time
        at: "03:00:00"
    actions:
      - action: kalkotronic.update_datetime
```

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

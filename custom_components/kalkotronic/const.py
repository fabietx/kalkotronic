"""Costanti dell'integrazione Kalkotronic."""

DOMAIN = "kalkotronic"
MANUFACTURER = "Kalko Tronic"

# Chiavi di configurazione
CONF_WIFI_SSID = "wifi_ssid"
CONF_WIFI_PASSWORD = "wifi_password"
CONF_GATEWAY = "gateway"
CONF_SUBNET = "subnet"
DEFAULT_SUBNET = "255.255.255.0"

# Polling
UPDATE_FAST = 120            # secondi tra due letture dei dati frequenti
DAILY_REFRESH_HOUR = 0       # lettura giornaliera (modello, seriale, versioni) alle 00:01
DAILY_REFRESH_MINUTE = 1
DAILY_RETRY = 1800           # se la lettura giornaliera fallisce, nuovo tentativo dopo 30 minuti

# Protezione dell'ESP8266
REQUEST_PAUSE = 2            # pausa minima tra due richieste consecutive, da qualunque origine
REQUEST_RETRIES = 1          # nuovi tentativi per pagina prima di considerarla fallita
REQUEST_TIMEOUT = 15         # timeout totale di una richiesta (secondi)
CONNECT_TIMEOUT = 10         # timeout di connessione (secondi)

# Tenuta del dato
STALE_MAX = 600              # un valore non aggiornato da più di 10 minuti non viene più mostrato
FAILURE_LOG_THRESHOLD = 3    # cicli falliti consecutivi su una pagina prima di un warning nel log

# Recupero automatico del wifi
RECOVERY_COOLDOWN = 300      # secondi minimi tra due tentativi di recupero
REBOOT_WAIT = 30             # attesa del riavvio dell'ESP dopo il salvataggio

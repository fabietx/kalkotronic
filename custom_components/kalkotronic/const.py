"""Costanti dell'integrazione Kalkotronic."""

DOMAIN = "kalkotronic"
MANUFACTURER = "Kalko Tronic"

# Chiavi di configurazione
CONF_WIFI_SSID = "wifi_ssid"
CONF_WIFI_PASSWORD = "wifi_password"
CONF_GATEWAY = "gateway"
CONF_SUBNET = "subnet"
DEFAULT_SUBNET = "255.255.255.0"

# Polling a più livelli (valori in minuti, modificabili dalle opzioni)
CONF_FAST_INTERVAL = "fast_interval"      # CaricaDatiImp: temperatura, allarmi, stato
CONF_HOME_INTERVAL = "home_interval"      # Home: indicatore System Problem
CONF_ENERGY_INTERVAL = "energy_interval"  # Consumielettrici: energia consumata
DEFAULT_FAST_INTERVAL = 2
DEFAULT_HOME_INTERVAL = 10
DEFAULT_ENERGY_INTERVAL = 30
INTERVAL_LIMITS = {                        # (minimo, massimo) in minuti
    CONF_FAST_INTERVAL: (1, 30),
    CONF_HOME_INTERVAL: (1, 120),
    CONF_ENERGY_INTERVAL: (1, 720),
}
DAILY_REFRESH_HOUR = 0       # lettura giornaliera (modello, seriale, versioni) alle 00:01
DAILY_REFRESH_MINUTE = 1
DAILY_RETRY = 1800           # se la lettura giornaliera fallisce, nuovo tentativo dopo 30 minuti

# Protezione dell'ESP8266
REQUEST_PAUSE = 2            # pausa minima tra due richieste consecutive, da qualunque origine
REQUEST_RETRIES = 1          # nuovi tentativi per pagina prima di considerarla fallita
REQUEST_TIMEOUT = 15         # timeout totale di una richiesta (secondi)
CONNECT_TIMEOUT = 10         # timeout di connessione (secondi)

# Tenuta del dato: un valore resta valido per STALE_FACTOR volte l'intervallo
# della sua pagina, e comunque almeno STALE_MIN secondi
STALE_FACTOR = 3
STALE_MIN = 600
FAILURE_LOG_THRESHOLD = 3    # cicli falliti consecutivi su una pagina prima di un warning nel log

# Recupero automatico del wifi
RECOVERY_COOLDOWN = 300      # secondi minimi tra due tentativi di recupero
REBOOT_WAIT = 30             # attesa del riavvio dell'ESP dopo il salvataggio

import aiohttp
import re


class KalkotronicClient:
    """Esegue le richieste HTTP verso il modulo ESP8266.
    
    Una GET per pagina, tutti i valori della pagina estratti insieme.
    """

    def __init__(self, host: str):
        self._host = host

    # ------------------------------------------------------------------
    # Metodi HTTP di basso livello
    # ------------------------------------------------------------------

    async def _get_page(self, pin: str) -> str:
        """Esegue una GET e restituisce l'HTML grezzo."""
        url = f"http://{self._host}/?pin={pin}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                return await resp.text()

    async def _get_home(self) -> str:
        """Esegue una GET sulla home (nessun parametro pin)."""
        url = f"http://{self._host}/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                return await resp.text()

    # ------------------------------------------------------------------
    # Fetch dati — una chiamata HTTP per blocco
    # ------------------------------------------------------------------

    async def fetch_fast_data(self) -> dict:
        """Pagina CaricaDatiImp — aggiornamento ogni 2 minuti.
        
        Valori dinamici: temperatura, efficienza, allarmi, giorni lavoro.
        """
        html = await self._get_page("CaricaDatiImp")
        return _parse_fast_data(html)

    async def fetch_daily_data(self) -> dict:
        """Pagina TipoImpianto — aggiornamento giornaliero.
        
        Valori statici: modello, seriale, versione firmware.
        """
        html = await self._get_page("TipoImpianto")
        return _parse_daily_data(html)

    async def fetch_home_status(self) -> dict:
        """Home page — aggiornamento ogni 2 minuti.
        
        Legge il colore del pallino di stato.
        """
        html = await self._get_page("Home")
        return _parse_home_status(html)
        
    async def fetch_energy_data(self) -> dict:
        """Pagina Consumielettrici — aggiornamento ogni 2 minuti."""
        html = await self._get_page("Consumielettrici")
        return _parse_energy_data(html)


# ------------------------------------------------------------------
# Funzioni di parsing — separate dal client per facilità di test
# ------------------------------------------------------------------

def _find(pattern: str, html: str):
    """Cerca un pattern nell'HTML e restituisce il primo gruppo."""
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def _parse_fast_data(html: str) -> dict:
    return {
        "temperature":           _find(r"Temperatura impianto:\s*(?:<[^>]+>\s*)*([\d.]+)", html),
        "efficiency":            _find(r"Efficienza stimata:\s*(?:<[^>]+>\s*)*(\d+)", html),
        "working_days":          _find(r"totale di\s+(\d+)\s+giorni", html),
        "maintenance_days_left": _find(r"Giorni mancanti prima della revisione:\s*(\d+)", html),
        "maintenance_delay":     _find(r"Giorni di ritardo revisione fasce:\s*(\d+)", html),
        "temp_alarms":           _find(r"Allarmi Temperatura:\s*(\d+)", html),
        "fuse_alarms":           _find(r"Allarmi Fusibile:\s*(\d+)", html),
        "status_message":        _find(r"MESSAGGIO CARD:\s*([^<]+)", html),
    }


def _parse_daily_data(html: str) -> dict:
    return {
        "model":      _find(r"Modello:\s*([^<]+)", html),
        "serial":     _find(r"Codice Seriale:\s*([^<]+)", html),
        "sw_version": _find(r"V\.Software Scheda:\s*([^<]+)", html),
        "wifi_version": _find(r"Versione\s*KT\s*WiFi\s*V\s*([0-9.]+)", html),
    }


def _parse_home_status(html: str) -> dict:
    color = _find(r'background-color:\s*(#[0-9A-Fa-f]{6});\s*border-radius:\s*50%', html)
    
    if color is None:
        raise ValueError("Colore stato non trovato nell'HTML — risposta incompleta")
    
    is_ok = color.upper() == "#00FF00"
    return {
        "system_problem": not is_ok,
        "status_color":   color,
    }


def _parse_energy_data(html: str) -> dict:
    raw = _find(r"Watt consumati dall'inizio del periodo sono:\s*([\d,]+)\s*Kwh", html)
    if raw is None:
        raise ValueError("Valore energia non trovato nell'HTML")
    # Converti virgola decimale italiana in punto
    value = float(raw.replace(",", "."))
    return {
        "energy_kwh": value,
    }
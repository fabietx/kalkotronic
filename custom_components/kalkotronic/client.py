import aiohttp
import re
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


class KalkotronicClient:
    """Client ottimizzato con sessione HTTP persistente per ridurre il carico sull'ESP8266."""

    def __init__(self, host: str):
        self._host = host
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Ottiene o crea una sessione persistente."""
        async with self._lock:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=15, sock_connect=10)
                self._session = aiohttp.ClientSession(timeout=timeout)
            return self._session

    async def close(self):
        """Chiude la sessione (da chiamare in unload)."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_page(self, pin: str) -> str:
        """Esegue una GET con sessione riutilizzata."""
        session = await self._get_session()
        url = f"http://{self._host}/?pin={pin}"
        
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def fetch_fast_data(self) -> dict:
        html = await self._get_page("CaricaDatiImp")
        return _parse_fast_data(html)

    async def fetch_daily_data(self) -> dict:
        html = await self._get_page("TipoImpianto")
        return _parse_daily_data(html)

    async def fetch_home_status(self) -> dict:
        html = await self._get_page("Home")
        return _parse_home_status(html)

    async def fetch_energy_data(self) -> dict:
        html = await self._get_page("Consumielettrici")
        return _parse_energy_data(html)

    async def fetch_all_fast(self) -> dict:
        """Fetch combinato per ridurre il numero di richieste all'ESP."""
        tasks = [
            self.fetch_fast_data(),
            self.fetch_home_status(),
            self.fetch_energy_data(),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for result in results:
            if isinstance(result, dict):
                data.update(result)
            elif isinstance(result, Exception):
                _LOGGER.warning("Errore durante fetch fast data: %s", result)
        return data


def _find(pattern: str, html: str):
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
        "model":        _find(r"Modello:\s*([^<]+)", html),
        "serial":       _find(r"Codice Seriale:\s*([^<]+)", html),
        "sw_version":   _find(r"V\.Software Scheda:\s*([^<]+)", html),
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
    value = float(raw.replace(",", "."))
    return {
        "energy": value,
    }

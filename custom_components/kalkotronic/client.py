"""Client HTTP per il webserver ESP8266 dei sistemi Kalkotronic."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
import html as html_lib
import logging
import re
import time
from typing import Any
from urllib.parse import quote_plus, urlencode

import aiohttp
from yarl import URL

from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CONNECT_TIMEOUT,
    DEFAULT_SUBNET,
    FAILURE_LOG_THRESHOLD,
    REBOOT_WAIT,
    RECOVERY_COOLDOWN,
    REQUEST_PAUSE,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT,
    STALE_MAX,
)

_LOGGER = logging.getLogger(__name__)

# Se uno di questi testi compare nella risposta, l'ESP sta servendo
# la pagina di configurazione wifi invece dei dati dell'impianto
PORTAL_MARKERS = ("wifisave",)

# Valore inviato nel campo "blynk" del portale di configurazione: è lo stesso
# usato dalla v0.4. L'integrazione non usa Blynk, ma il portale si aspetta il campo.
BLYNK_TOKEN = "YOUR_BLYNK_TOKEN"


class KalkotronicClient:
    """Client verso il webserver dell'impianto.

    Tutte le richieste (polling, pulsante, servizi, recupero wifi) passano da
    qui: sono serializzate, distanziate di almeno REQUEST_PAUSE secondi e fatte
    ciascuna su una connessione nuova, perché l'ESP8266 regge male sia la
    concorrenza sia il riuso delle connessioni keep-alive.
    """

    def __init__(
        self,
        host: str,
        wifi_ssid: str | None = None,
        wifi_password: str | None = None,
        gateway: str | None = None,
        subnet: str | None = None,
    ) -> None:
        self._host = host
        self._ssid = wifi_ssid or None
        self._password = wifi_password or None
        self._gateway = gateway or None
        self._subnet = subnet or DEFAULT_SUBNET

        self._session: aiohttp.ClientSession | None = None
        self._session_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        self._recovery_lock = asyncio.Lock()
        self._last_request = float("-inf")
        self._last_recovery = float("-inf")

        # Ultimo valore valido per chiave: {chiave: (valore, istante monotonic)}
        self._cache: dict[str, tuple[Any, float]] = {}
        # Cicli falliti consecutivi per pagina, per un logging non ripetitivo
        self._failures: dict[str, int] = {}

    @property
    def host(self) -> str:
        return self._host

    # ------------------------------------------------------------------ HTTP

    async def _get_session(self) -> aiohttp.ClientSession:
        """Ottiene o crea la sessione HTTP."""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                # force_close: una connessione nuova per ogni richiesta. L'ESP8266
                # chiude le connessioni keep-alive in modo imprevedibile e riusarle
                # causa errori sporadici (ServerDisconnectedError).
                connector = aiohttp.TCPConnector(force_close=True, limit=1)
                timeout = aiohttp.ClientTimeout(
                    total=REQUEST_TIMEOUT, sock_connect=CONNECT_TIMEOUT
                )
                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={"Connection": "close"},
                )
            return self._session

    async def close(self) -> None:
        """Chiude la sessione (chiamato in unload e se il setup fallisce)."""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = None

    async def _request(self, url: str | URL) -> str:
        """Esegue una GET serializzata e distanziata dalle precedenti."""
        session = await self._get_session()
        async with self._request_lock:
            wait = self._last_request + REQUEST_PAUSE - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    # errors="replace": un carattere non valido non deve far
                    # perdere l'intera pagina
                    return await resp.text(errors="replace")
            finally:
                self._last_request = time.monotonic()

    async def _get_page(self, pin: str) -> str:
        """GET di una pagina dati, con rilevamento del portale wifi e recupero."""
        url = f"http://{self._host}/?pin={pin}"
        html = await self._request(url)

        if not _is_config_portal(html):
            return html

        _LOGGER.warning(
            "Kalkotronic %s sta rispondendo con la pagina di configurazione wifi",
            self._host,
        )
        await self._recover_wifi()

        html = await self._request(url)
        if _is_config_portal(html):
            raise UpdateFailed(
                f"{self._host} risponde ancora con la pagina di configurazione wifi"
            )
        return html

    async def _recover_wifi(self) -> None:
        """Reinvia SSID, password e rete all'ESP (equivale a cliccare Salva)."""
        if not (self._ssid and self._password and self._gateway):
            raise UpdateFailed(
                "Pagina di configurazione wifi rilevata ma parametri wifi non "
                "configurati nell'integrazione (Impostazioni > Configura)"
            )

        async with self._recovery_lock:
            # Se il recupero è già stato tentato da poco, non ripeterlo
            if time.monotonic() - self._last_recovery < RECOVERY_COOLDOWN:
                return
            self._last_recovery = time.monotonic()

            query = urlencode(
                {
                    "s": self._ssid,
                    "p": self._password,
                    "server": "",
                    "port": "8080",
                    "blynk": BLYNK_TOKEN,
                    "ip": self._host,
                    "gw": self._gateway,
                    "sn": self._subnet,
                }
            )
            # encoded=True evita la doppia codifica da parte di aiohttp
            url = URL(f"http://{self._host}/wifisave?{query}", encoded=True)

            try:
                await self._request(url)
            except Exception as err:  # noqa: BLE001 - l'ESP chiude la connessione mentre si riavvia
                _LOGGER.debug("Risposta wifisave da %s: %s", self._host, err)

            _LOGGER.warning(
                "Parametri wifi reinviati a %s, attendo il riavvio", self._host
            )
            await asyncio.sleep(REBOOT_WAIT)

    # --------------------------------------------------------------- comandi

    async def reset_alarms(self) -> None:
        """Azzera i contatori allarmi."""
        await self._request(URL(f"http://{self._host}/?pin=ResAllSET+", encoded=True))

    async def set_datetime(self, moment: datetime) -> None:
        """Imposta data e ora sul dispositivo (non supporta NTP)."""
        # quote_plus produce ad es. 13.04.2026+21%3A00; encoded=True impedisce
        # ad aiohttp di ricodificare %3A in %253A
        value = quote_plus(moment.strftime("%d.%m.%Y %H:%M"))
        await self._request(
            URL(f"http://{self._host}/?Mia_Data_ora={value}", encoded=True)
        )

    # ---------------------------------------------------------------- letture

    async def fetch_fast_data(self) -> dict[str, Any]:
        """Pagina CaricaDatiImp: dati dell'impianto."""
        return _parse_fast_data(await self._get_page("CaricaDatiImp"))

    async def fetch_home_status(self) -> dict[str, Any]:
        """Home page: stato del sistema."""
        return _parse_home_status(await self._get_page("Home"))

    async def fetch_energy_data(self) -> dict[str, Any]:
        """Pagina Consumielettrici: energia consumata."""
        return _parse_energy_data(await self._get_page("Consumielettrici"))

    async def fetch_daily_data(self) -> dict[str, Any]:
        """Pagina TipoImpianto: modello, seriale, versioni."""
        try:
            return await self._fetch_with_retry(self._fetch_daily_page)
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(
                f"Lettura TipoImpianto da {self._host} fallita: {err}"
            ) from err

    async def _fetch_daily_page(self) -> dict[str, Any]:
        return _parse_daily_data(await self._get_page("TipoImpianto"))

    async def _fetch_with_retry(
        self, fetch: Callable[[], Awaitable[dict[str, Any]]]
    ) -> dict[str, Any]:
        """Esegue un fetch con nuovi tentativi (la pausa la gestisce _request)."""
        for attempt in range(REQUEST_RETRIES + 1):
            try:
                return await fetch()
            except UpdateFailed:
                # Portale wifi: il recupero è già stato tentato, ripetere non serve
                raise
            except Exception as err:
                if attempt == REQUEST_RETRIES:
                    raise
                _LOGGER.debug(
                    "Tentativo %d fallito su %s (%s), riprovo",
                    attempt + 1,
                    self._host,
                    err,
                )
        raise UpdateFailed("Nessun tentativo eseguito")  # non raggiungibile

    async def fetch_all_fast(self) -> dict[str, Any]:
        """Lettura combinata dei dati frequenti.

        Le pagine vengono lette una alla volta. Se una pagina o un singolo
        campo non arrivano, resta valido l'ultimo valore letto per al massimo
        STALE_MAX secondi: gli errori sporadici dell'ESP non portano i sensori
        a "sconosciuto" e non sporcano lo storico.
        """
        pages = (
            ("CaricaDatiImp", self.fetch_fast_data),
            ("Home", self.fetch_home_status),
            ("Consumielettrici", self.fetch_energy_data),
        )

        errors: list[str] = []
        for name, fetch in pages:
            try:
                values = await self._fetch_with_retry(fetch)
            except Exception as err:  # noqa: BLE001
                errors.append(f"{name}: {err}")
                self._note_failure(name, err)
                continue
            self._note_success(name)
            stamp = time.monotonic()
            for key, value in values.items():
                if value is not None:
                    self._cache[key] = (value, stamp)

        now = time.monotonic()
        data = {
            key: value
            for key, (value, stamp) in self._cache.items()
            if now - stamp <= STALE_MAX
        }

        # Nessun dato fresco né recente: le entità devono risultare non disponibili
        if not data:
            raise UpdateFailed(f"Nessun dato valido da {self._host}: {errors}")
        if errors:
            _LOGGER.debug(
                "Lettura parziale da %s, mantenuti gli ultimi valori validi: %s",
                self._host,
                errors,
            )
        return data

    def _note_failure(self, page: str, err: Exception) -> None:
        count = self._failures.get(page, 0) + 1
        self._failures[page] = count
        if count == FAILURE_LOG_THRESHOLD:
            _LOGGER.warning(
                "Pagina %s di %s non letta da %d cicli consecutivi: %s",
                page,
                self._host,
                count,
                err,
            )
        else:
            _LOGGER.debug("Pagina %s di %s non letta: %s", page, self._host, err)

    def _note_success(self, page: str) -> None:
        if self._failures.get(page, 0) >= FAILURE_LOG_THRESHOLD:
            _LOGGER.info("Pagina %s di %s di nuovo leggibile", page, self._host)
        self._failures[page] = 0


# ---------------------------------------------------------------------- parser


def _is_config_portal(html: str) -> bool:
    low = html.lower()
    return any(marker in low for marker in PORTAL_MARKERS)


def _find(pattern: str, html: str) -> str | None:
    """Cerca un pattern nell'HTML e restituisce il primo gruppo."""
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def _to_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _to_float(value: str | None) -> float | None:
    try:
        return float(value.replace(",", ".")) if value is not None else None
    except ValueError:
        return None


def _to_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(html_lib.unescape(value).split())
    return text or None


def _parse_fast_data(html: str) -> dict[str, Any]:
    data = {
        "temperature": _to_float(
            _find(r"Temperatura impianto:\s*(?:<[^>]+>\s*)*([\d.]+)", html)
        ),
        "efficiency": _to_int(
            _find(r"Efficienza stimata:\s*(?:<[^>]+>\s*)*(\d+)", html)
        ),
        "working_days": _to_int(_find(r"totale di\s+(\d+)\s+giorni", html)),
        "maintenance_days_left": _to_int(
            _find(r"Giorni mancanti prima della revisione:\s*(\d+)", html)
        ),
        "maintenance_delay": _to_int(
            _find(r"Giorni di ritardo revisione fasce:\s*(\d+)", html)
        ),
        "temp_alarms": _to_int(_find(r"Allarmi Temperatura:\s*(\d+)", html)),
        "fuse_alarms": _to_int(_find(r"Allarmi Fusibile:\s*(\d+)", html)),
        "status_message": _to_text(_find(r"MESSAGGIO CARD:\s*([^<]+)", html)),
    }
    # Pagina troncata o diversa dal previsto: è una lettura fallita
    if all(value is None for value in data.values()):
        raise ValueError("nessun dato trovato in CaricaDatiImp (risposta incompleta)")
    return data


def _parse_daily_data(html: str) -> dict[str, Any]:
    data = {
        "model": _to_text(_find(r"Modello:\s*([^<]+)", html)),
        "serial": _to_text(_find(r"Codice Seriale:\s*([^<]+)", html)),
        "sw_version": _to_text(_find(r"V\.Software Scheda:\s*([^<]+)", html)),
        "wifi_version": _to_text(
            _find(r"Versione\s*KT\s*WiFi\s*V\s*([0-9.]+)", html)
        ),
    }
    if all(value is None for value in data.values()):
        raise ValueError("nessun dato trovato in TipoImpianto (risposta incompleta)")
    return data


def _parse_home_status(html: str) -> dict[str, Any]:
    color = _find(r"background-color:\s*(#[0-9A-Fa-f]{6});\s*border-radius:\s*50%", html)
    if color is None:
        raise ValueError("colore di stato non trovato nella Home (risposta incompleta)")
    return {
        "system_problem": color.upper() != "#00FF00",
        "status_color": color,
    }


def _parse_energy_data(html: str) -> dict[str, Any]:
    value = _to_float(
        _find(r"Watt consumati dall'inizio del periodo sono:\s*([\d,]+)\s*Kwh", html)
    )
    if value is None:
        raise ValueError("valore energia non trovato (risposta incompleta)")
    return {"energy": value}

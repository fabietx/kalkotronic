import aiohttp
import re

class KalkotronicClient:
    def __init__(self, host: str):
        self._host = host

    async def _get_page(self, pin: str) -> str:
        url = f"http://{self._host}/?pin={pin}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                return await resp.text()


        async def fetch_fast_data(self) -> dict:
        html = await self._get_page("Home")

        def find(pattern):
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else None

        color = find(r'background-color:\s*(#[0-9A-Fa-f]{6});\s*border-radius:\s*50%')
        # Se non trova nulla, considera problema presente per sicurezza
        is_ok = color.upper() == "#00FF00" if color else False

        return {
            "system_problem": not is_ok,
            "system_status_color": color,
        }

    # ---------- PAGINA CaricaDatiImp ----------

    async def fetch_daily_data(self) -> dict:
        html = await self._get_page("CaricaDatiImp")

        def find(pattern):
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else None

        return {
            "status_message": find(r"MESSAGGIO CARD:\s*([^<]+)</b>"),
            "working_days": find(r"totale di\s+(\d+)\s+giorni"),
            "maintenance_expiration": find(r"revisione:\s*(\d+)"),
            "maintenance_delay": find(r"ritardo revisione fasce:\s*(\d+)"),
            "temp_alarms": find(r"Allarmi Temperatura:\s*(\d+)"),
            "fuse_alarms": find(r"Allarmi Fusibile:\s*(\d+)"),
        }

    async def fetch_fast_data(self) -> dict:
        html = await self._get_page("CaricaDatiImp")

        def find(pattern):
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else None

        return {
            "temperature": find(r"Temperatura impianto:\s*(?:<[^>]+>\s*)*([\d.]+)"),
            "efficiency": find(r"Efficienza stimata:\s*(?:<[^>]+>\s*)*(\d+)"),
        }

    # ---------- PAGINA TipoImpianto ----------

    async def fetch_device_info(self) -> dict:
        html = await self._get_page("TipoImpianto")

        def find(pattern):
            match = re.search(pattern, html, re.IGNORECASE)
            return match.group(1).strip() if match else None

        return {
            "model": find(r"Modello:\s*([^<]+)"),
            "serial": find(r"Codice Seriale:\s*([^<]+)"),
            "sw_version": find(r"V\.Software Scheda:\s*([^<]+)"),
            "wifi_version": find(r"Versione\s*KT\s*WiFi\s*V\s*([0-9.]+)"),
        }
        
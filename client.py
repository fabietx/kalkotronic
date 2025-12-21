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
            "frequency": find(r"Frequenza di lavoro:\s*([^<]+)"),
            "temp_alarms": find(r"Allarmi Temperatura:\s*(\d+)"),
            "fuse_alarms": find(r"Allarmi Fusibile:\s*(\d+)"),
        }

    async def fetch_fast_data(self) -> dict:
        html = await self._get_page("CaricaDatiImp")

        def find(pattern):
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else None

        return {
            "temperature": find(r"Temperatura impianto:\s*([\d.]+)"),
            "efficiency": find(r"Efficienza stimata:.*?<font[^>]*>\s*(\d+)\s*</font>"),
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
            "wifi_version": find(r"KT WiFi V\s*([^<]+)"),
        }
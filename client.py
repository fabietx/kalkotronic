import aiohttp
from bs4 import BeautifulSoup
import re

class KalkotronicClient:
    """Client per leggere i dati dal dispositivo Kalkotronic."""

    def __init__(self, host: str):
        self.host = host
        self.url_caricadati = f"http://{host}/?pin=CaricaDatiImp"
        self.url_tipoimpianto = f"http://{host}/?pin=TipoImpianto"

    async def fetch_caricadati(self):
        """Legge tutti i dati dalla pagina CaricaDatiImp."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url_caricadati, timeout=10) as resp:
                resp.raise_for_status()
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        data = {}

        # Serial
        b_serial = soup.find("b", string=re.compile(r"Impianto KalkoTronic S/N"))
        if b_serial:
            match = re.search(r":\s*(.*)", b_serial.text)
            if match:
                data["serial"] = match.group(1).strip()

        # Status message
        b_status = soup.find("b", string=re.compile(r"MESSAGGIO CARD"))
        if b_status:
            match = re.search(r":\s*(.*)", b_status.text)
            if match:
                data["status_message"] = match.group(1).strip()

        # Working days
        p_working = soup.find("p", string=re.compile(r"ha lavorato per un totale di"))
        if p_working:
            match = re.search(r"di\s+(\d+)\s*\(", p_working.text)
            if match:
                data["working_days"] = int(match.group(1))

        # Maintenance expiration
        p_maint_exp = soup.find("p", string=re.compile(r"Giorni mancanti prima della revisione"))
        if p_maint_exp:
            match = re.search(r":\s*(\d+)", p_maint_exp.text)
            if match:
                data["maintenance_expiration"] = int(match.group(1))

        # Maintenance delay
        p_maint_delay = soup.find("p", string=re.compile(r"Giorni di ritardo revisione fasce"))
        if p_maint_delay:
            match = re.search(r":\s*(\d+)", p_maint_delay.text)
            if match:
                data["maintenance_delay"] = int(match.group(1))

        # Efficiency
        b_efficiency = soup.find("b", string=re.compile(r"Efficienza stimata"))
        if b_efficiency:
            font_tag = b_efficiency.find("font")
            if font_tag:
                val = font_tag.get_text(strip=True)
                if val.isdigit():
                    data["efficiency"] = int(val)

        # Frequency
        freq_tag = soup.find(string=re.compile(r"Frequenza di lavoro"))
        if freq_tag:
            match = re.search(r":\s*(.*)", freq_tag)
            if match:
                data["frequency"] = match.group(1).strip()

        # Temperature
        p_temp = soup.find("p", string=re.compile(r"Temperatura impianto"))
        if p_temp:
            match = re.search(r":\s*(.*)", p_temp.text)
            if match:
                data["temperature"] = match.group(1).strip()

        # Temp alarms
        p_temp_alarms = soup.find("p", string=re.compile(r"Registrati N° Allarmi Temperatura"))
        if p_temp_alarms:
            match = re.search(r":\s*(\d+)", p_temp_alarms.text)
            if match:
                data["temp_alarms"] = int(match.group(1))

        # Fuse alarms
        p_fuse_alarms = soup.find("p", string=re.compile(r"Registrati N° Allarmi Fusibile"))
        if p_fuse_alarms:
            match = re.search(r":\s*(\d+)", p_fuse_alarms.text)
            if match:
                data["fuse_alarms"] = int(match.group(1))

        return data

    async def fetch_tipoimpianto(self):
        """Legge i dati dalla pagina TipoImpianto."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url_tipoimpianto, timeout=10) as resp:
                resp.raise_for_status()
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        data = {}

        # Model
        p_model = soup.find("p", string=re.compile(r"Modello:"))
        if p_model:
            match = re.search(r":\s*(.*)", p_model.text)
            if match:
                data["model"] = match.group(1).strip()

        # Serial (riutilizzabile per device info)
        p_serial = soup.find("p", string=re.compile(r"Codice Seriale:"))
        if p_serial:
            match = re.search(r":\s*(.*)", p_serial.text)
            if match:
                data["serial"] = match.group(1).strip()

        # Software version
        p_sw = soup.find("p", string=re.compile(r"V\.Software Scheda:"))
        if p_sw:
            match = re.search(r":\s*(.*)", p_sw.text)
            if match:
                data["sw_version"] = match.group(1).strip()

        # WiFi version
        p_wifi = soup.find("p", string=re.compile(r"Versione KT WiFi"))
        if p_wifi:
            match = re.search(r"V\s+([\d\.]+)", p_wifi.text)
            if match:
                data["wifi_version"] = match.group(1).strip()

        return data

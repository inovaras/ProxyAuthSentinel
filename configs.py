import os
import logging
import rarfile
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Настройка пути к unrar
if os.name == 'posix':
    rarfile.UNRAR_TOOL = '/usr/bin/unrar'  # Linux
else:
    rarfile.UNRAR_TOOL = 'UnRAR.exe'       # Windows


BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PROXIES = os.getenv("PROXIES", "").split(',')

# Схема валидации аккаунтов
ACCOUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "phone": {"type": "string"},
        "twoFA": {"type": "string"},
        "app_id": {"type": "number"},
        "app_hash": {"type": "string"},
        "device": {"type": "string"},
        "app_version": {"type": "string"},
        "phone_code": {"type": "string"},
        "session_string": {"type": "string"}
    },
    "required": ["phone", "app_id", "app_hash", "device", "app_version"]
}

MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", 3)) # Максимальное количество попыток восстановления
PROXY_ROTATION = os.getenv("PROXY_ROTATION", "True") == "True"       # Смена прокси при восстановлении
DELAY_BETWEEN_ATTEMPTS = int(os.getenv("DELAY_BETWEEN_ATTEMPTS", 10)) # Задержка между попытками в секундах
MAX_CONCURRENT = 5 # Ограничение на максимальное количество параллельно обрабатываемых загрузок
MAX_FILE_SIZE = 100 * 1024 * 1024  # Максимальный допустимый размер загружаемого файла — 100 МБ

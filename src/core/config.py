from pathlib import Path
from dotenv import load_dotenv
import os

from dataclasses import dataclass

load_dotenv()

TG_TOKEN = os.getenv('TG_TOKEN')
VK_API_VERSION = os.getenv('VK_API_VERSION')

# Путь для сохранения данных и результатов обработки - не пушится
BASE_PATH: Path = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_PATH / 'data'

# Настройки логгирования
@dataclass(frozen=True)
class LoggingConfig:
    # папка и имена файлов логов
    LOG_PATH: Path = DATA_PATH / 'logs'
        
    APP_LOG_NAME: str = 'app.log'
    ERR_LOG_NAME: str = 'err.log'

    # уровни и ротация
    LEVEL: str = 'INFO'
    MAX_BYTES: int = 10 * 1024 * 1024
    BACKUP_COUNT: int = 5

    # опции
    CLEAN_ON_START: bool = True     # очищать папку логов при каждом запуске приложения
    ENABLE_CONSOLE: bool = True     # выводить логи в консоль

    # Формат логов
    LOG_FORMAT: str = '%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s'
    


from pathlib import Path
from dotenv import load_dotenv
import os

from dataclasses import dataclass

load_dotenv()

TG_TOKEN = os.getenv('TG_TOKEN')
VK_API_VERSION = os.getenv('VK_API_VERSION')

# Режим распознавания лиц (True — InsightFace, False — отбор по лайкам)
USE_INSIGHTFACE: bool = os.getenv('USE_INSIGHTFACE', 'true').lower() in ('true', '1', 'yes')

# Модель InsightFace (buffalo_l по умолчанию)
INSIGHTFACE_MODEL: str = os.getenv('INSIGHTFACE_MODEL', 'buffalo_l')

# Путь для сохранения данных и результатов обработки - не пушится
BASE_PATH: Path = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_PATH / 'data'

# Путь для скачанных фото
PHOTO_DIR: Path = Path(os.getenv('PHOTO_DIR', str(DATA_PATH / 'photos')))

# Размер пачки скачивания фото для InsightFace анализа
PHOTO_BATCH_SIZE: int = int(os.getenv('PHOTO_BATCH_SIZE', '10'))

# Сколько ready-кандидатов держать впереди курсора (предзагрузка)
PHOTO_BUFFER_AHEAD: int = int(os.getenv('PHOTO_BUFFER_AHEAD', '5'))

# Очистка БД при старте (true — очистить все таблицы, false — не трогать)
CLEAN_DB_ON_START: bool = os.getenv('CLEAN_DB_ON_START', 'false').lower() in ('true', '1', 'yes')

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
    


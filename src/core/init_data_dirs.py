# Файл инициализации рабочих дирректория для логирования, кэшa и обработанных данных

from src.core.config import DATA_PATH, LoggingConfig

def setup_data_dirs(cfg: LoggingConfig):
    """
    Инициализирует рабочие папки проекта для сохранения логов и данных обработки
    Эти данные не должны коммититься в репозиторий
    """
    # ./data/
    DATA_PATH.mkdir(parents=True, exist_ok=True)

    # ./data/logs
    cfg.LOG_PATH.mkdir(parents=True, exist_ok=True)
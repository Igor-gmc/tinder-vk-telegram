import glob
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from src.core.config import LoggingConfig

# флаг, чтобы не инициализировать логирование дважды
_CONFIGURED_INIT_LOGGER = False

def _cleanup_logs(log_path: Path) -> None:
    """
    Удаляет файлы логирования из папки логов при старте

    Args:
        log_path: Path - путь до дирректории логов
    """
    pattern = str(log_path / '*.log*')

    for p in glob.glob(pattern):
        try:
            os.remove(p)
        except OSError:
            pass

def setup_logger(cfg: LoggingConfig) -> None:
    """
    Вызывать 1 раз на старте приложения (main.py / entrypoint)
    """
    global _CONFIGURED_INIT_LOGGER

    # проверяем состояние логгера, если инициализация уже была, то пропускаем
    if _CONFIGURED_INIT_LOGGER:
        return
    
    # init
    path_log = Path(cfg.LOG_PATH)
    size_log = cfg.MAX_BYTES
    backup_count_log = cfg.BACKUP_COUNT
    
    if cfg.CLEAN_ON_START:          # если в конфиге True
        _cleanup_logs(path_log)     # то удаляем все логи

    level = getattr(logging, cfg.LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(cfg.LOG_FORMAT)               # Формат строк логов из LoggingConfig
    root = logging.getLogger()
    root.setLevel(level)

    # чтобы не было дублей, если setup_logger() вызывается повторно
    if root.handlers:
        root.handlers.clear()
    # чтобы сообщения не дублировались через propagation
    root.propagate = False

    # настройка вывода в консоль логов
    if cfg.ENABLE_CONSOLE:
        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    # app.log
    app_fh = RotatingFileHandler(
        filename=str(path_log / cfg.APP_LOG_NAME),
        maxBytes=size_log,
        backupCount=backup_count_log,
        encoding='utf-8'
    )
    app_fh.setLevel(level)
    app_fh.setFormatter(formatter)
    root.addHandler(app_fh)

    # err.log
    err_fh = RotatingFileHandler(
        filename=str( path_log / cfg.ERR_LOG_NAME),
        maxBytes=size_log,
        backupCount=backup_count_log,
        encoding='utf-8'
    )
    err_fh.setLevel(logging.ERROR)
    err_fh.setFormatter(formatter)
    root.addHandler(err_fh)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """log = get_logger(__name__)"""
    return logging.getLogger(name)

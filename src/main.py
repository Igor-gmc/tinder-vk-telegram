from src.core.log_setup import setup_logger, get_logger
from src.core.init_data_dirs import setup_data_dirs
from src.core.config import LoggingConfig

def main():
    loger_cfg = LoggingConfig()

    # Если папки для обработки данных и логов не созданы, то создаем их
    setup_data_dirs(loger_cfg)

    setup_logger(loger_cfg)
    log = get_logger(__name__)

    log.info('Старт проекта')

if __name__ == '__main__':
    main()
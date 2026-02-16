from src.core.log_setup import setup_logger
from src.core.log_setup import get_logger
from src.core.init_data_dirs import setup_data_dirs
from src.core.config import LoggingConfig

def main():
    loger_cfg = LoggingConfig()

    # Если папки для обработки данных и логов не созданы, то создаем их
    setup_data_dirs(loger_cfg)  # используется только в main.py
    setup_logger(loger_cfg)     # используется только в main.py

    # получаем логгер для текущего файла.py
    log = get_logger(__name__)  # ничего менять не надо
    log.info('Старт проекта')   # логирование вспомогательной информации или статуса и подобное

if __name__ == '__main__':
    main()
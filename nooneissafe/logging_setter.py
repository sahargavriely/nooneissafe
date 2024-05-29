import pathlib
import logging
from logging.handlers import SysLogHandler, RotatingFileHandler


def setup_logging(log_lvl=logging.INFO, stream_to_screen=True,
                  stream_to_syslog=False):

    logs_dir = pathlib.Path(__file__).parent.parent / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    logs_path = logs_dir / 'nooneissafe.log'

    logging.root.setLevel(log_lvl)

    logging.Formatter.default_msec_format = '%s.%03d'
    format = 'nooneissafe ' \
        '%(levelname)s %(filename)s:%(lineno)d %(funcName)s - %(message)s'

    if stream_to_screen:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(f'%(asctime)s {format}'))
        logging.root.addHandler(stream_handler)

    if stream_to_syslog:
        syslog_handler = SysLogHandler(address='/dev/log')
        syslog_handler.ident = 'nooneissafe '
        syslog_handler.setFormatter(logging.Formatter(format))
        logging.root.addHandler(syslog_handler)

    file_handler = RotatingFileHandler(
        str(logs_path), maxBytes=4 * 1024 * 1024, backupCount=4)
    file_handler.setFormatter(logging.Formatter(f'%(asctime)s {format}'))
    logging.root.addHandler(file_handler)

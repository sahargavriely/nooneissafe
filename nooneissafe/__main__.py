import logging
import pathlib
import threading
import time

from .logging_setter import setup_logging
from .video import record_loop


# read this comment!
# sources might differ and won't be in an increasing order
# e.g. if you have 2 connected cameras then you should set `amount_of_cameras`
#      to 2 but it might be the case that the active sources will be [0, 2]
#      and not [0, 1] like this code assumes.

stop_signal = pathlib.Path('stop')
if stop_signal.exists():
    stop_signal.unlink()

amount_of_cameras = 100
threads = list()

setup_logging()
logger = logging.getLogger(__name__)

for source in range(amount_of_cameras):
    thread = threading.Thread(target=record_loop, args=(source,), daemon=True)
    threads.append(thread)
    thread.start()

while not stop_signal.exists():
    time.sleep(5)

logger.info('terminating')

for thread in threads:
    thread.join(timeout=3)

logger.info('terminated')

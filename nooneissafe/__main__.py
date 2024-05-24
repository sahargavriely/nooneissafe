import threading

from .logging_setter import setup_logging
from .video import record_loop


setup_logging()


amount_of_cameras = 1
threads = list()

for i in range(amount_of_cameras):
    thread = threading.Thread(target=record_loop, args=(i,), daemon=True)
    threads.append(thread)
    thread.start()

input('Press enter to stop\n')

for thread in threads:
    thread.join(timeout=3)

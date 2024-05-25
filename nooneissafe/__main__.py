import threading

from .logging_setter import setup_logging
from .video import record_loop


# read this comment!
# sources might differ and won't be in an increasing order
# e.g. if you have 2 connected cameras then you should set `amount_of_cameras`
#      to 2 but it might be the case that the active sources will be [0, 2]
#      and not [0, 1] like this code assumes.

amount_of_cameras = 1
threads = list()

setup_logging()

for source in range(amount_of_cameras):
    thread = threading.Thread(target=record_loop, args=(source,), daemon=True)
    threads.append(thread)
    thread.start()

input('Press enter to stop\n')

for thread in threads:
    thread.join(timeout=3)

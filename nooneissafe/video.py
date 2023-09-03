import contextlib
import pathlib
import time

import cv2 as cv
import numpy as np

from .utils import (
    color_retengale,
    extensive_write,
    filter_conours,
    now,
)


dt_str_f = '%Y/%m/%d/%H-%M-%S'


@contextlib.contextmanager
def capture_video():
    cap = cv.VideoCapture(0)
    cap.read()
    print('Establise clear frame')
    time.sleep(3)
    print('Camera rolling')
    print('Action')
    with contextlib.suppress(KeyboardInterrupt):
        yield cap
    print('\nCut')
    cap.release()
    cv.destroyAllWindows()


@contextlib.contextmanager
def open_video_file(file_name):
    fourcc = cv.VideoWriter_fourcc(*'XVID')
    file_path = pathlib.Path(f'database/{file_name}.avi')
    file_path.parent.mkdir(parents=True, exist_ok=True)
    out = cv.VideoWriter(str(file_path), fourcc, 20.0, (640,  480))
    print('opening video file:', file_name)
    yield out
    print('closing video file:', file_name)
    out.release()


def present_frame(frame, show):
    if not show:
        return True
    cv.imshow('frame', frame)
    if cv.waitKey(1) == ord('q'):
        return False
    return True


def record_loop(show=False, min_rec_time=10, time_between_frames=3):
    with capture_video() as cap:
        _, frame = cap.read()
        while cap.isOpened():
            pre_frame, (_, frame) = frame, cap.read()
            if not present_frame(frame, show):
                break
            time.sleep(time_between_frames)
            counters = filter_conours(pre_frame, frame)
            if not counters:
                # no movment detected
                continue
            rec_start_time = now()
            with open_video_file(now().strftime(dt_str_f)) as file:
                extensive_write(file, pre_frame, amount_to_write=25)
                color_retengale(frame, counters)
                extensive_write(file, frame)
                while (now() - rec_start_time).seconds < min_rec_time:
                    pre_frame, (_, frame) = frame, cap.read()
                    present_frame(frame, show)
                    file.write(frame)
                    if filter_conours(pre_frame, frame):
                        rec_start_time = now()
                        print('new record time:', now().strftime(dt_str_f))

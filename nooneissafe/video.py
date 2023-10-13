import contextlib
import pathlib
import time

import cv2 as cv

from .utils import (
    color_retengale,
    extensive_write,
    filter_conours,
    now,
)


dt_str_f = '%Y/%m/%d/%H-%M-%S'


@contextlib.contextmanager
def capture_video(source):
    cap = cv.VideoCapture(source)
    if cap is None or not cap.isOpened():
        msg = f'Error: unable to open camera {source=!r}'
        print(msg)
        raise ValueError(msg)
    cap.read()
    print(f'Establise clear frame {source=!r}')
    time.sleep(3)
    print(f'Camera rolling {source=!r}')
    print(f'Action {source=!r}')
    with contextlib.suppress(KeyboardInterrupt):
        yield cap
    print(f'\nCut {source=!r}')
    cap.release()
    cv.destroyAllWindows()


@contextlib.contextmanager
def open_video_file(file_path):
    fourcc = cv.VideoWriter_fourcc(*'XVID')
    file_path = pathlib.Path(f'database/{file_path}.avi')
    file_path.parent.mkdir(parents=True, exist_ok=True)
    out = cv.VideoWriter(str(file_path), fourcc, fps=20, frameSize=(640, 480))
    print('Opening video file:', file_path)
    yield out
    print('Closing video file:', file_path)
    out.release()


def present_frame(frame, show):
    if not show:
        return True
    cv.imshow('frame', frame)
    if cv.waitKey(1) == ord('q'):
        return False
    return True


def record_loop(source=0, show=False, min_rec_time=10, time_between_frames=1):
    with capture_video(source) as cap:
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
            file_path = f'{now().strftime(dt_str_f)}_{source}'
            with open_video_file(file_path) as file:
                extensive_write(file, pre_frame, amount_to_write=25)
                color_retengale(frame, counters)
                extensive_write(file, frame)
                while (now() - rec_start_time).seconds < min_rec_time:
                    pre_frame, (_, frame) = frame, cap.read()
                    present_frame(frame, show)
                    file.write(frame)
                    if filter_conours(pre_frame, frame):
                        rec_start_time = now()
                        print('New record time:', now().strftime(dt_str_f))

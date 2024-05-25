import contextlib
import logging
import pathlib
import threading
import time

import cv2 as cv

from .notification import send_email
from .utils import (
    color_rectangle,
    extensive_write,
    filter_contours,
    now,
)


dt_str_f = '%Y/%m/%d/%H-%M-%S'
db_dir = 'database'
video_prefix = 'avi'
logger = logging.getLogger(__name__)


@contextlib.contextmanager
def capture_video(source):
    cap = cv.VideoCapture(source)
    if cap is None or not cap.isOpened():
        msg = f'failed to open camera source {source}'
        logger.error(msg)
        raise ValueError(msg)
    cap.read()
    logger.info('establish clear frame source %r', source)
    time.sleep(3)
    logger.info('camera rolling source %r', source)
    logger.info('action source %r', source)
    with contextlib.suppress(KeyboardInterrupt):
        yield cap
    logger.info('\ncut source %r', source)
    cap.release()
    cv.destroyAllWindows()


@contextlib.contextmanager
def open_video_file(file_path):
    fourcc = cv.VideoWriter_fourcc(*'XVID')
    file_path = pathlib.Path(f'{db_dir}/{file_path}.{video_prefix}')
    file_path.parent.mkdir(parents=True, exist_ok=True)
    out = cv.VideoWriter(str(file_path), fourcc, fps=20, frameSize=(640, 480))
    logger.info('opening video file: %s', file_path)
    yield out
    logger.info('closing video file: %s', file_path)
    out.release()


def present_frame(frame, show):
    if not show:
        return True
    cv.imshow('frame', frame)
    if cv.waitKey(1) == ord('q'):
        return False
    return True


def save_frame(file_path, frame):
    img_path = pathlib.Path(f'database/{file_path}_frame.jpg')
    img_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info('saving framing frame: %s', img_path)
    cv.imwrite(str(img_path), frame)
    return img_path


def send_email_wrapper(img_path, video_size):
    try:
        message = f'Movement detected, capture {video_size} bytes'
        send_email(img_path, message)
    except:
        logger.exception('failed to send email %s', img_path)


def record_loop(source, show=False, min_rec_time=10, time_between_sample=1):
    with capture_video(source) as cap:
        _, frame = cap.read()
        while cap.isOpened():
            file_path = f'{now().strftime(dt_str_f)}_{source}'
            pre_frame, (_, frame) = frame, cap.read()
            if not present_frame(frame, show):
                logger.info('preset window closed, ending loop')
                break
            counters = filter_contours(pre_frame, frame)
            if not counters:
                time.sleep(time_between_sample)
                logger.debug('no movement detected')
                continue
            rec_start_time = now()
            logger.info('movement detected')
            img_path = save_frame(file_path, frame)
            with open_video_file(file_path) as file:
                extensive_write(file, pre_frame, amount_to_write=25)
                color_rectangle(frame, counters)
                extensive_write(file, frame)
                while (now() - rec_start_time).seconds < min_rec_time:
                    pre_frame, (_, frame) = frame, cap.read()
                    present_frame(frame, show)
                    file.write(frame)
                    if filter_contours(pre_frame, frame):
                        rec_start_time = now()
                        pretty_time = rec_start_time.strftime(dt_str_f)
                        logger.info('keep record alive: %s', pretty_time)
            file_path = pathlib.Path(f'{db_dir}/{file_path}.{video_prefix}')
            threading.Thread(target=send_email_wrapper,
                             args=(img_path, file_path.stat().st_size)).start()

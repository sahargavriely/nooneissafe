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
video_suffix = 'video.avi'
image_suffix = 'frame.jpg'
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
    logger.info('cut source %r', source)
    cap.release()
    cv.destroyAllWindows()


@contextlib.contextmanager
def open_video_file(base_name):
    fourcc = cv.VideoWriter_fourcc(*'XVID')
    file_path = pathlib.Path(base_name + video_suffix)
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


def save_frame(base_name, frame):
    image_path = pathlib.Path(base_name + image_suffix)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info('saving framing frame: %s', image_path)
    cv.imwrite(str(image_path), frame)
    return image_path


def send_email_wrapper(image_path, video_size):
    try:
        message = f'Movement detected, capture {video_size} bytes'
        send_email(image_path, message)
    except:
        logger.exception('failed to send email %s', image_path)


def record_loop(source, show=False, min_rec_time=10, time_between_sample=1):
    with capture_video(source) as cap:
        _, frame = cap.read()
        while cap.isOpened():
            base_name = f'database/{now().strftime(dt_str_f)}_{source}_'
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
            image_path = save_frame(base_name, frame)
            with open_video_file(base_name) as file:
                extensive_write(file, pre_frame, amount_to_write=25)
                color_rectangle(frame, counters)
                extensive_write(file, frame)
                while (now() - rec_start_time).seconds < min_rec_time:
                    pre_frame, (_, frame) = frame, cap.read()
                    present_frame(frame, show)
                    file.write(frame)
                    if filter_contours(pre_frame, frame):
                        rec_start_time = now()
                        pretty_print_time = rec_start_time.strftime(dt_str_f)
                        logger.info('keep record alive: %s', pretty_print_time)
            video_size = pathlib.Path(base_name + video_suffix).stat().st_size
            threading.Thread(target=send_email_wrapper,
                             args=(image_path, video_size,)).start()

import contextlib
import logging
import math
import pathlib
import subprocess
import tempfile
import threading
import time

import cv2 as cv

from .notification import send_notification
from .utils import (
    color_rectangle,
    extensive_write,
    filter_contours,
    now,
)


dt_str_f = '%Y/%m/%d/%H-%M-%S'
video_suffix = 'video.mp4'
image_suffix = 'frame.jpg'
sizes = [(1280, 720), (640, 480)]  # (1920, 1080) is too big
default_fps = 20.0
video_codecs = ('avc1', 'H264', 'mp4v')
video_normalize_timeout_sec = 180
logger = logging.getLogger(__name__)


@contextlib.contextmanager
def capture_video(source):
    cap = cv.VideoCapture(source)
    for w, h in sizes:
        with contextlib.suppress(Exception):
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, h)
            cap.set(cv.CAP_PROP_FRAME_WIDTH, w)
            logger.info('succefully set resolution of source %r to %sX%s',
                        source, w, h)
            break
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
def open_video_file(cap, base_name, frame):
    file_path = pathlib.Path(base_name + video_suffix)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    cap_fps = cap.get(cv.CAP_PROP_FPS)
    if not math.isfinite(cap_fps) or cap_fps <= 0:
        logger.warning('invalid camera fps (%s), falling back to %s',
                       cap_fps, default_fps)
        cap_fps = default_fps
    frame_width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    if frame_width <= 0 or frame_height <= 0:
        if frame is None:
            msg = f'missing frame data to infer dimensions for {file_path}'
            logger.error(msg)
            raise RuntimeError(msg)
        frame_height, frame_width = frame.shape[:2]
        logger.warning('invalid frame dimensions from camera, '
                       'falling back to current frame shape %sx%s',
                       frame_width, frame_height)
    frame_size = frame_width, frame_height
    out = None
    for codec in video_codecs:
        fourcc = cv.VideoWriter_fourcc(*codec)
        candidate = cv.VideoWriter(str(file_path), fourcc, cap_fps, frame_size)
        if candidate.isOpened():
            logger.info('using %s codec for video output %s', codec, file_path)
            out = candidate
            break
        logger.warning('failed to create %s writer for %s', codec, file_path)
        candidate.release()
    if out is None:
        msg = f'failed to open video writer for {file_path}'
        logger.error(msg)
        raise RuntimeError(msg)
    logger.info('opening video file: %s', file_path)
    try:
        yield out
    finally:
        logger.info('closing video file: %s', file_path)
        out.release()


def normalize_video_for_distribution(video_path):
    with tempfile.NamedTemporaryFile(
        suffix='.mp4',
        delete=False,
        dir=str(video_path.parent),
    ) as tmp:
        normalized_path = pathlib.Path(tmp.name)
    ffmpeg_cmd = [
        'ffmpeg',
        '-y',
        '-i',
        str(video_path),
        '-an',
        '-c:v',
        'libx264',
        '-profile:v',
        'baseline',
        '-level',
        '3.1',
        '-pix_fmt',
        'yuv420p',
        '-preset',
        'veryfast',
        '-crf',
        '27',
        '-movflags',
        '+faststart',
        '-vf',
        'scale=trunc(iw/2)*2:trunc(ih/2)*2',
        str(normalized_path),
    ]
    try:
        subprocess.run(
            ffmpeg_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=video_normalize_timeout_sec,
        )
    except FileNotFoundError:
        logger.warning('ffmpeg is not available, keeping original video %s',
                       video_path)
        with contextlib.suppress(FileNotFoundError):
            normalized_path.unlink()
        return
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        logger.warning('failed to normalize output video %s: %s',
                       video_path, error)
        with contextlib.suppress(FileNotFoundError):
            normalized_path.unlink()
        return
    normalized_path.replace(video_path)
    logger.info('normalized video to H.264 MP4: %s', video_path)


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


def send_notification_wrapper(base_name):
    try:
        image_path = pathlib.Path(base_name + image_suffix)
        video_path = pathlib.Path(base_name + video_suffix)
        normalize_video_for_distribution(video_path)
        mb = video_path.stat().st_size / 2**20
        msg = f'Movement detected, capture {base_name} with *{mb:.1f} MB*'
        send_notification(image_path, video_path, msg)
    except:
        logger.exception('failed to send notification %r', base_name)


def record_loop(source, show=False, min_rec_time=10, time_between_sample=1):
    with capture_video(source) as cap:
        captured, frame = cap.read()
        if not captured:
            msg = f'failed to read initial frame from source {source}'
            logger.error(msg)
            raise RuntimeError(msg)
        capture_fps = cap.get(cv.CAP_PROP_FPS)
        if not math.isfinite(capture_fps) or capture_fps <= 0:
            capture_fps = default_fps
        fphs = max(int(capture_fps) // 2, 1)  # frames per half a second
        while cap.isOpened():
            base_name = f'database/{now().strftime(dt_str_f)}_{source}_'
            pre_frame, (captured, frame) = frame, cap.read()
            if not captured:
                logger.warning(
                    'failed to read frame from source %r, ending loop',
                    source,
                )
                break
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
            save_frame(base_name, frame)
            with open_video_file(cap, base_name, frame) as file:
                extensive_write(file, pre_frame, amount_to_write=fphs)
                color_rectangle(frame, counters)
                extensive_write(file, frame, amount_to_write=fphs)
                while (now() - rec_start_time).seconds < min_rec_time:
                    pre_frame, (captured, frame) = frame, cap.read()
                    if not captured:
                        logger.warning('failed to read frame while recording '
                                       'source %r, ending recording loop',
                                       source)
                        break
                    present_frame(frame, show)
                    file.write(frame)
                    if filter_contours(pre_frame, frame):
                        rec_start_time = now()
                        pretty_print_time = rec_start_time.strftime(dt_str_f)
                        logger.info('keep record alive: %s', pretty_print_time)
            threading.Thread(target=send_notification_wrapper,
                             args=(base_name,)).start()

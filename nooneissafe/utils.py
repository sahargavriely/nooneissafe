import datetime
import mimetypes
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass

import cv2 as cv
import numpy as np


def color_rectangle(frame, contours):
    for contour in contours:
        if cv.contourArea(contour) < 500:
            # too small: skip!
            continue
        x, y, w, h = cv.boundingRect(contour)
        cv.rectangle(img=frame, pt1=(x, y), pt2=(x + w, y + h),
                     color=(0, 255, 0))


def extensive_write(file, frame, amount_to_write=15):
    for _ in range(amount_to_write):
        file.write(frame)


@dataclass
class MotionDetectionResult:
    contours: list
    motion_pixels: int
    motion_ratio: float
    has_motion: bool


class MotionDetector:
    def __init__(
        self,
        history=200,
        var_threshold=32,
        min_contour_area=900,
        min_motion_ratio=0.003,
        required_motion_frames=2,
        warmup_frames=3,
    ):
        self.min_contour_area = min_contour_area
        self.min_motion_ratio = min_motion_ratio
        self.required_motion_frames = required_motion_frames
        self.warmup_frames = warmup_frames
        self._frame_count = 0
        self._positive_streak = 0
        self._kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
        self._subtractor = cv.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=False,
        )

    def detect(self, frame):
        clean_frame = _clean_frame(frame)
        fg_mask = self._subtractor.apply(clean_frame)
        thresh_mask = cv.threshold(
            src=fg_mask,
            thresh=200,
            maxval=255,
            type=cv.THRESH_BINARY,
        )[1]
        thresh_mask = cv.morphologyEx(
            src=thresh_mask,
            op=cv.MORPH_OPEN,
            kernel=self._kernel,
            iterations=1,
        )
        thresh_mask = cv.morphologyEx(
            src=thresh_mask,
            op=cv.MORPH_CLOSE,
            kernel=self._kernel,
            iterations=2,
        )
        contours, _ = cv.findContours(
            image=thresh_mask,
            mode=cv.RETR_EXTERNAL,
            method=cv.CHAIN_APPROX_SIMPLE,
        )
        filtered_contours = [
            contour for contour in contours
            if cv.contourArea(contour) > self.min_contour_area
        ]
        motion_pixels = int(cv.countNonZero(thresh_mask))
        motion_ratio = motion_pixels / float(thresh_mask.size)
        has_positive_signal = (
            bool(filtered_contours) and motion_ratio >= self.min_motion_ratio
        )
        self._frame_count += 1
        if self._frame_count <= self.warmup_frames:
            self._positive_streak = 0
            return MotionDetectionResult(
                contours=filtered_contours,
                motion_pixels=motion_pixels,
                motion_ratio=motion_ratio,
                has_motion=False,
            )
        if has_positive_signal:
            self._positive_streak += 1
        else:
            self._positive_streak = 0
        return MotionDetectionResult(
            contours=filtered_contours,
            motion_pixels=motion_pixels,
            motion_ratio=motion_ratio,
            has_motion=self._positive_streak >= self.required_motion_frames,
        )


def filter_contours(f1, f2, thresh=50, accepted_size=500):
    f1 = _clean_frame(f1)
    f2 = _clean_frame(f2)
    diff_f = cv.absdiff(src1=f1, src2=f2)
    kernel = np.ones((5, 5))
    diff_f = cv.dilate(diff_f, kernel, 1)
    thresh_f = cv.threshold(src=diff_f, thresh=thresh, maxval=255,
                            type=cv.THRESH_BINARY)[1]
    contours, _ = cv.findContours(image=thresh_f, mode=cv.RETR_EXTERNAL,
                                  method=cv.CHAIN_APPROX_SIMPLE)
    filtered_contours = [contour for contour in contours
                         if cv.contourArea(contour) > accepted_size]
    return filtered_contours


def now():
    return datetime.datetime.now()


def _clean_frame(frame):
    frame = cv.cvtColor(src=frame, code=cv.COLOR_BGR2GRAY)
    frame = cv.GaussianBlur(src=frame, ksize=(5, 5), sigmaX=0)
    return frame


def _encode_multipart_form_data(fields, files):
    boundary = f'----NoOneIsSafeBoundary{uuid.uuid4().hex}'
    body = bytearray()
    for field_name, value in fields.items():
        if value is None:
            continue
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        disposition = f'Content-Disposition: form-data; name="{field_name}"'
        body.extend(f'{disposition}\r\n\r\n'.encode('utf-8'))
        body.extend(str(value).encode('utf-8'))
        body.extend(b'\r\n')
    for field_name, file_path in files:
        mime_type = mimetypes.guess_type(file_path.name)[0]
        if mime_type is None:
            mime_type = 'application/octet-stream'
        with file_path.open('rb') as file_handle:
            payload = file_handle.read()
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        disposition = (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{file_path.name}"'
        )
        body.extend(f'{disposition}\r\n'.encode('utf-8'))
        body.extend(f'Content-Type: {mime_type}\r\n\r\n'.encode('utf-8'))
        body.extend(payload)
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    content_type = f'multipart/form-data; boundary={boundary}'
    return bytes(body), content_type


def post_multipart(url, fields, files, timeout, headers=None):
    body, content_type = _encode_multipart_form_data(fields, files)
    request_headers = {'Content-Type': content_type}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        body = error.read().decode('utf-8', errors='replace')
        raise RuntimeError(
            f'HTTP {error.code} while posting multipart to {url}: {body}'
        ) from error

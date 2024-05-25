import datetime

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


def extensive_write(file, frame, amount_to_write=100):
    for _ in range(amount_to_write):
        file.write(frame)


def filter_contours(f1, f2, thresh=50, accepted_size=500):
    f1 = _clean_frame(f1)
    f2 = _clean_frame(f2)
    diff_f = cv.absdiff(src1=f1, src2=f2)
    kernel = np.ones((5, 5))
    diff_f = cv.dilate(diff_f, kernel, 1)
    thresh_f = cv.threshold(src=diff_f, thresh=thresh, maxval=1,
                            type=cv.THRESH_BINARY)[1]
    contours, _ = cv.findContours(image=thresh_f, mode=cv.RETR_EXTERNAL,
                                  method=cv.CHAIN_APPROX_SIMPLE)
    filtered_contours = [contour for contour in contours
                         if cv.contourArea(contour) > accepted_size]
    return filtered_contours


def now():
    return datetime.datetime.now()


def _clean_frame(frame):
    frame = cv.cvtColor(src=frame, code=cv.COLOR_BGR2RGB)
    frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    frame = cv.GaussianBlur(src=frame, ksize=(5, 5), sigmaX=0)
    return frame

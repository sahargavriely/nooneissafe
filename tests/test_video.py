import unittest
from unittest import mock

import numpy as np

from nooneissafe import video


class _DummyCapture:

    def __init__(self, fps, width, height):
        self._mapping = {
            video.cv.CAP_PROP_FPS: fps,
            video.cv.CAP_PROP_FRAME_WIDTH: width,
            video.cv.CAP_PROP_FRAME_HEIGHT: height,
        }

    def get(self, prop):
        return self._mapping[prop]


class OpenVideoFileTests(unittest.TestCase):

    @mock.patch.object(video.cv, 'VideoWriter_fourcc')
    @mock.patch.object(video.cv, 'VideoWriter')
    def test_open_video_file_falls_back_to_default_fps_and_frame_size(
        self,
        video_writer,
        video_writer_fourcc,
    ):
        cap = _DummyCapture(fps=0, width=0, height=0)
        frame = np.zeros((8, 16, 3), dtype=np.uint8)
        opened_writer = mock.Mock()
        opened_writer.isOpened.return_value = True
        video_writer.return_value = opened_writer
        video_writer_fourcc.return_value = 1234

        with video.open_video_file(cap, '/tmp/capture_', frame):
            pass

        _, _, used_fps, used_size = video_writer.call_args.args
        self.assertEqual(used_fps, video.default_fps)
        self.assertEqual(used_size, (16, 8))
        opened_writer.release.assert_called_once()

    @mock.patch.object(video.cv, 'VideoWriter_fourcc')
    @mock.patch.object(video.cv, 'VideoWriter')
    def test_open_video_file_falls_back_codec_when_xvid_fails(
        self,
        video_writer,
        video_writer_fourcc,
    ):
        cap = _DummyCapture(fps=24, width=16, height=8)
        frame = np.zeros((8, 16, 3), dtype=np.uint8)
        failed_writer = mock.Mock()
        failed_writer.isOpened.return_value = False
        fallback_writer = mock.Mock()
        fallback_writer.isOpened.return_value = True
        video_writer.side_effect = [failed_writer, fallback_writer]
        video_writer_fourcc.side_effect = [1111, 2222]

        with video.open_video_file(cap, '/tmp/capture_', frame):
            pass

        self.assertEqual(video_writer.call_count, 2)
        failed_writer.release.assert_called_once()
        fallback_writer.release.assert_called_once()


if __name__ == '__main__':
    unittest.main()

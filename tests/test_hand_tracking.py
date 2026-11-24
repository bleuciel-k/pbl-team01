import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from app.hand_tracking import annotate_frame, track_capture


def hand_result(*labels):
    points = [SimpleNamespace(x=0.2 + i * 0.02, y=0.5) for i in range(21)]
    return SimpleNamespace(
        hand_landmarks=[points for _ in labels],
        handedness=[[SimpleNamespace(category_name=label)] for label in labels],
    )


class HandTrackingTests(unittest.TestCase):
    def test_us05_annotates_all_landmarks_and_labels(self):
        """US-05の追跡プロトタイプで、現在のフレームに両手を描画することを確認する。"""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        result = hand_result("Left", "Right")

        with (
            patch("app.hand_tracking.cv2.circle") as circle,
            patch("app.hand_tracking.cv2.putText") as put_text,
        ):
            annotate_frame(frame, result, 27.5)

        self.assertEqual(circle.call_count, 42)
        self.assertEqual(
            [call.args[1] for call in put_text.call_args_list],
            ["Left", "Right", "Tracking FPS: 27.5 | Hands: 2"],
        )

    def test_us05_uses_fresh_results_when_hands_leave_and_return(self):
        """US-05の追跡プロトタイプで、各フレームの検出結果（2手、0手、1手）が反映されることを確認する。"""
        frame = np.full((8, 8, 3), (10, 20, 30), dtype=np.uint8)
        capture = Mock()
        capture.get.return_value = 25.0
        capture.read.side_effect = [(True, frame)] * 3 + [(False, None)]
        landmarker = Mock()
        landmarker.detect_for_video.side_effect = [
            hand_result("Left", "Right"), hand_result(), hand_result("Left")
        ]

        counts, fps = track_capture(capture, landmarker, camera=False, headless=True)

        self.assertEqual(dict(counts), {2: 1, 0: 1, 1: 1})
        self.assertGreater(fps, 0)
        calls = landmarker.detect_for_video.call_args_list
        self.assertEqual([call.args[1] for call in calls], [0, 40, 80])
        self.assertEqual(calls[0].args[0].numpy_view()[0, 0].tolist(), [30, 20, 10])

    def test_us05_camera_read_error_is_reported(self):
        """US-05の追跡プロトタイプで、カメラ入力の読み取り失敗が通知されることを確認する。"""
        capture = Mock()
        capture.read.return_value = False, None

        with self.assertRaisesRegex(RuntimeError, "Camera frame could not be read"):
            track_capture(capture, Mock(), camera=True, headless=True)

    def test_us05_empty_recording_is_reported(self):
        """US-05の追跡プロトタイプで、処理できるフレームが録画にない場合にエラーになることを確認する。"""
        capture = Mock()
        capture.get.return_value = float("nan")
        capture.read.return_value = False, None

        with self.assertRaisesRegex(RuntimeError, "No frames were processed"):
            track_capture(capture, Mock(), camera=False, headless=True)

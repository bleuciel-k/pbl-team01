import json
import socket
import unittest
from types import SimpleNamespace

from app.landmark_stream import send_landmarks


class LandmarkStreamTests(unittest.TestCase):
    def setUp(self):
        self.receiver = self.enterContext(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        self.receiver.bind(("127.0.0.1", 0))
        self.receiver.settimeout(1)
        self.sender = self.enterContext(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))

    def receive_frame(self, result):
        send_landmarks(self.sender, 7, 233, result, port=self.receiver.getsockname()[1])
        packet, address = self.receiver.recvfrom(4096)
        self.assertEqual(address[0], "127.0.0.1")
        return json.loads(packet)

    def test_us05_sends_both_hands_with_original_coordinates(self):
        """US-05の検証用に、両手の座標とフレーム情報をローカルUDPで送信する。"""
        left = [SimpleNamespace(x=0.2, y=0.5, z=-0.1)] * 21
        right = [SimpleNamespace(x=0.8, y=0.5, z=0.1)] * 21
        result = SimpleNamespace(
            hand_landmarks=[left, right],
            handedness=[[SimpleNamespace(category_name=name)] for name in ("Left", "Right")],
        )

        self.assertEqual(self.receive_frame(result), {
            "version": 1,
            "sequence": 7,
            "timestamp_ms": 233,
            "hands": [
                {"side": "Left", "landmarks": [[0.2, 0.5, -0.1]] * 21},
                {"side": "Right", "landmarks": [[0.8, 0.5, 0.1]] * 21},
            ],
        })

    def test_us05_sends_an_empty_frame_when_tracking_is_lost(self):
        """US-05の検証用に、手を見失ったときも空のフレームを送信する。"""
        result = SimpleNamespace(hand_landmarks=[], handedness=[])
        self.assertEqual(self.receive_frame(result)["hands"], [])

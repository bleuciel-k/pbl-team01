import json
import math
import socket
from functools import partial


def send_landmarks(sock, sequence, timestamp_ms, result, *, port=5005):
    hands = []
    for points, categories in zip(result.hand_landmarks, result.handedness):
        if not categories or categories[0].category_name not in ("Left", "Right"):
            continue
        landmarks = [[point.x, point.y, point.z] for point in points]
        if len(landmarks) == 21 and all(math.isfinite(value) for point in landmarks for value in point):
            hands.append({"side": categories[0].category_name, "landmarks": landmarks})

    # 手を検出できなかったフレームも送信し、Godot側の前回表示を消す。
    packet = {
        # JSONの項目を変える場合は landmark_receiver.gd の検証処理も確認する。
        "version": 1,
        "sequence": sequence,
        "timestamp_ms": timestamp_ms,
        "hands": hands,
    }
    data = json.dumps(packet, separators=(",", ":"), allow_nan=False).encode("utf-8")
    try:
        sock.sendto(data, ("127.0.0.1", port))
    except BlockingIOError:
        # 送信バッファが満杯の場合は次のフレームを優先する。
        pass


def main():
    from app.hand_tracking import main as run_tracking

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setblocking(False)
        return run_tracking(on_result=partial(send_landmarks, sock))


if __name__ == "__main__":
    raise SystemExit(main())

"""Run a two-hand MediaPipe preview from a webcam or a recorded video."""

import argparse
from collections import Counter
import math
import os
from pathlib import Path
import sys
from time import perf_counter

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision


WINDOW_TITLE = "Gesture Magic Battle - Hand Tracking"
HAND_CONNECTIONS = vision.HandLandmarksConnections.HAND_CONNECTIONS


def annotate_frame(frame, result, fps):
    height, width = frame.shape[:2]
    for landmarks, categories in zip(result.hand_landmarks, result.handedness):
        points = [
            (round(point.x * (width - 1)), round(point.y * (height - 1)))
            for point in landmarks
        ]
        color = (80, 220, 100)
        for connection in HAND_CONNECTIONS:
            cv2.line(frame, points[connection.start], points[connection.end], color, 2, cv2.LINE_AA)
        for point in points:
            cv2.circle(frame, point, 3, (245, 245, 245), -1, cv2.LINE_AA)

        label = categories[0].category_name if categories else "Unknown"
        wrist_x, wrist_y = points[0]
        label_position = (max(0, min(wrist_x, width - 80)), max(24, min(wrist_y - 8, height - 1)))
        cv2.putText(frame, label, label_position, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    status = f"Tracking FPS: {fps:.1f} | Hands: {len(result.hand_landmarks)}"
    (text_width, _), baseline = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
    cv2.rectangle(frame, (6, 4), (text_width + 18, 28 + baseline + 4), (0, 0, 0), -1)
    cv2.putText(frame, status, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)


def track_capture(capture, landmarker, *, camera, headless):
    counts = Counter()
    frames = 0
    last_timestamp = -1
    started = perf_counter()
    source_fps = None
    if not camera:
        source_fps = capture.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(source_fps) or source_fps <= 0:
            source_fps = 30.0

    while True:
        ok, frame = capture.read()
        if not ok:
            if camera:
                raise RuntimeError("Camera frame could not be read. Check camera permissions and connections.")
            break

        if camera:
            elapsed_ms = int((perf_counter() - started) * 1000)
        else:
            elapsed_ms = int(frames * 1000 / source_fps)

        # VIDEOモードでは、起動直後も含めてタイムスタンプを厳密に増加させる必要がある。
        timestamp = max(elapsed_ms, last_timestamp + 1)
        last_timestamp = timestamp
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
        counts[len(result.hand_landmarks)] += 1
        frames += 1

        if not headless:
            annotate_frame(frame, result, frames / (perf_counter() - started))
            cv2.imshow(WINDOW_TITLE, frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
            if cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) == 0:
                break

    if not frames:
        raise RuntimeError("No frames were processed.")
    return counts, frames / (perf_counter() - started)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True, help="Path to the MediaPipe .task model.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--camera", type=int, default=0, help="Webcam device index (default: 0).")
    source.add_argument("--video", type=Path, help="Read a recorded video instead of a webcam.")
    parser.add_argument("--headless", action="store_true", help="Print tracking statistics without opening a window.")
    args = parser.parse_args(argv)

    if not args.model.is_file():
        parser.error(f"model file does not exist: {args.model}")
    if args.video is not None and not args.video.is_file():
        parser.error(f"video file does not exist: {args.video}")
    if sys.platform.startswith("linux") and not args.headless and not os.environ.get("DISPLAY"):
        parser.error("no graphical display is configured. Use --headless for video verification.")

    camera = args.video is None
    capture_source = args.camera if camera else str(args.video)
    capture = cv2.VideoCapture(capture_source)
    try:
        if not capture.isOpened():
            raise RuntimeError(f"Could not open {'camera' if camera else 'video'}: {capture_source}")
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(args.model.resolve())),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
        )
        with vision.HandLandmarker.create_from_options(options) as landmarker:
            counts, fps = track_capture(capture, landmarker, camera=camera, headless=args.headless)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, ValueError, cv2.error) as error:
        print(f"Hand tracking failed: {error}", file=sys.stderr)
        return 1
    finally:
        capture.release()
        if not args.headless:
            cv2.destroyAllWindows()

    print(f"Processed {counts.total()} frames at {fps:.1f} tracking FPS.")
    print(f"Frames by detected hands: 0={counts[0]}, 1={counts[1]}, 2={counts[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

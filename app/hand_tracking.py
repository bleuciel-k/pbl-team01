"""Run a two-hand MediaPipe preview from a webcam or a recorded video."""

import argparse
from collections import Counter
import math
import os
from pathlib import Path
import sys
from time import perf_counter
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

from app.gesture_classifier import GestureClassifier, GestureDataset, extract_features


WINDOW_TITLE = "Gesture Magic Battle - Hand Tracking"
HAND_CONNECTIONS = vision.HandLandmarksConnections.HAND_CONNECTIONS
DEFAULT_MODEL_PATH = Path(".venv/hand_landmarker.task")
HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)


def _find_japanese_font():
    candidates = [
        "/usr/share/fonts/haranoaji/HaranoAjiGothic-Regular.otf",
        "/usr/share/fonts/google-noto-sans-mono-cjk-vf-fonts/NotoSansMonoCJK-VF.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


_JP_FONT_PATH = _find_japanese_font()


def _draw_japanese_text(frame, text, position, font_size=18, color=(255, 255, 255)):
    """Draw Japanese text onto a BGR OpenCV frame using Pillow if a font is available."""
    if _JP_FONT_PATH is None:
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
    except ImportError:
        return
    font = ImageFont.truetype(_JP_FONT_PATH, font_size)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil_img)
    draw.text(position, text, font=font, fill=(color[2], color[1], color[0]))
    frame[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)


def ensure_model_file(model_path: Path) -> Path:
    """Download the MediaPipe hand landmarker model if it does not exist."""
    if not model_path.is_file():
        model_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading hand_landmarker.task to {model_path}...", file=sys.stderr)
        urllib.request.urlretrieve(HAND_LANDMARKER_MODEL_URL, model_path)
    return model_path


def annotate_frame(frame, result, fps, *, mirrored=False, classifier=None, sample_count=0):
    height, width = frame.shape[:2]
    for landmarks, categories in zip(result.hand_landmarks, result.handedness):
        points = [
            (round(point.x * (width - 1)), round(point.y * (height - 1)))
            for point in landmarks
        ]
        if mirrored:
            points = [(width - 1 - x, y) for x, y in points]
        color = (80, 220, 100)
        for connection in HAND_CONNECTIONS:
            cv2.line(frame, points[connection.start], points[connection.end], color, 2, cv2.LINE_AA)
        for point in points:
            cv2.circle(frame, point, 3, (245, 245, 245), -1, cv2.LINE_AA)

        handedness = categories[0].category_name if categories else "Unknown"
        label = handedness
        if classifier is not None:
            features = extract_features(landmarks, handedness)
            gesture, dist = classifier.predict(features)
            dist_text = f" ({dist:.2f})" if dist is not None else ""
            label = f"{handedness} | {gesture}{dist_text}"
        wrist_x, wrist_y = points[0]
        label_position = (max(0, min(wrist_x, width - 220)), max(24, min(wrist_y - 8, height - 1)))
        cv2.putText(frame, label, label_position, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    status = f"Tracking FPS: {fps:.1f} | Hands: {len(result.hand_landmarks)}"
    if classifier is not None:
        status += f" | Samples: {sample_count}"
        _draw_japanese_text(
            frame,
            "使い方: [1-5] ポーズ登録 / [c] データ消去 / [q] 終了",
            (12, 46),
            font_size=18,
            color=(255, 255, 255),
        )
    (text_width, _), baseline = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
    cv2.rectangle(frame, (6, 4), (text_width + 18, 28 + baseline + 4), (0, 0, 0), -1)
    cv2.putText(frame, status, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)


def track_capture(capture, landmarker, *, camera, headless, dataset=None, classifier=None):
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
            preview = cv2.flip(frame, 1) if camera else frame
            sample_count = len(dataset.features) if dataset is not None else 0
            annotate_frame(
                preview,
                result,
                frames / (perf_counter() - started),
                mirrored=camera,
                classifier=classifier,
                sample_count=sample_count,
            )
            cv2.imshow(WINDOW_TITLE, preview)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if dataset is not None and classifier is not None:
                if ord("1") <= key <= ord("5") and result.hand_landmarks:
                    class_name = f"Class_{chr(key)}"
                    handedness = result.handedness[0][0].category_name if result.handedness[0] else "Right"
                    features = extract_features(result.hand_landmarks[0], handedness)
                    dataset.add_sample(features, class_name)
                    dataset.save()
                    classifier.fit(dataset.features, dataset.labels)
                elif key == ord("c"):
                    dataset.clear()
                    dataset.save()
                    classifier.fit(dataset.features, dataset.labels)
            if cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) == 0:
                break

    if not frames:
        raise RuntimeError("No frames were processed.")
    return counts, frames / (perf_counter() - started)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Path to the MediaPipe .task model (default: {DEFAULT_MODEL_PATH}).",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--camera", type=int, default=0, help="Webcam device index (default: 0).")
    source.add_argument("--video", type=Path, help="Read a recorded video instead of a webcam.")
    parser.add_argument("--headless", action="store_true", help="Print tracking statistics without opening a window.")
    parser.add_argument("--dataset", type=Path, default=Path("data/gestures.json"), help="Path to gesture dataset JSON.")
    parser.add_argument("--threshold", type=float, default=0.6, help="Distance threshold for Unknown classification.")
    args = parser.parse_args(argv)

    ensure_model_file(args.model)
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
        dataset = GestureDataset(args.dataset)
        dataset.load()
        classifier = GestureClassifier(distance_threshold=args.threshold)
        classifier.fit(dataset.features, dataset.labels)
        with vision.HandLandmarker.create_from_options(options) as landmarker:
            counts, fps = track_capture(
                capture,
                landmarker,
                camera=camera,
                headless=args.headless,
                dataset=dataset,
                classifier=classifier,
            )
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

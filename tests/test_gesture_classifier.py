"""Tests for gesture feature extraction and k-NN classification."""

from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from app.gesture_classifier import GestureClassifier, GestureDataset, extract_features


def _make_landmarks(coords):
    return [SimpleNamespace(x=float(x), y=float(y), z=float(z)) for x, y, z in coords]


class GestureClassifierTests(unittest.TestCase):
    def test_req_proto_extract_features_translation_and_scale_invariant(self):
        """REQ-PROTO: 特徴量抽出が手首原点への平行移動とスケールに不変であることを確認する。"""
        base = [(i * 0.01, i * 0.02, 0.0) for i in range(21)]
        shifted_scaled = [(x * 2.5 + 0.3, y * 2.5 - 0.1, z * 2.5) for x, y, z in base]

        feat_base = extract_features(_make_landmarks(base), "Right")
        feat_shifted = extract_features(_make_landmarks(shifted_scaled), "Right")

        self.assertEqual(feat_base.shape, (63,))
        np.testing.assert_allclose(feat_base, feat_shifted, atol=1e-6)

    def test_req_proto_extract_features_mirrors_left_hand_to_right(self):
        """REQ-PROTO: 左手の鏡像ランドマークが右手と同じ特徴量に正規化されることを確認する。"""
        right_coords = [(0.5 + i * 0.01, 0.5 - i * 0.01, 0.0) for i in range(21)]
        left_coords = [(0.5 - i * 0.01, 0.5 - i * 0.01, 0.0) for i in range(21)]

        feat_right = extract_features(_make_landmarks(right_coords), "Right")
        feat_left = extract_features(_make_landmarks(left_coords), "Left")

        np.testing.assert_allclose(feat_right, feat_left, atol=1e-6)

    def test_req_proto_knn_classifier_predicts_known_and_unknown(self):
        """REQ-PROTO: k-NN分類器が既知クラスを分類し、しきい値超えをUnknownと判定することを確認する。"""
        classifier = GestureClassifier(n_neighbors=3, distance_threshold=0.5)
        self.assertEqual(classifier.predict(np.zeros(63)), ("Unknown", None))

        c1 = np.zeros(63)
        c1[3] = 1.0
        c2 = np.zeros(63)
        c2[4] = 1.0

        features = [c1, c1 + 0.05, c2, c2 + 0.05]
        labels = ["Class_1", "Class_1", "Class_2", "Class_2"]
        classifier.fit(features, labels)

        label, dist = classifier.predict(c1 + 0.02)
        self.assertEqual(label, "Class_1")
        self.assertIsNotNone(dist)
        self.assertLess(dist, 0.5)

        far_away = np.ones(63) * 5.0
        label_unknown, dist_unknown = classifier.predict(far_away)
        self.assertEqual(label_unknown, "Unknown")
        self.assertGreater(dist_unknown, 0.5)

    def test_req_proto_dataset_save_and_load(self):
        """REQ-PROTO: データセットのJSON保存と読込が正しく動作することを確認する。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "gestures.json"
            dataset = GestureDataset(path)
            dataset.add_sample(np.arange(63, dtype=float), "Class_1")
            dataset.save()

            loaded = GestureDataset(path)
            loaded.load()
            self.assertEqual(len(loaded.features), 1)
            self.assertEqual(loaded.labels, ["Class_1"])
            np.testing.assert_allclose(loaded.features[0], np.arange(63, dtype=float))

            loaded.clear()
            self.assertEqual(len(loaded.features), 0)
            self.assertEqual(loaded.labels, [])


if __name__ == "__main__":
    unittest.main()

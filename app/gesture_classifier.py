"""Feature extraction and k-NN gesture classification for hand landmarks."""

import json
from pathlib import Path

import numpy as np
from sklearn.neighbors import KNeighborsClassifier


def extract_features(landmarks, handedness: str = "Right") -> np.ndarray:
    """Convert 21 MediaPipe hand landmarks into a translation-, scale-, and handedness-invariant 63D vector."""
    coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float64)
    # 手首（インデックス0）を原点に平行移動する
    coords = coords - coords[0]
    # 左手はX軸を反転して右手系に揃える
    if handedness == "Left":
        coords[:, 0] = -coords[:, 0]
    flat = coords.flatten()
    norm = np.linalg.norm(flat)
    if norm > 0:
        flat = flat / norm
    return flat


class GestureDataset:
    """Stores labeled hand gesture feature vectors and persists them to JSON."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.features: list[np.ndarray] = []
        self.labels: list[str] = []

    def add_sample(self, features: np.ndarray, label: str) -> None:
        self.features.append(np.asarray(features, dtype=np.float64))
        self.labels.append(label)

    def clear(self) -> None:
        self.features.clear()
        self.labels.clear()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "samples": [
                {"label": label, "features": feat.tolist()}
                for label, feat in zip(self.labels, self.features)
            ]
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self.path.is_file():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.clear()
        for item in payload.get("samples", []):
            self.features.append(np.asarray(item["features"], dtype=np.float64))
            self.labels.append(item["label"])


class GestureClassifier:
    """k-NN classifier with distance-threshold rejection for unknown poses."""

    def __init__(self, n_neighbors: int = 3, distance_threshold: float = 0.6):
        self.n_neighbors = n_neighbors
        self.distance_threshold = distance_threshold
        self._model: KNeighborsClassifier | None = None

    def fit(self, features: list[np.ndarray], labels: list[str]) -> None:
        if not features:
            self._model = None
            return
        k = min(self.n_neighbors, len(features))
        model = KNeighborsClassifier(n_neighbors=k, metric="euclidean")
        model.fit(np.vstack(features), labels)
        self._model = model

    def predict(self, features: np.ndarray) -> tuple[str, float | None]:
        if self._model is None:
            return "Unknown", None
        vec = np.asarray(features, dtype=np.float64).reshape(1, -1)
        distances, _ = self._model.kneighbors(vec, n_neighbors=1)
        min_dist = float(distances[0, 0])
        if min_dist > self.distance_threshold:
            return "Unknown", min_dist
        label = str(self._model.predict(vec)[0])
        return label, min_dist

"""Train and evaluate the hybrid Isolation Forest + Random Forest detection ensemble."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from .features import FEATURE_NAMES
from .generate_dataset import generate_dataset

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def train(data_dir=DEFAULT_DATA_DIR, artifact_dir=DEFAULT_ARTIFACT_DIR, *, regenerate=False):
    data_dir, artifact_dir = Path(data_dir), Path(artifact_dir)
    train_path = data_dir / "training_dataset.csv"
    if regenerate or not train_path.exists():
        generate_dataset(data_dir)

    frame = pd.read_csv(train_path)
    missing = [name for name in FEATURE_NAMES + ["label"] if name not in frame.columns]
    if missing:
        raise ValueError(f"Training dataset is missing required columns: {missing}")
    frame = frame.dropna(subset=FEATURE_NAMES + ["label"])
    x = frame[FEATURE_NAMES].astype(float)
    y = frame["label"].astype(str)

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )
    scaler = StandardScaler().fit(x_train)
    scaler.set_output(transform="pandas")
    x_train_scaled = scaler.transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    forest = RandomForestClassifier(
        n_estimators=220, max_depth=14, min_samples_leaf=2,
        class_weight="balanced_subsample", random_state=42, n_jobs=-1,
    )
    forest.fit(x_train_scaled, y_train)
    predictions = forest.predict(x_test_scaled)
    accuracy = float(accuracy_score(y_test, predictions))
    f1 = float(f1_score(y_test, predictions, average="weighted"))

    isolation = IsolationForest(
        n_estimators=180, contamination=0.08, max_samples="auto", random_state=42, n_jobs=-1
    )
    isolation.fit(x_train_scaled)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(forest, artifact_dir / "random_forest.joblib")
    joblib.dump(isolation, artifact_dir / "isolation_forest.joblib")
    joblib.dump(scaler, artifact_dir / "scaler.joblib")
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "samples": int(len(frame)),
        "train_samples": int(len(x_train)),
        "test_samples": int(len(x_test)),
        "features": FEATURE_NAMES,
        "accuracy": round(accuracy, 4),
        "weighted_f1": round(f1, 4),
        "classes": sorted(y.unique().tolist()),
        "class_distribution": y.value_counts().to_dict(),
        "sklearn_version": __import__("sklearn").__version__,
    }
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    try:
        from .predict import clear_model_cache

        clear_model_cache()
    except Exception:
        pass
    print(classification_report(y_test, predictions))
    print(f"Saved ensemble artifacts to {artifact_dir} (accuracy={accuracy:.3f}, f1={f1:.3f})")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the SENTINELFLOW threat detection ensemble.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--regenerate", action="store_true", help="Regenerate the synthetic dataset first.")
    args = parser.parse_args()
    train(Path(args.data_dir), Path(args.artifact_dir), regenerate=args.regenerate)

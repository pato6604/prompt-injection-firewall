from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.pipeline import Pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "ml" / "data"
MODEL_DIR = REPO_ROOT / "ml" / "models" / "tfidf_lr_v1"
VAL_F1_THRESHOLD = 0.88


def _load_split(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    return pd.read_csv(path)


def _class_counts(df: pd.DataFrame) -> dict[int, int]:
    counts = df["label"].value_counts().sort_index()
    return {int(label): int(count) for label, count in counts.items()}


def _metrics(y_true: pd.Series, y_pred: Any) -> dict[str, Any]:
    report = classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        output_dict=True,
        zero_division=0,
    )
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)

    return {
        "precision_macro": float(report["macro avg"]["precision"]),
        "recall_macro": float(report["macro avg"]["recall"]),
        "f1_macro": float(macro_f1),
        "by_class": {
            0: {
                "precision": float(report["0"]["precision"]),
                "recall": float(report["0"]["recall"]),
                "f1": float(report["0"]["f1-score"]),
            },
            1: {
                "precision": float(report["1"]["precision"]),
                "recall": float(report["1"]["recall"]),
                "f1": float(report["1"]["f1-score"]),
            },
        },
    }


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_yaml_scalar(item) for item in value) + "]"
    if value is None:
        return "null"

    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _to_yaml(data: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_to_yaml(value, indent + 2))
        else:
            lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")

    return "\n".join(lines)


def main() -> int:
    train_df = _load_split("train")
    val_df = _load_split("val")
    test_df = _load_split("test")

    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=50_000,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=1.0,
                    max_iter=1000,
                    solver="lbfgs",
                ),
            ),
        ]
    )

    pipeline.fit(train_df["text"], train_df["label"])

    val_pred = pipeline.predict(val_df["text"])
    test_pred = pipeline.predict(test_df["text"])

    val_metrics = _metrics(val_df["label"], val_pred)
    test_metrics = _metrics(test_df["label"], test_pred)

    print("Validation classification report:")
    print(
        classification_report(
            val_df["label"],
            val_pred,
            labels=[0, 1],
            digits=4,
            zero_division=0,
        )
    )
    print("Test classification report:")
    print(
        classification_report(
            test_df["label"],
            test_pred,
            labels=[0, 1],
            digits=4,
            zero_division=0,
        )
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_DIR / "model.joblib")

    metadata = {
        "name": "tfidf_lr",
        "version": "v1",
        "framework": "scikit-learn",
        "metrics": {
            "val": val_metrics,
            "test": test_metrics,
        },
        "hyperparameters": {
            "C": 1.0,
            "ngram_range": [1, 2],
            "max_features": 50_000,
            "max_iter": 1000,
            "solver": "lbfgs",
        },
        "trained_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "dataset": {
            "rows": {
                "train": int(len(train_df)),
                "val": int(len(val_df)),
                "test": int(len(test_df)),
            },
            "class_counts": {
                "train": _class_counts(train_df),
                "val": _class_counts(val_df),
                "test": _class_counts(test_df),
            },
        },
    }
    (MODEL_DIR / "metadata.yaml").write_text(_to_yaml(metadata) + "\n", encoding="utf-8")

    val_f1_macro = val_metrics["f1_macro"]
    print(f"F1 macro val: {val_f1_macro:.4f}")

    if val_f1_macro < VAL_F1_THRESHOLD:
        print(
            f"Validation macro F1 {val_f1_macro:.4f} is below "
            f"the required threshold {VAL_F1_THRESHOLD:.4f}.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

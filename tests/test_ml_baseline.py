from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "ml" / "data"
MODEL_DIR = REPO_ROOT / "ml" / "models" / "tfidf_lr_v1"
RANDOM_STATE = 42


def _sample_max(df: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df

    class_counts = df["label"].value_counts()
    if len(class_counts) > 1 and class_counts.min() >= 2:
        return (
            df.groupby("label", group_keys=False)
            .sample(
                n=max_rows // len(class_counts),
                random_state=RANDOM_STATE,
            )
            .sample(frac=1, random_state=RANDOM_STATE)
            .reset_index(drop=True)
        )

    return df.sample(n=max_rows, random_state=RANDOM_STATE).reset_index(drop=True)


def test_baseline_smoke():
    train_df = pd.read_csv(DATA_DIR / "train.csv")
    test_df = pd.read_csv(DATA_DIR / "test.csv")

    train_sample = _sample_max(train_df, 200)
    test_sample = _sample_max(test_df, 50)

    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=5000,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=1.0,
                    max_iter=500,
                    solver="lbfgs",
                ),
            ),
        ]
    )

    pipeline.fit(train_sample["text"], train_sample["label"])
    predictions = pipeline.predict(test_sample["text"])
    score = f1_score(
        test_sample["label"],
        predictions,
        average="macro",
        zero_division=0,
    )

    assert score > 0.7


def test_model_artifact_existe():
    assert (MODEL_DIR / "model.joblib").exists()

    metadata = (MODEL_DIR / "metadata.yaml").read_text(encoding="utf-8")
    assert "metrics:" in metadata
    assert "  val:" in metadata
    assert "    f1_macro:" in metadata

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


DATA_DIR = Path(__file__).resolve().parents[1] / "ml" / "data"
SPLIT_NAMES = ("train", "val", "test")
REQUIRED_COLUMNS = {"text", "label", "lang"}
RANDOM_STATE = 42


def _split_path(name: str) -> Path:
    return DATA_DIR / f"{name}.csv"


def _read_split(name: str) -> pd.DataFrame:
    return pd.read_csv(_split_path(name))


def _assert_split_texts_are_disjoint() -> None:
    split_texts = {
        name: set(_read_split(name)["text"].astype(str))
        for name in SPLIT_NAMES
    }

    assert split_texts["train"].isdisjoint(split_texts["val"])
    assert split_texts["train"].isdisjoint(split_texts["test"])
    assert split_texts["val"].isdisjoint(split_texts["test"])


def test_splits_exist():
    for name in SPLIT_NAMES:
        path = _split_path(name)
        assert path.exists()
        assert path.stat().st_size > 0
        assert not pd.read_csv(path).empty


def test_columns():
    for name in SPLIT_NAMES:
        df = _read_split(name)
        assert REQUIRED_COLUMNS.issubset(df.columns)


def test_labels_binary():
    for name in SPLIT_NAMES:
        df = _read_split(name)
        assert set(df["label"].unique()).issubset({0, 1})


def test_balance_minimo():
    train_df = _read_split("train")
    class_ratios = train_df["label"].value_counts(normalize=True)

    assert set(class_ratios.index) == {0, 1}
    assert (class_ratios >= 0.30).all()


def test_lang_presente():
    train_df = _read_split("train")

    assert (train_df["lang"] == "es").any()


def test_split_reproducible():
    prompts_path = DATA_DIR / "prompts.csv"
    if not prompts_path.exists():
        _assert_split_texts_are_disjoint()
        return

    prompts_df = pd.read_csv(prompts_path)
    if prompts_df.empty or not {"text", "label"}.issubset(prompts_df.columns):
        _assert_split_texts_are_disjoint()
        return

    train_df, temp_df = train_test_split(
        prompts_df,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=prompts_df["label"],
    )
    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.5,
        random_state=RANDOM_STATE,
        stratify=temp_df["label"],
    )

    expected_splits = {
        "train": train_df,
        "val": val_df,
        "test": test_df,
    }
    actual_splits = {name: _read_split(name) for name in SPLIT_NAMES}

    for name, expected_df in expected_splits.items():
        expected_labels = set(expected_df["label"].unique())
        actual_labels = set(actual_splits[name]["label"].unique())

        assert expected_labels == {0, 1}
        assert actual_labels == {0, 1}
        assert set(expected_df["text"]) == set(actual_splits[name]["text"])

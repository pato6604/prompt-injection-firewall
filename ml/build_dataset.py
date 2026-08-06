"""Build the curated prompt-injection dataset.

Run from the repository root:
    ./venv/Scripts/python.exe ml/build_dataset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from datasets import DatasetDict, load_dataset
from sklearn.model_selection import train_test_split


RANDOM_STATE = 42
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "ml" / "data"
ES_CURATED_PATH = DATA_DIR / "es_prompts_curated.csv"
OUTPUT_COLUMNS = ["text", "label", "lang", "source"]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_deepset_dataframe() -> pd.DataFrame:
    try:
        dataset = load_dataset("deepset/prompt-injections")
    except Exception as exc:  # pragma: no cover - depends on network/HF cache state
        fail(
            "no se pudo descargar/cargar deepset/prompt-injections desde Hugging Face. "
            f"Revise la red o el cache local. Detalle: {exc}"
        )

    if isinstance(dataset, DatasetDict):
        split_frames: list[pd.DataFrame] = []
        for split_name, split_dataset in dataset.items():
            columns = list(split_dataset.column_names)
            print(f"deepset split={split_name} columns={columns}")
            frame = split_dataset.to_pandas()
            frame["_hf_split"] = split_name
            split_frames.append(frame)
        if not split_frames:
            fail("deepset/prompt-injections no expuso splits con filas.")
        raw = pd.concat(split_frames, ignore_index=True)
    else:
        columns = list(dataset.column_names)
        print(f"deepset columns={columns}")
        raw = dataset.to_pandas()

    text_column = pick_text_column(raw.columns)
    labels = build_numeric_labels(raw)

    normalized = pd.DataFrame(
        {
            "text": raw[text_column].astype("string").str.strip(),
            "label": labels.astype(int),
            "lang": "en",
            "source": "deepset",
        }
    )
    normalized = normalized.dropna(subset=["text", "label"])
    normalized = normalized[normalized["text"] != ""]
    normalized = normalized[normalized["label"].isin([0, 1])]
    normalized = normalized.drop_duplicates(subset=["text"], keep="first")
    normalized = normalized.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)

    return balance_if_needed(normalized)


def pick_text_column(columns: pd.Index) -> str:
    candidates = [
        "text",
        "prompt",
        "instruction",
        "input",
        "query",
        "content",
        "sentence",
    ]
    for candidate in candidates:
        if candidate in columns:
            return candidate
    fail(
        "no se encontro una columna de texto conocida en deepset/prompt-injections. "
        f"Columnas disponibles: {list(columns)}"
    )


def build_numeric_labels(raw: pd.DataFrame) -> pd.Series:
    if "label_text" in raw.columns:
        normalized = raw["label_text"].astype("string").str.strip().str.lower()
        mapping = {
            "injection": 1,
            "prompt injection": 1,
            "jailbreak": 1,
            "malicious": 1,
            "attack": 1,
            "not injection": 0,
            "no injection": 0,
            "benign": 0,
            "safe": 0,
            "normal": 0,
        }
        labels = normalized.map(mapping)
        if labels.isna().any():
            unknown = sorted(normalized[labels.isna()].dropna().unique().tolist())
            fail(f"label_text contiene valores no soportados: {unknown}")
        return labels

    if "label" in raw.columns:
        labels = pd.to_numeric(raw["label"], errors="coerce")
        if labels.isna().any():
            fail("la columna label existe pero contiene valores no numericos.")
        labels = labels.astype(int)
        invalid = sorted(set(labels.unique().tolist()) - {0, 1})
        if invalid:
            fail(f"la columna label contiene valores fuera de 0/1: {invalid}")
        return labels

    fail(
        "no se encontro label_text ni label en deepset/prompt-injections. "
        f"Columnas disponibles: {list(raw.columns)}"
    )


def balance_if_needed(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["label"].value_counts().to_dict()
    print(f"deepset after dedupe class_counts={counts}")
    if len(counts) < 2:
        fail("deepset/prompt-injections quedo con una sola clase despues de normalizar.")

    minority_count = int(min(counts.values()))
    majority_label = max(counts, key=counts.get)
    majority_count = int(counts[majority_label])
    max_majority = minority_count * 2

    if majority_count <= max_majority:
        balanced = df
    else:
        majority = df[df["label"] == majority_label].sample(
            n=max_majority, random_state=RANDOM_STATE
        )
        minority = df[df["label"] != majority_label]
        balanced = pd.concat([minority, majority], ignore_index=True)

    balanced = balanced.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
    print(f"deepset final class_counts={balanced['label'].value_counts().to_dict()}")
    return balanced


def load_spanish_curated() -> pd.DataFrame:
    if not ES_CURATED_PATH.exists():
        fail(f"falta el subset espanol curado: {ES_CURATED_PATH}")

    df = pd.read_csv(ES_CURATED_PATH)
    required = {"text", "label", "lang"}
    missing = sorted(required - set(df.columns))
    if missing:
        fail(f"{ES_CURATED_PATH} no tiene las columnas requeridas: {missing}")

    df = df[["text", "label", "lang"]].copy()
    df["text"] = df["text"].astype("string").str.strip()
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    df = df.dropna(subset=["text", "label", "lang"])
    df["label"] = df["label"].astype(int)
    df["lang"] = df["lang"].astype("string").str.strip()

    if (df["text"] == "").any():
        fail(f"{ES_CURATED_PATH} contiene textos vacios.")
    if not set(df["label"].unique()).issubset({0, 1}):
        fail(f"{ES_CURATED_PATH} contiene labels fuera de 0/1.")
    if set(df["lang"].unique()) != {"es"}:
        fail(f'{ES_CURATED_PATH} debe tener lang="es" en todas las filas.')
    if df.duplicated(subset=["text"]).any():
        fail(f"{ES_CURATED_PATH} contiene textos duplicados exactos.")

    df["source"] = "curated_es"
    return df[OUTPUT_COLUMNS]


def write_split(name: str, df: pd.DataFrame) -> None:
    path = DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    print_counts(name, df)


def print_counts(name: str, df: pd.DataFrame) -> None:
    print(f"{name}: rows={len(df)}")
    print(f"{name}: class_counts={df['label'].value_counts().sort_index().to_dict()}")
    print(f"{name}: lang_counts={df['lang'].value_counts().sort_index().to_dict()}")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    deepset_df = load_deepset_dataframe()
    es_df = load_spanish_curated()
    curated = pd.concat([deepset_df, es_df], ignore_index=True)
    curated = curated.drop_duplicates(subset=["text"], keep="first")
    curated = curated.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
    curated = curated[OUTPUT_COLUMNS]

    prompts_path = DATA_DIR / "prompts.csv"
    curated.to_csv(prompts_path, index=False, encoding="utf-8")
    print_counts("prompts", curated)

    train_df, temp_df = train_test_split(
        curated,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=curated["label"],
    )
    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.5,
        random_state=RANDOM_STATE,
        stratify=temp_df["label"],
    )

    write_split("train", train_df.reset_index(drop=True))
    write_split("val", val_df.reset_index(drop=True))
    write_split("test", test_df.reset_index(drop=True))


if __name__ == "__main__":
    main()

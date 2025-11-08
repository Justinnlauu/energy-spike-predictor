from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "synthetic_med_device_energy.csv"
MODEL_PATH = BASE_DIR / "energy_spike_model.pkl"

TARGET_HORIZON_STEPS = 6
TARGET_COLUMN = "is_spike_in_30_min"

LEAKY_COLUMNS = [
    "is_spike",
    "power_kW",
    "power_kW_previous_5min",
    "power_kW_previous_15min",
    "power_kW_rolling_std_15min",
]

DROP_COLUMNS = ["timestamp", "order_id"]

CATEGORICAL_CANDIDATES = [
    "facility_id",
    "line_id",
    "product_type",
    "batch_status",
    "autoclave_state",
]


class ModelLoadError(RuntimeError):
    """Raised when model artifacts cannot be loaded or trained."""


def _load_dataset() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise ModelLoadError(f"Dataset not found at '{DATA_PATH}'.")
    return pd.read_csv(DATA_PATH)


def _engineer_target(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "is_spike" not in df.columns:
        raise ModelLoadError("Expected column 'is_spike' not present in dataset.")
    df[TARGET_COLUMN] = df["is_spike"].shift(-TARGET_HORIZON_STEPS)
    df = df.dropna(subset=[TARGET_COLUMN])
    return df


def _prepare_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    drop_candidates: List[str] = LEAKY_COLUMNS + DROP_COLUMNS + [TARGET_COLUMN]
    columns_to_drop = [col for col in drop_candidates if col in df.columns]
    X = df.drop(columns=columns_to_drop)
    y = df[TARGET_COLUMN].astype(int)

    categorical_cols = [col for col in CATEGORICAL_CANDIDATES if col in X.columns]

    return X, y, categorical_cols


def _build_preprocessor(
    categorical_cols: List[str], numeric_cols: List[str]
) -> ColumnTransformer:
    categorical_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="most_frequent")), ("encoder", OneHotEncoder(handle_unknown="ignore"))]
    )

    numeric_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))])

    return ColumnTransformer(
        transformers=[
            ("categorical", categorical_transformer, categorical_cols),
            ("numeric", numeric_transformer, numeric_cols),
        ]
    )


def _compute_baseline_row(
    df: pd.DataFrame, categorical_cols: List[str], numeric_cols: List[str]
) -> Dict[str, Any]:
    baseline: Dict[str, Any] = {}

    for col in numeric_cols:
        value = df[col].median()
        if pd.isna(value):
            value = float(0)
        baseline[col] = float(value)

    for col in categorical_cols:
        mode_series = df[col].mode(dropna=True)
        if mode_series.empty:
            baseline[col] = ""
        else:
            baseline[col] = str(mode_series.iloc[0])

    return baseline


def train_model(random_state: int = 42) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    df = _load_dataset()
    df = _engineer_target(df)
    X, y, categorical_cols = _prepare_feature_matrix(df)

    numeric_cols = [col for col in X.columns if col not in categorical_cols]

    preprocessor = _build_preprocessor(categorical_cols, numeric_cols)

    classifier = RandomForestClassifier(
        n_estimators=200,
        random_state=random_state,
        n_jobs=-1,
        class_weight="balanced",
    )

    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    class_report = classification_report(
        y_test, y_pred, target_names=["No Spike (0)", "Spike (1)"]
    )

    baseline_row = _compute_baseline_row(X, categorical_cols, numeric_cols)

    artifacts: Dict[str, Any] = {
        "model": pipeline,
        "feature_columns": list(X.columns),
        "categorical_columns": categorical_cols,
        "numeric_columns": numeric_cols,
        "baseline_row": baseline_row,
    }

    joblib.dump(artifacts, MODEL_PATH)

    metrics: Dict[str, Any] = {
        "accuracy": float(accuracy),
        "classification_report": class_report,
    }

    return artifacts, metrics


def load_model_artifacts(force_retrain: bool = False) -> Dict[str, Any]:
    if force_retrain or not MODEL_PATH.exists():
        artifacts, _ = train_model()
        return artifacts

    try:
        artifacts = joblib.load(MODEL_PATH)
    except Exception as exc:  # pragma: no cover - defensive
        raise ModelLoadError(f"Failed to load model artifacts: {exc}") from exc

    required_keys = {"model", "feature_columns", "categorical_columns", "numeric_columns", "baseline_row"}
    if not required_keys.issubset(artifacts):
        # If the stored model is in an unexpected format, retrain.
        artifacts, _ = train_model()
        return artifacts

    return artifacts


__all__ = [
    "load_model_artifacts",
    "train_model",
    "ModelLoadError",
    "DATA_PATH",
    "MODEL_PATH",
    "TARGET_COLUMN",
]

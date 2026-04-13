"""Save/load trained Distinguisher to disk via joblib.

We persist the full Distinguisher object (which has its sklearn
StandardScaler + LogisticRegression + pairwise specs). Joblib handles
sklearn objects efficiently.
"""

from __future__ import annotations

from pathlib import Path

import joblib

from scalping_bot.models import Distinguisher


def save_model(model: Distinguisher, path: Path) -> None:
    """Persist a fitted Distinguisher to `path`."""
    if model._fit is None:  # pragma: no cover - defensive
        raise RuntimeError("model is not fit; nothing to save")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path) -> Distinguisher:
    """Restore a saved Distinguisher from `path`."""
    obj = joblib.load(path)
    if not isinstance(obj, Distinguisher):
        raise TypeError(f"expected Distinguisher, got {type(obj).__name__}")
    return obj

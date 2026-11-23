"""Load trained ensembles and score behavioural feature vectors."""
import json
import logging
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from django.conf import settings

from .features import (
    FEATURE_NAMES,
    CLASS_CRITICAL,
    CLASS_NORMAL,
    CLASS_SUSPICIOUS,
    classify_score,
    confidence_from_score,
    rule_based_score,
    rule_based_signals,
    vector_from_dict,
)

logger = logging.getLogger("sentinelflow")

CLASS_ORDER = [CLASS_NORMAL, CLASS_SUSPICIOUS, CLASS_CRITICAL]


def artifact_dir():
    return Path(settings.ML_ARTIFACT_DIR)


@lru_cache(maxsize=1)
def load_models():
    directory = artifact_dir()
    required = ["random_forest.joblib", "isolation_forest.joblib", "scaler.joblib", "metadata.json"]
    if not all((directory / name).exists() for name in required):
        logger.info("ML artifacts not found at %s; using explainable rule-based scoring.", directory)
        return None
    try:
        models = {
            "rf": joblib.load(directory / "random_forest.joblib"),
            "iforest": joblib.load(directory / "isolation_forest.joblib"),
            "scaler": joblib.load(directory / "scaler.joblib"),
            "metadata": json.loads((directory / "metadata.json").read_text(encoding="utf-8")),
        }
        logger.info("Loaded SENTINELFLOW ML ensemble trained on %s samples.", models["metadata"].get("samples"))
        return models
    except Exception as exc:
        logger.warning("Could not load ML artifacts (%s); falling back to rule-based scoring.", exc)
        return None


def clear_model_cache():
    load_models.cache_clear()


def _iforest_risk(iforest, scaler, vector):
    scaled = scaler.transform(vector)
    decision = float(iforest.decision_function(scaled)[0])
    return float(np.clip((0.5 - decision) / 1.2, 0.0, 1.0)) * 100


def predict(features):
    """Return classification, risk score, anomaly score, confidence and reasons."""
    signals = rule_based_signals(features)
    reasons = [text for text, _ in signals]
    rule_score = rule_based_score(features)
    models = load_models()

    if models is None:
        classification = classify_score(rule_score)
        return {
            "model": "RULE_BASED",
            "classification": classification,
            "risk_score": round(rule_score, 2),
            "anomaly_score": round(rule_score / 100, 4),
            "confidence": confidence_from_score(rule_score),
            "reasons": reasons or ["No anomalous behavioural signals detected."],
            "models_agreed": None,
        }

    vector = pd.DataFrame(vector_from_dict(features), columns=FEATURE_NAMES)
    try:
        probabilities = models["rf"].predict_proba(vector)[0]
        classes = list(models["rf"].classes_)
        prob = {name: float(probabilities[classes.index(name)]) if name in classes else 0.0 for name in CLASS_ORDER}
        rf_score = prob[CLASS_NORMAL] * 10 + prob[CLASS_SUSPICIOUS] * 55 + prob[CLASS_CRITICAL] * 95
        iso_score = _iforest_risk(models["iforest"], models["scaler"], vector)
        risk = round(0.7 * rf_score + 0.3 * iso_score, 2)
        classification = classify_score(risk)
        ml_label = max(CLASS_ORDER, key=lambda name: prob[name])
        agreed = classification == ml_label
        if not agreed and classification != CLASS_NORMAL:
            reasons.append(f"Random Forest suggested {ml_label} with {prob[ml_label]:.0%} confidence.")
        if iso_score >= 70:
            reasons.append(f"Isolation Forest anomaly index is elevated ({iso_score:.0f}/100).")
        if not reasons:
            reasons = ["Behaviour aligns with the established baseline."]
        return {
            "model": "HYBRID_RF_IFOREST",
            "classification": classification,
            "risk_score": risk,
            "anomaly_score": round(iso_score / 100, 4),
            "confidence": round(max(confidence_from_score(risk), max(prob.values())), 3),
            "reasons": reasons,
            "models_agreed": agreed,
            "probabilities": {key: round(value, 4) for key, value in prob.items()},
        }
    except Exception as exc:
        logger.exception("ML inference failed: %s", exc)
        return {
            "model": "RULE_BASED_FALLBACK",
            "classification": classify_score(rule_score),
            "risk_score": round(rule_score, 2),
            "anomaly_score": round(rule_score / 100, 4),
            "confidence": confidence_from_score(rule_score),
            "reasons": reasons or ["Rule-based baseline: no anomalous signals detected."],
            "models_agreed": None,
        }

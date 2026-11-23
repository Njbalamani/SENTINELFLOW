"""Shared feature contract between the Django application and the ML pipeline."""
import math

FEATURE_NAMES = [
    "off_hours",
    "failed_logins_1h",
    "download_count_1h",
    "file_access_count_1h",
    "unique_resources_1h",
    "log_bytes_1h",
    "privilege_changes_24h",
    "session_duration_minutes",
    "user_tenure_days",
    "role_risk_weight",
    "activity_risk_weight",
    "unusual_location",
    "hour_sin",
    "hour_cos",
]

ROLE_WEIGHTS = {"ADMIN": 1.3, "ANALYST": 1.15, "VIEWER": 1.0}
ACTIVITY_WEIGHTS = {
    "LOGIN": 1.0,
    "LOGOUT": 1.0,
    "FAILED_LOGIN": 2.0,
    "FILE_ACCESS": 1.1,
    "DOWNLOAD": 1.3,
    "UPLOAD": 1.2,
    "PRIVILEGE_CHANGE": 2.5,
    "CONFIG_CHANGE": 2.2,
}

CLASS_NORMAL = "NORMAL"
CLASS_SUSPICIOUS = "SUSPICIOUS"
CLASS_CRITICAL = "CRITICAL"
CLASSIFICATIONS = (CLASS_NORMAL, CLASS_SUSPICIOUS, CLASS_CRITICAL)


def vector_from_dict(features):
    """Return feature values in the exact order expected by the trained models."""
    return [[float(features.get(name, 0.0) or 0.0) for name in FEATURE_NAMES]]


def rule_based_signals(features):
    """Explainable risk signals used as fallback and as human-readable reasons."""
    signals = []
    failed = float(features.get("failed_logins_1h", 0) or 0)
    downloads = float(features.get("download_count_1h", 0) or 0)
    accesses = float(features.get("file_access_count_1h", 0) or 0)
    unique = float(features.get("unique_resources_1h", 0) or 0)
    log_bytes = float(features.get("log_bytes_1h", 0) or 0)
    privilege = float(features.get("privilege_changes_24h", 0) or 0)

    if features.get("off_hours"):
        signals.append(("Off-hours activity outside 07:00-19:00", 18))
    if failed >= 1:
        signals.append((f"{int(failed)} failed login attempt(s) within one hour", min(30, int(failed) * 9)))
    if downloads >= 5:
        signals.append((f"Abnormal download frequency ({int(downloads)} in one hour)", min(28, int(downloads) * 5)))
    if accesses >= 25:
        signals.append((f"High file access frequency ({int(accesses)} in one hour)", 14))
    if unique >= 18:
        signals.append((f"Access to {int(unique)} distinct resources in one hour", 12))
    if log_bytes > math.log1p(100 * 1024 * 1024):
        signals.append(("Large aggregate data transfer within one hour", 16))
    if privilege > 0:
        signals.append((f"{int(privilege)} privilege/configuration change(s) in 24 hours", 25))
    if features.get("unusual_location"):
        signals.append(("Access from an unrecognized location", 15))
    if float(features.get("activity_risk_weight", 1)) >= 2:
        signals.append(("High-risk activity type (privilege/configuration change)", 10))
    return signals


def rule_based_score(features):
    weight = float(features.get("role_risk_weight", 1.0) or 1.0)
    score = sum(points for _, points in rule_based_signals(features)) * weight
    return min(100.0, max(0.0, score))


def classify_score(score):
    if score >= 65:
        return CLASS_CRITICAL
    if score >= 35:
        return CLASS_SUSPICIOUS
    return CLASS_NORMAL


def confidence_from_score(score):
    distance = abs(score - 50) / 50
    return round(0.55 + 0.42 * distance, 3)

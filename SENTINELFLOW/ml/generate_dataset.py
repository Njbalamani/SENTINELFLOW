"""Generate deterministic, realistic synthetic behaviour data for development and training.

No production or employee data is used anywhere in this project.
"""
import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .features import ACTIVITY_WEIGHTS, FEATURE_NAMES, ROLE_WEIGHTS, classify_score, rule_based_score

SEED = 42
ROLES = ["VIEWER", "ANALYST", "ADMIN"]
DEPARTMENTS = ["ENGINEERING", "FINANCE", "HUMAN_RESOURCES", "OPERATIONS", "SALES", "IT", "LEGAL"]
ACTIVITIES = ["LOGIN", "FILE_ACCESS", "DOWNLOAD", "UPLOAD", "CONFIG_CHANGE", "PRIVILEGE_CHANGE", "FAILED_LOGIN"]
RESOURCES = [
    "/shared/finance/Q3_forecast.xlsx", "/repos/core-api/src/main.py",
    "/shared/hr/payroll_2026.csv", "/vault/legal/contracts/", "/shared/engineering/design.fig",
    "/reports/quarterly_summary.pdf", "/shared/operations/inventory.xlsx",
]
IPS = ["10.20.4.18", "10.20.4.22", "10.20.8.41", "172.16.3.9", "203.0.113.44", "198.51.100.27"]

TRAIN_HEADERS = ["timestamp", "username", "role", "department", *FEATURE_NAMES, "label"]
EVENT_HEADERS = [
    "timestamp", "username", "role", "department", "activity_type", "resource",
    "ip_address", "bytes_transferred", "off_hours", "unusual_location", "source", "label",
]


def _hour_features(hour):
    angle = 2 * math.pi * hour / 24
    return math.sin(angle), math.cos(angle)


def _write_csv(path, headers, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def generate_dataset(output_dir, *, train_rows=3600, event_rows=1500, seed=SEED):
    """Create training and event-level sample CSVs; returns their paths."""
    rng = random.Random(seed)
    output_dir = Path(output_dir)
    usernames = [f"user{i:03d}" for i in range(1, 49)]
    profiles = {
        name: {"role": rng.choice(ROLES), "department": rng.choice(DEPARTMENTS), "tenure": rng.randint(30, 1400)}
        for name in usernames
    }
    end = datetime(2026, 11, 23, tzinfo=timezone.utc)
    start = end - timedelta(days=60)

    train_records, event_records = [], []

    for index in range(train_rows):
        malicious = index % 19 == 0
        username = rng.choice(usernames)
        profile = profiles[username]
        if malicious:
            hour = rng.choice([0, 1, 2, 3, 4, 5, 20, 21, 22, 23])
            features = {
                "off_hours": 1,
                "failed_logins_1h": rng.randint(3, 9),
                "download_count_1h": rng.randint(8, 40),
                "file_access_count_1h": rng.randint(30, 90),
                "unique_resources_1h": rng.randint(18, 55),
                "log_bytes_1h": math.log1p(rng.randint(100, 2000) * 1024 * 1024),
                "privilege_changes_24h": rng.choice([0, 1, 1, 2, 3]),
                "session_duration_minutes": rng.randint(5, 90),
                "user_tenure_days": profile["tenure"],
                "role_risk_weight": ROLE_WEIGHTS[profile["role"]],
                "activity_risk_weight": rng.choice([1.3, 2.0, 2.5]),
                "unusual_location": 1 if rng.random() < 0.75 else 0,
            }
            label = "CRITICAL" if rng.random() > 0.18 else "SUSPICIOUS"
            activity = rng.choice(["DOWNLOAD", "FAILED_LOGIN", "PRIVILEGE_CHANGE", "FILE_ACCESS"])
        else:
            hour = rng.choices(range(24), weights=[1, 1, 1, 1, 2, 4, 7, 10, 12, 12, 11, 10, 10, 11, 12, 11, 9, 7, 5, 4, 3, 2, 1, 1])[0]
            failed = rng.choices([0, 1, 2, 3], weights=[96, 2, 1, 1])[0]
            downloads = rng.choices(range(6), weights=[45, 25, 14, 9, 5, 2])[0]
            features = {
                "off_hours": 1 if hour < 7 or hour >= 19 else 0,
                "failed_logins_1h": failed,
                "download_count_1h": downloads,
                "file_access_count_1h": rng.randint(1, 24),
                "unique_resources_1h": rng.randint(1, 14),
                "log_bytes_1h": math.log1p(rng.randint(0, 30) * 1024 * 1024),
                "privilege_changes_24h": 0 if rng.random() < 0.97 else 1,
                "session_duration_minutes": rng.randint(5, 480),
                "user_tenure_days": profile["tenure"],
                "role_risk_weight": ROLE_WEIGHTS[profile["role"]],
                "activity_risk_weight": ACTIVITY_WEIGHTS[rng.choice(ACTIVITIES)],
                "unusual_location": 1 if rng.random() < 0.03 else 0,
            }
            score = rule_based_score(features) + rng.uniform(-8, 8)
            label = classify_score(score)
            activity = rng.choice(ACTIVITIES)
        sine, cosine = _hour_features(hour)
        features["hour_sin"], features["hour_cos"] = sine, cosine
        moment = start + timedelta(
            days=rng.randint(0, 59), hours=hour, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59)
        )
        train_records.append({
            "timestamp": moment.isoformat(),
            "username": username,
            "role": profile["role"],
            "department": profile["department"],
            **{name: round(float(features[name]), 4) for name in FEATURE_NAMES},
            "label": label,
        })

    for index in range(event_rows):
        username = rng.choice(usernames)
        profile = profiles[username]
        malicious = index % 23 == 0
        hour = rng.choice([1, 2, 3, 21, 22]) if malicious else rng.randint(7, 18)
        moment = start + timedelta(days=rng.randint(0, 59), hours=hour, minutes=rng.randint(0, 59))
        activity = "DOWNLOAD" if malicious else rng.choice(ACTIVITIES)
        event_records.append({
            "timestamp": moment.isoformat(),
            "username": username,
            "role": profile["role"],
            "department": profile["department"],
            "activity_type": activity,
            "resource": rng.choice(RESOURCES),
            "ip_address": rng.choice(IPS),
            "bytes_transferred": rng.randint(80_000_000, 900_000_000) if malicious else rng.randint(0, 25_000_000),
            "off_hours": 1 if hour < 7 or hour >= 19 else 0,
            "unusual_location": 1 if malicious and rng.random() < 0.7 else 0,
            "source": "SYNTHETIC",
            "label": "CRITICAL" if malicious else "NORMAL",
        })

    train_path = output_dir / "training_dataset.csv"
    event_path = output_dir / "sample_user_activity.csv"
    _write_csv(train_path, TRAIN_HEADERS, train_records)
    _write_csv(event_path, EVENT_HEADERS, event_records)
    return train_path, event_path


if __name__ == "__main__":
    import os

    base = Path(os.environ.get("SENTINELFLOW_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
    for path in generate_dataset(base):
        print(f"Generated {path}")

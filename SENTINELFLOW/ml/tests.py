import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from ml.features import (
    CLASS_CRITICAL,
    CLASS_NORMAL,
    FEATURE_NAMES,
    classify_score,
    rule_based_score,
    vector_from_dict,
)
from ml.generate_dataset import generate_dataset
from ml.predict import predict


class FeatureContractTests(SimpleTestCase):
    def test_vector_uses_canonical_feature_order(self):
        values = vector_from_dict({"download_count_1h": 5})
        self.assertEqual(len(values[0]), len(FEATURE_NAMES))
        self.assertEqual(values[0][FEATURE_NAMES.index("download_count_1h")], 5.0)

    def test_rule_scores_and_classes(self):
        normal = {name: 0 for name in FEATURE_NAMES}
        attack = dict(normal, off_hours=1, failed_logins_1h=6, download_count_1h=25,
                      privilege_changes_24h=2, unusual_location=1)
        self.assertEqual(classify_score(rule_based_score(normal)), CLASS_NORMAL)
        self.assertEqual(classify_score(rule_based_score(attack)), CLASS_CRITICAL)


class DatasetTests(SimpleTestCase):
    def test_generation_writes_both_csv_files(self):
        with tempfile.TemporaryDirectory() as directory:
            train_path, event_path = generate_dataset(Path(directory), train_rows=120, event_rows=40)
            self.assertTrue(train_path.exists())
            self.assertTrue(event_path.exists())
            header = train_path.read_text(encoding="utf-8").splitlines()[0]
            for name in FEATURE_NAMES:
                self.assertIn(name, header)
            self.assertEqual(len(event_path.read_text(encoding="utf-8").splitlines()), 41)


class PredictionTests(SimpleTestCase):
    def test_rule_based_fallback_when_artifacts_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            with override_settings(ML_ARTIFACT_DIR=directory):
                from ml.predict import clear_model_cache

                clear_model_cache()
                result = predict({"failed_logins_1h": 4, "off_hours": 1, "unusual_location": 1})
                self.assertIn(result["model"], {"RULE_BASED", "HYBRID_RF_IFOREST"})
                self.assertIn("risk_score", result)
                self.assertTrue(0 <= result["risk_score"] <= 100)
                clear_model_cache()

    @unittest.skipUnless(
        all(
            (Path(settings.ML_ARTIFACT_DIR) / name).exists()
            for name in ("metadata.json", "random_forest.joblib", "isolation_forest.joblib")
        ),
        "ML artifacts not trained",
    )
    def test_hybrid_ensemble_prediction(self):
        from ml.predict import clear_model_cache

        clear_model_cache()
        result = predict({name: 0 for name in FEATURE_NAMES})
        self.assertEqual(result["model"], "HYBRID_RF_IFOREST")
        self.assertIn(result["classification"], {CLASS_NORMAL, "SUSPICIOUS", CLASS_CRITICAL})
        self.assertIsInstance(result["reasons"], list)
        clear_model_cache()

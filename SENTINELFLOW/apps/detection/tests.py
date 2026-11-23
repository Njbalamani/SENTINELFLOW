from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ROLE_ANALYST, User
from apps.alerts.models import SecurityAlert
from apps.detection.models import Classification, DetectionResult, RiskLevel, UserRiskProfile
from apps.detection.services import analyze_activity, risk_level_for, update_risk_profile
from apps.monitoring.models import ActivityType, UserActivity
from ml.features import classify_score, rule_based_score


class DetectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="subject", password="Pass!2026", role=ROLE_ANALYST)

    def _activity(self, activity_type=ActivityType.DOWNLOAD, **kwargs):
        return UserActivity.objects.create(
            user=self.user, activity_type=activity_type, timestamp=timezone.now(), **kwargs
        )

    def test_rule_score_classifies_attack_pattern_as_critical(self):
        features = {
            "off_hours": 1, "failed_logins_1h": 6, "download_count_1h": 20,
            "file_access_count_1h": 50, "unique_resources_1h": 30,
            "log_bytes_1h": 20, "privilege_changes_24h": 2, "unusual_location": 1,
            "role_risk_weight": 1.0, "activity_risk_weight": 2.5,
        }
        self.assertEqual(classify_score(rule_based_score(features)), Classification.CRITICAL)

    def test_analyze_activity_creates_detection_alert_and_profile(self):
        activity = self._activity(is_unusual_location=True)
        result = analyze_activity(activity)
        self.assertEqual(result.activity, activity)
        self.assertTrue(DetectionResult.objects.filter(pk=result.pk).exists())
        self.assertTrue(UserRiskProfile.objects.filter(user=self.user).exists())
        if result.classification in {Classification.SUSPICIOUS, Classification.CRITICAL}:
            self.assertTrue(SecurityAlert.objects.filter(detection=result).exists())

    def test_risk_profile_reflects_detection_history(self):
        for index in range(3):
            activity = self._activity(activity_type=ActivityType.FAILED_LOGIN)
            DetectionResult.objects.create(
                activity=activity, user=self.user, classification=Classification.CRITICAL,
                risk_score=90, created_at=timezone.now(),
            )
        profile = update_risk_profile(self.user)
        self.assertGreater(profile.risk_score, 50)
        self.assertEqual(profile.risk_level, RiskLevel.CRITICAL)
        self.assertEqual(profile.critical_count, 3)

    def test_risk_thresholds(self):
        self.assertEqual(risk_level_for(10), RiskLevel.LOW)
        self.assertEqual(risk_level_for(55), RiskLevel.MEDIUM)
        self.assertEqual(risk_level_for(80), RiskLevel.HIGH)
        self.assertEqual(risk_level_for(95), RiskLevel.CRITICAL)

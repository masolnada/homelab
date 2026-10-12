import unittest
from datetime import datetime, timedelta, timezone

from digest import ZONE, summarize


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 13, 6, tzinfo=timezone.utc)
        self.previous = self.now - timedelta(days=1)
        self.devices = {"sensor": "Temperature sensors"}

    def test_healthy_stays_silent(self):
        points = [self.previous + timedelta(hours=i) for i in range(25)]
        self.assertIsNone(summarize(self.devices, {"sensor": points}, self.now, self.previous))

    def test_missing_and_exactly_three_hours_are_offline(self):
        for reports in [{}, {"sensor": [self.now - timedelta(hours=3)]}]:
            self.assertIn("No reports for 3 hours", summarize(self.devices, reports, self.now, self.previous))

    def test_first_report_after_silence_is_recovery(self):
        message = summarize(self.devices, {"sensor": [self.now - timedelta(minutes=5)]}, self.now, self.previous)
        self.assertIn("Reporting again", message)
        self.assertNotIn("No reports for 3 hours", message)

    def test_gap_during_day_is_reported_once_as_recovered(self):
        points = [self.previous - timedelta(minutes=5), self.previous + timedelta(hours=1)]
        points += [self.previous + timedelta(hours=i) for i in range(6, 25)]
        message = summarize(self.devices, {"sensor": points}, self.now, self.previous)
        self.assertEqual(message.count("Temperature sensors / sensor"), 1)
        self.assertIn("Reporting again", message)

    def test_recovered_then_failed_is_only_listed_offline(self):
        points = [self.previous + timedelta(hours=5)]
        message = summarize(self.devices, {"sensor": points}, self.now, self.previous)
        self.assertNotIn("Reporting again", message)
        self.assertIn("No reports for 3 hours", message)

    def test_recovery_before_previous_digest_is_not_repeated(self):
        points = [self.previous - timedelta(minutes=5)] + [self.previous + timedelta(hours=i) for i in range(25)]
        self.assertIsNone(summarize(self.devices, {"sensor": points}, self.now, self.previous))

    def test_timezone_follows_daylight_saving(self):
        summer = datetime(2026, 10, 24, 8, tzinfo=ZONE)
        winter = datetime(2026, 10, 25, 8, tzinfo=ZONE)
        self.assertEqual(summer.utcoffset(), timedelta(hours=2))
        self.assertEqual(winter.utcoffset(), timedelta(hours=1))


if __name__ == "__main__":
    unittest.main()

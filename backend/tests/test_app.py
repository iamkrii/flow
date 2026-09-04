"""Small end-to-end regression tests for the Flask API.

These tests use a temporary SQLite database, so they never touch the
developer's local flow.db file. Run with:

    python -m unittest discover -s backend/tests
"""

import os
import tempfile
import unittest
import uuid


TEST_DIR = tempfile.TemporaryDirectory(prefix="flow-tests-")
os.environ["SQLITE_PATH"] = os.path.join(TEST_DIR.name, "test.db")
os.environ["JWT_SECRET"] = "test-secret"

from backend.main import app  # noqa: E402  (environment must be set first)
from backend import database  # noqa: E402


class FlowAPITestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        email = f"tester-{uuid.uuid4().hex}@example.com"
        response = self.client.post(
            "/api/auth/signup",
            json={"email": email, "password": "password123", "name": "Test User"},
        )
        self.assertEqual(response.status_code, 200)
        self.token = response.get_json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def request(self, method, path, **kwargs):
        kwargs.setdefault("headers", self.headers)
        return getattr(self.client, method)(path, **kwargs)

    def test_sqlite_uses_the_shared_schema_file(self):
        self.assertTrue(database.SCHEMA_PATH.endswith("sql/oracle_schema.sql"))
        with database.get_conn() as conn:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(
            tables,
            {"users", "settings", "periods", "symptoms", "moods", "daily_logs"},
        )

    def create_sample_logs(self):
        period = self.request(
            "post", "/api/periods",
            json={"start_date": "2026-08-01", "end_date": "2026-08-05", "flow_level": 2, "notes": "sample"},
        )
        symptom = self.request(
            "post", "/api/symptoms",
            json={"log_date": "2026-08-02", "symptom": "Cramps", "severity": 3, "notes": "sample"},
        )
        mood = self.request(
            "post", "/api/moods",
            json={"log_date": "2026-08-02", "mood": "🙂 Calm", "energy": 4},
        )
        daily = self.request(
            "post", "/api/daily",
            json={
                "log_date": "2026-08-02", "weight_kg": 60.5, "temperature_c": 36.7,
                "discharge": "Creamy", "intercourse": False, "medication": "none",
                "cramps": 2, "notes": "sample",
            },
        )
        for response in (period, symptom, mood, daily):
            self.assertEqual(response.status_code, 200)
        return tuple(response.get_json()["id"] for response in (period, symptom, mood, daily))

    def test_log_records_support_create_read_update_delete(self):
        period_id, symptom_id, mood_id, daily_id = self.create_sample_logs()

        self.assertEqual(self.request("get", "/api/periods").status_code, 200)
        self.assertEqual(self.request("get", "/api/symptoms").status_code, 200)
        self.assertEqual(self.request("get", "/api/moods").status_code, 200)
        self.assertEqual(self.request("get", "/api/daily").status_code, 200)

        updates = [
            ("put", f"/api/periods/{period_id}", {"start_date": "2026-08-01", "end_date": "2026-08-06", "flow_level": 3, "notes": "updated"}),
            ("put", f"/api/symptoms/{symptom_id}", {"log_date": "2026-08-03", "symptom": "Headache", "severity": 2, "notes": "updated"}),
            ("put", f"/api/moods/{mood_id}", {"log_date": "2026-08-03", "mood": "😊 Happy", "energy": 5}),
            ("put", f"/api/daily/{daily_id}", {"log_date": "2026-08-03", "weight_kg": 61, "temperature_c": 36.8, "discharge": "Watery", "intercourse": True, "medication": "none", "cramps": 1, "notes": "updated"}),
        ]
        for method, path, body in updates:
            self.assertEqual(self.request(method, path, json=body).status_code, 200)

        deletes = [
            f"/api/periods/{period_id}", f"/api/symptoms/{symptom_id}",
            f"/api/moods/{mood_id}", f"/api/daily/{daily_id}",
        ]
        for path in deletes:
            self.assertEqual(self.request("delete", path).status_code, 200)

    def test_profile_settings_and_report_queries(self):
        self.assertEqual(
            self.request("put", "/api/me", json={"name": "Updated User"}).status_code,
            200,
        )
        settings = self.request(
            "put", "/api/settings",
            json={"avg_cycle_length": 30, "avg_period_length": 6, "luteal_phase_length": 14, "notifications_enabled": True},
        )
        self.assertEqual(settings.status_code, 200)
        self.assertEqual(self.request("get", "/api/settings").get_json()["avg_cycle_length"], 30)

        self.create_sample_logs()
        reports = self.request("get", "/api/reports")
        self.assertEqual(reports.status_code, 200)
        payload = reports.get_json()
        self.assertEqual(set(payload["related_queries"]), {"period_settings", "period_symptoms", "daily_moods"})
        self.assertEqual(set(payload["complex_queries"]), {"symptoms_by_period", "mood_measurements"})
        self.assertGreaterEqual(len(payload["related_queries"]["period_settings"]), 1)

    def test_account_can_be_deleted_with_dependents(self):
        self.create_sample_logs()
        response = self.request("delete", "/api/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.request("get", "/api/me").status_code, 404)


if __name__ == "__main__":
    unittest.main()

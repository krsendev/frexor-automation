import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("FREXOR_WEBHOOK_TOKEN", "test-webhook-token")
os.environ.setdefault("FREXOR_WORKER_TOKEN", "test-worker-token")

import httpx

from frexor_api import database
from frexor_api.main import app


def assessment_payload(external_id: str) -> dict:
    return {
        "external_id": external_id,
        "name": "Dummy Participant",
        "position": "Operator",
        "test_date": "2026-10-08",
        "answers": {
            "disc": [
                {"question_no": number, "mirip": "A", "tidak_mirip": "B"}
                for number in range(1, 25)
            ],
            "vak": [
                {"question_no": number, "answer": "A"}
                for number in range(1, 31)
            ],
            "iq": [
                {"question_no": number, "answer": "A"}
                for number in range(1, 61)
            ],
        },
    }


class ApiQueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        database.DATABASE_PATH = Path(self.temporary.name) / "queue.db"
        database.initializeDatabase()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        )
        self.webhook_headers = {"Authorization": "Bearer test-webhook-token"}
        self.worker_headers = {
            "Authorization": "Bearer test-worker-token",
            "X-Worker-ID": "worker-test-01",
        }

    async def asyncTearDown(self):
        await self.client.aclose()
        self.temporary.cleanup()

    async def test_complete_job_flow(self):
        created = await self.client.post(
            "/api/v1/webhooks/assessments",
            headers=self.webhook_headers,
            json=assessment_payload("FORM-INTEGRATION-001"),
        )
        self.assertEqual(created.status_code, 201)

        claimed = await self.client.post(
            "/api/v1/worker/jobs/claim",
            headers={"Authorization": "Bearer test-worker-token"},
            json={"worker_id": "worker-test-01"},
        )
        self.assertEqual(claimed.status_code, 200)
        claim_data = claimed.json()
        job_id = claim_data["job_id"]
        self.assertEqual(claim_data["modules"]["DISC"]["status"], "PENDING")

        answers = await self.client.get(
            f"/api/v1/worker/jobs/{job_id}/answers/DISC",
            headers=self.worker_headers,
        )
        self.assertEqual(answers.status_code, 200)
        self.assertEqual(answers.json()["count"], 24)

        heartbeat = await self.client.post(
            f"/api/v1/worker/jobs/{job_id}/heartbeat",
            headers=self.worker_headers,
        )
        self.assertEqual(heartbeat.status_code, 200)

        for module in ("DISC", "VAK", "IQ"):
            processing = await self.client.patch(
                f"/api/v1/worker/jobs/{job_id}/modules/{module}",
                headers=self.worker_headers,
                json={"status": "PROCESSING"},
            )
            self.assertEqual(processing.status_code, 200)
            done = await self.client.patch(
                f"/api/v1/worker/jobs/{job_id}/modules/{module}",
                headers=self.worker_headers,
                json={"status": "DONE", "pdf_path": f"output/{module}.pdf"},
            )
            self.assertEqual(done.status_code, 200)

        status = await self.client.get(
            f"/api/v1/jobs/{job_id}",
            headers=self.webhook_headers,
        )
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "DONE")

    async def test_heartbeat_rejects_webhook_token(self):
        created = (await self.client.post(
            "/api/v1/webhooks/assessments",
            headers=self.webhook_headers,
            json=assessment_payload("FORM-INTEGRATION-002"),
        )).json()
        await self.client.post(
            "/api/v1/worker/jobs/claim",
            headers={"Authorization": "Bearer test-worker-token"},
            json={"worker_id": "worker-test-01"},
        )
        response = await self.client.post(
            f"/api/v1/worker/jobs/{created['job_id']}/heartbeat",
            headers={
                "Authorization": "Bearer test-webhook-token",
                "X-Worker-ID": "worker-test-01",
            },
        )
        self.assertEqual(response.status_code, 401)

    async def test_expired_claim_is_requeued_and_claimed_again(self):
        created = (await self.client.post(
            "/api/v1/webhooks/assessments",
            headers=self.webhook_headers,
            json=assessment_payload("FORM-RECOVERY-CLAIMED"),
        )).json()
        await self.client.post(
            "/api/v1/worker/jobs/claim",
            headers={"Authorization": "Bearer test-worker-token"},
            json={"worker_id": "worker-test-01"},
        )
        with database.transaction() as connection:
            connection.execute(
                "UPDATE jobs SET lease_until = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", created["job_id"]),
            )

        claimed_again = await self.client.post(
            "/api/v1/worker/jobs/claim",
            headers={"Authorization": "Bearer test-worker-token"},
            json={"worker_id": "worker-test-02"},
        )
        self.assertEqual(claimed_again.status_code, 200)
        self.assertEqual(claimed_again.json()["worker_id"], "worker-test-02")
        self.assertEqual(claimed_again.json()["attempt_count"], 2)

    async def test_expired_processing_requires_review(self):
        created = (await self.client.post(
            "/api/v1/webhooks/assessments",
            headers=self.webhook_headers,
            json=assessment_payload("FORM-RECOVERY-PROCESSING"),
        )).json()
        job_id = created["job_id"]
        await self.client.post(
            "/api/v1/worker/jobs/claim",
            headers={"Authorization": "Bearer test-worker-token"},
            json={"worker_id": "worker-test-01"},
        )
        await self.client.patch(
            f"/api/v1/worker/jobs/{job_id}/modules/DISC",
            headers=self.worker_headers,
            json={"status": "PROCESSING"},
        )
        with database.transaction() as connection:
            connection.execute(
                "UPDATE jobs SET lease_until = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", job_id),
            )

        next_claim = await self.client.post(
            "/api/v1/worker/jobs/claim",
            headers={"Authorization": "Bearer test-worker-token"},
            json={"worker_id": "worker-test-02"},
        )
        self.assertEqual(next_claim.status_code, 204)
        current = await self.client.get(
            f"/api/v1/jobs/{job_id}",
            headers=self.webhook_headers,
        )
        self.assertEqual(current.json()["status"], "REVIEW_REQUIRED")
        self.assertEqual(current.json()["error_code"], "LEASE_EXPIRED")


if __name__ == "__main__":
    unittest.main()

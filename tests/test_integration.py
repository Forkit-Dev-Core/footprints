import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from serve import create_footprints_app


class FootprintsIntegrationTest(unittest.TestCase):
    def test_local_ui_and_core_share_an_origin_and_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            registry_root = Path(directory)
            with TestClient(
                create_footprints_app(registry_root), base_url="http://127.0.0.1"
            ) as client:
                page = client.get("/footprints/")
                self.assertEqual(page.status_code, 200)
                self.assertIn('id="passport-form"', page.text)
                for script in ("discovery.js", "passport.js"):
                    self.assertEqual(client.get(f"/footprints/{script}").status_code, 200)
                self.assertEqual(client.get("/footprints/serve.py").status_code, 404)
                self.assertEqual(client.get("http://external.example/footprints/").status_code, 400)

                artifact_hash = hashlib.sha256(b"synthetic model artifact").hexdigest()
                payload = {
                    "name": "integration-model",
                    "version": "1.0.0",
                    "creator": {"name": "Test fixture"},
                    "task_type": "embedding",
                    "architecture": "encoder-only",
                    "artifact_hash": artifact_hash,
                    "artifact_files": ["model.safetensors"],
                }
                created = client.post("/models", json=payload)
                self.assertEqual(created.status_code, 201, created.text)
                passport_id = created.json()["id"]
                stored_path = registry_root / "models" / f"{passport_id}.json"
                passport = json.loads(stored_path.read_text(encoding="utf-8"))
                self.assertEqual(passport["artifact_hash"], artifact_hash)

                verify_path = f"/verify/{passport_id}"
                verified = client.post(verify_path)
                self.assertEqual(verified.status_code, 200, verified.text)
                self.assertTrue(verified.json()["valid"])
                self.assertEqual(verified.json()["stored_id"], passport_id)

                passport["name"] = "changed after registration"
                stored_path.write_text(json.dumps(passport), encoding="utf-8")
                rejected = client.post(verify_path)
                self.assertEqual(rejected.status_code, 409, rejected.text)
                self.assertEqual(rejected.json()["error"]["code"], "id_mismatch")

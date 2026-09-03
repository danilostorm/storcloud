import io
import os

os.environ.setdefault("STORCLOUD_SETUP_TOKEN", "ci-setup-token")
os.environ.setdefault("STORCLOUD_COOKIE_SECURE", "false")

from fastapi.testclient import TestClient

from main import app


def test_full_control_plane_smoke():
    with TestClient(app) as client:
        setup = client.get("/setup/status")
        assert setup.status_code == 200

        register = client.post(
            "/auth/register",
            json={
                "username": "admin",
                "email": "admin@example.test",
                "password": "very-strong-ci-password",
                "setup_token": "ci-setup-token",
            },
        )
        assert register.status_code == 200, register.text
        assert register.json()["user"]["role"] == "admin"

        me = client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["username"] == "admin"

        pair_ticket = client.post("/devices/pair-ticket", json={})
        assert pair_ticket.status_code == 200
        pair = client.post(
            "/agent/pair",
            json={
                "ticket": pair_ticket.json()["ticket"],
                "name": "CI Player PC",
                "os": "linux",
                "arch": "x86_64",
                "logical_cpus": 8,
            },
        )
        assert pair.status_code == 200, pair.text
        device_id = pair.json()["device_id"]
        device_token = pair.json()["device_token"]

        heartbeat = client.post("/agent/heartbeat", headers={"Authorization": f"Bearer {device_token}"})
        assert heartbeat.status_code == 200

        launch_ticket = client.post(f"/devices/{device_id}/launch-ticket", json={"game_id": "test-game"})
        assert launch_ticket.status_code == 200
        consume = client.post(
            "/agent/launch/consume",
            headers={"Authorization": f"Bearer {device_token}"},
            json={"ticket": launch_ticket.json()["ticket"], "game_id": "test-game"},
        )
        assert consume.status_code == 200

        save = client.post(
            "/saves/test-game/auto",
            files={"file": ("test.state", io.BytesIO(b"storcloud-save-state"), "application/octet-stream")},
        )
        assert save.status_code == 200, save.text
        assert save.json()["size_bytes"] == len(b"storcloud-save-state")

        saved = client.get("/saves/test-game/auto")
        assert saved.status_code == 200
        assert saved.content == b"storcloud-save-state"

        devices = client.get("/devices")
        assert devices.status_code == 200
        assert any(item["id"] == device_id for item in devices.json()["items"])

        logout = client.post("/auth/logout", json={})
        assert logout.status_code == 200
        assert client.get("/auth/me").status_code == 401

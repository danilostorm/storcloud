import io
import os

os.environ.setdefault("STORCLOUD_SETUP_TOKEN", "ci-setup-token")
os.environ.setdefault("STORCLOUD_COOKIE_SECURE", "false")

from fastapi.testclient import TestClient

from app import app


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

        rom = client.post(
            "/library/roms",
            data={"platform_id": "nes", "title": "CI Homebrew"},
            files={"file": ("ci-homebrew.nes", io.BytesIO(b"NES\x1a" + b"\0" * 64), "application/octet-stream")},
        )
        assert rom.status_code == 200, rom.text
        rom_id = rom.json()["item"]["id"]
        assert client.get("/library/roms").json()["count"] == 1
        rom_file = client.get(f"/library/roms/{rom_id}/file")
        assert rom_file.status_code == 200
        assert rom_file.content.startswith(b"NES\x1a")

        retro_session = client.post(
            "/activity/start",
            json={
                "mode": "retro-wasm",
                "game_key": f"rom-{rom_id}",
                "title": "CI Homebrew",
                "platform_id": "nes",
            },
        )
        assert retro_session.status_code == 200, retro_session.text
        retro_session_id = retro_session.json()["session"]["id"]
        assert client.post(f"/activity/{retro_session_id}/heartbeat").status_code == 200
        assert client.post(f"/activity/{retro_session_id}/end").status_code == 200
        summary = client.get("/activity/summary")
        assert summary.status_code == 200
        assert summary.json()["sessions"] >= 1
        continuing = client.get("/activity/continue")
        assert continuing.status_code == 200
        assert continuing.json()["items"][0]["launch_url"] == f"/retro/?rom={rom_id}"

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
        auth = {"Authorization": f"Bearer {device_token}"}

        heartbeat = client.post("/agent/heartbeat", headers=auth)
        assert heartbeat.status_code == 200

        launch_ticket = client.post(f"/devices/{device_id}/launch-ticket", json={"game_id": "test-game"})
        assert launch_ticket.status_code == 200
        consume = client.post(
            "/agent/launch/consume",
            headers=auth,
            json={"ticket": launch_ticket.json()["ticket"], "game_id": "test-game"},
        )
        assert consume.status_code == 200

        native_session = client.post(
            "/agent/activity/start",
            headers=auth,
            json={"game_id": "test-game", "title": "CI Native Game"},
        )
        assert native_session.status_code == 200, native_session.text
        native_session_id = native_session.json()["session_id"]
        assert client.post(f"/agent/activity/{native_session_id}/heartbeat", headers=auth).status_code == 200
        assert client.post(f"/agent/activity/{native_session_id}/end", headers=auth).status_code == 200

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

        achievements = client.get("/achievements")
        assert achievements.status_code == 200, achievements.text
        unlocked = {item["id"] for item in achievements.json()["items"] if item["unlocked"]}
        assert "first-launch" in unlocked
        assert "paired-device" in unlocked
        assert "local-pc" in unlocked

        admin_overview = client.get("/admin/overview")
        assert admin_overview.status_code == 200, admin_overview.text
        assert admin_overview.json()["users"] == 1
        assert admin_overview.json()["roms"] == 1
        assert admin_overview.json()["sessions"] >= 2
        assert client.get("/admin/users/detail").status_code == 200
        assert client.get("/admin/activity").status_code == 200

        logout = client.post("/auth/logout", json={})
        assert logout.status_code == 200
        assert client.get("/auth/me").status_code == 401

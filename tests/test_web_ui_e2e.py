import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]


def _http_get(url: str, timeout: float = 5.0) -> Tuple[int, Dict[str, str], bytes]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - test-only
        status = resp.status
        headers = {k.lower(): v for k, v in resp.headers.items()}
        body = resp.read()
        return status, headers, body


def _wait_http_ok(url: str, timeout_s: float = 60.0, interval_s: float = 1.0) -> None:
    deadline = time.time() + timeout_s
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            status, _, _ = _http_get(url, timeout=5.0)
            if status == 200:
                return
        except Exception as exc:  # noqa: BLE001 - test-only
            last_err = exc
        time.sleep(interval_s)
    raise AssertionError(f"Service did not become ready at {url}. Last error: {last_err!r}")


def _docker_compose_cmd() -> Optional[list[str]]:
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def _start_local_web_ui() -> subprocess.Popen:
    env = os.environ.copy()
    env.update(
        {
            "SUPERVISOR_INGRESS_ENTRY": "/ingress",
            "SUPERVISOR_INGRESS_HOST": "127.0.0.1",
            "SUPERVISOR_INGRESS_PORT": "8099",
            "HEALTH_HOST": "127.0.0.1",
            "HEALTH_PORT": "8099",
            "LLM_ENABLED": "false",
            "OPENAI_API_KEY": "",
            "MQTT_ENABLED": "false",
            "TELEGRAM_ENABLED": "false",
            "RTSP_URL": "",
            "PYTHONUNBUFFERED": "1",
        }
    )
    return subprocess.Popen(
        [sys.executable, "-m", "src.main"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def _stop_local_web_ui(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def _assert_web_ui_loaded(base_url: str, path: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
        page.wait_for_selector("text=Smart Motion Detector", timeout=10_000)
        assert page.title() == "Smart Motion Detector"
        browser.close()


@pytest.fixture(scope="session")
def webui_base_url() -> str:
    """
    Bring up service using docker-compose and wait for readiness.

    Uses docker-compose.yml + docker-compose.test.yml (ingress simulation).
    Falls back to starting the app locally if Docker isn't available.
    """
    compose_files = ["-f", "docker-compose.yml", "-f", "docker-compose.test.yml"]
    compose_cmd = _docker_compose_cmd()

    base_url = "http://localhost:8099"
    if compose_cmd:
        subprocess.run(  # nosec - test-only
            [*compose_cmd, *compose_files, "up", "-d", "--build"],
            check=True,
        )
        try:
            _wait_http_ok(f"{base_url}/ready", timeout_s=120.0, interval_s=2.0)
            yield base_url
        finally:
            subprocess.run(  # nosec - test-only
                [*compose_cmd, *compose_files, "down", "--remove-orphans", "--volumes"],
                check=False,
            )
        return

    process = _start_local_web_ui()
    try:
        _wait_http_ok(f"{base_url}/ready", timeout_s=60.0, interval_s=1.0)
        yield base_url
    finally:
        _stop_local_web_ui(process)


@pytest.mark.e2e
def test_service_is_up_and_ready(webui_base_url: str) -> None:
    status, _, _ = _http_get(f"{webui_base_url}/ready")
    assert status == 200


@pytest.mark.e2e
def test_health_endpoint_200(webui_base_url: str) -> None:
    # Project’s documented health endpoint
    status, _, body = _http_get(f"{webui_base_url}/api/health")
    assert status == 200
    assert b"ok" in body.lower()


@pytest.mark.e2e
def test_webui_index_loads(webui_base_url: str) -> None:
    _assert_web_ui_loaded(webui_base_url, "/")


@pytest.mark.e2e
def test_ingress_path_index_loads(webui_base_url: str) -> None:
    # docker-compose.test.yml sets SUPERVISOR_INGRESS_ENTRY=/ingress
    _assert_web_ui_loaded(webui_base_url, "/ingress/")


@pytest.mark.e2e
def test_mjpeg_endpoint_accessible(webui_base_url: str) -> None:
    # We only verify connection and response headers, not full stream decode.
    req = urllib.request.Request(f"{webui_base_url}/stream.mjpeg", method="GET")
    with urllib.request.urlopen(req, timeout=10.0) as resp:  # nosec - test-only
        assert resp.status == 200
        ctype = resp.headers.get("Content-Type", "")
        assert "multipart" in ctype.lower()
        # Read a small chunk to ensure stream starts sending
        chunk = resp.read(256)
        assert chunk


@pytest.mark.e2e
def test_playwright_screenshot_webui(webui_base_url: str) -> None:
    os.makedirs("test-artifacts", exist_ok=True)
    screenshot_path = os.path.join("test-artifacts", "webui.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{webui_base_url}/ingress/", wait_until="domcontentloaded")
        page.wait_for_selector("text=Smart Motion Detector", timeout=10_000)
        page.screenshot(path=screenshot_path, full_page=True)
        browser.close()

    assert os.path.exists(screenshot_path)


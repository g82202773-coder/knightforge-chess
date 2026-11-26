"""Browser end-to-end tests for KnightForge v3.0 Pro desktop & mobile viewports."""
from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn

from knightforge_engine.server import app

playwright = pytest.importorskip("playwright.sync_api")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live_server_url() -> str:
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    yield url
    server.should_exit = True
    thread.join(timeout=3)


def test_v3_svg_board_mobile_overflow_and_openings(live_server_url: str) -> None:
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_server_url, wait_until="networkidle")
        assert "KnightForge" in page.title()
        page.wait_for_selector("#play-board .square")
        assert page.locator("#play-board .square").count() == 64
        assert page.locator("#play-board svg.kf-svg-piece").count() == 32

        overflow = page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert not overflow

        page.locator('.tab-btn[data-tab="openings"]').click()
        page.wait_for_selector("#opening-board .square")
        assert page.locator("#opening-board .square").count() == 64

        page.locator('.tab-btn[data-tab="tactics"]').click()
        page.wait_for_selector("#puzzle-board .square")
        assert page.locator("#puzzle-board .square").count() == 64
        browser.close()



def test_academy_coach_overlay_arrows_and_voice_controls(live_server_url: str) -> None:
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_server_url, wait_until="networkidle")
        page.locator('.tab-btn[data-tab="academy"]').click()
        page.wait_for_selector("#board .square")
        page.wait_for_selector("#coach-text")
        page.wait_for_selector("#coach-voice-select")
        page.wait_for_selector("#stop-speak-btn")
        page.wait_for_selector("#board .board-arrow")
        assert page.locator("#board .square.coach-arrow-source").count() == 1
        assert page.locator("#board .square.coach-arrow-target").count() == 1
        assert page.locator("#coach-text").inner_text().strip()
        assert page.locator("#coach-explanation").count() == 1

        # Stub the device TTS interface so the Listen action is deterministic in CI.
        page.evaluate(
            """() => {
                Object.defineProperty(window, "speechSynthesis", {
                    configurable: true,
                    value: {
                        cancel() {},
                        getVoices() { return []; },
                        addEventListener() {},
                        speak(utterance) {
                            window.__knightForgeSpoken = utterance.text;
                            if (utterance.onstart) utterance.onstart();
                            if (utterance.onend) utterance.onend();
                        }
                    }
                });
                window.SpeechSynthesisUtterance = function(text) {
                    this.text = text;
                };
            }"""
        )
        page.locator("#speak-btn").click()
        page.wait_for_function("Boolean(window.__knightForgeSpoken)")
        assert page.evaluate("window.__knightForgeSpoken").strip()
        browser.close()

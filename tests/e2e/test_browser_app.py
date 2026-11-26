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

def test_academy_mistake_coach_retry_continue_and_voice(live_server_url: str) -> None:
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_server_url, wait_until="networkidle")
        page.locator('.mobile-tab-btn[data-tab="academy"]').click()
        page.wait_for_selector("#board .square")
        page.locator("#academy-category").select_option("opening")
        page.wait_for_function(
            "() => document.querySelector('#board [data-sq=d2] .piece-wrap') !== null"
        )

        # A legal but off-lesson move should open the coach without changing the board.
        page.locator('#board [data-sq="d2"]').click()
        assert "selected" in (page.locator('#board [data-sq="d2"]').get_attribute("class") or "")
        assert "legal" in (page.locator('#board [data-sq="d4"]').get_attribute("class") or "")
        with page.expect_response(
            lambda response: "/api/sessions/" in response.url
            and response.url.endswith("/moves")
            and response.request.method == "POST",
            timeout=8000,
        ) as move_response:
            page.locator('#board [data-sq="d4"]').click()
        assert move_response.value.status == 200
        page.wait_for_selector("#mistake-coach:not(.hidden)", timeout=8000)
        assert "legal" in page.locator("#mistake-coach-text").inner_text().lower()
        assert page.locator("#mistake-hear-btn").is_visible()
        assert page.locator("#voice-toggle").is_checked()

        # Retry keeps the same position and lets the learner choose again.
        page.locator("#mistake-retry-btn").click()
        page.locator("#mistake-coach").wait_for(state="hidden")
        assert page.locator("#move-count").inner_text() == "0 half-moves"

        # Continue applies the curated lesson move, advances the board and closes the card.
        page.locator('#board [data-sq="d2"]').click()
        page.locator('#board [data-sq="d4"]').click()
        page.wait_for_selector("#mistake-coach:not(.hidden)")
        page.locator("#mistake-continue-btn").click()
        page.locator("#mistake-coach").wait_for(state="hidden")
        assert "e4" in page.locator("#moves").inner_text().lower()
        browser.close()



def test_academy_coach_speech_bubble_arrows_and_voice_controls(live_server_url: str) -> None:
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_server_url, wait_until="networkidle")
        page.locator('.mobile-tab-btn[data-tab="academy"]').click()
        page.wait_for_selector("#board .square")
        page.wait_for_selector(".academy-coach-callout")
        page.wait_for_selector("#coach-voice-select")
        page.wait_for_selector("#coach-rate-select")
        assert page.locator("#coach-text").inner_text().strip()
        assert page.locator("#coach-explanation").count() == 1
        assert page.locator("#board .board-arrow").count() == 1
        assert page.locator("#board .square.coach-arrow-source").count() == 1
        assert page.locator("#board .square.coach-arrow-target").count() == 1

        # Replace native TTS with a deterministic browser stub for the Listen action.
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
        page.locator("#coach-voice-select").select_option("")
        page.locator("#speak-btn").click()
        page.wait_for_function("Boolean(window.__knightForgeSpoken)")
        assert page.evaluate("window.__knightForgeSpoken").strip()
        page.locator("#stop-speak-btn").click()
        assert "stopped" in page.locator("#coach-voice-status").inner_text().lower()
        browser.close()



def test_academy_renders_board_preview_and_retry_when_training_api_is_offline(
    live_server_url: str,
) -> None:
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route("**/api/lessons**", lambda route: route.abort())
        page.goto(live_server_url, wait_until="networkidle")
        page.locator('.mobile-tab-btn[data-tab="academy"]').click()

        page.wait_for_selector("#academy-connection-alert:not(.hidden)")
        assert page.locator("#board .square").count() == 64
        assert page.locator("#board .piece-wrap").count() == 32
        assert page.locator("#academy-retry-btn").is_visible()
        assert "reconnect" in page.locator("#coach-text").inner_text().lower()
        assert page.locator("#undo-btn").is_disabled()
        assert page.locator("#flip-btn").is_enabled()
        browser.close()

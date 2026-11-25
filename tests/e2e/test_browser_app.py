from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get("KNIGHTFORGE_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session", autouse=True)
def app_server():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "knightforge_engine.server:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    try:
        import urllib.request

        for _ in range(60):
            try:
                with urllib.request.urlopen(BASE_URL + "/api/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, TimeoutError):
                time.sleep(0.5)
        else:
            raise RuntimeError("KnightForge server did not become healthy.")
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1365, "height": 900})
        page = context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        yield page
        context.close()
        browser.close()


def test_main_board_loads_and_supports_legal_move_undo_restart(page: Page) -> None:
    expect(page.locator("#connection-label")).to_have_text("SESSION ACTIVE")
    expect(page.locator("#board .square")).to_have_count(64)
    page.locator('#board button[aria-label="e2 P"]').click()
    expect(page.locator("#board .square.legal")).not_to_have_count(0)
    page.locator('#board button[aria-label="e4 empty"]').click()
    expect(page.locator("#move-count")).to_have_text("1 half-moves")
    expect(page.locator("#moves")).to_contain_text("e4")
    page.locator("#undo-btn").click()
    expect(page.locator("#move-count")).to_have_text("0 half-moves")
    page.locator("#restart-btn").click()
    expect(page.locator("#board .square")).to_have_count(64)


def test_mastery_mode_hides_hints(page: Page) -> None:
    page.locator("#mode-select").select_option("mastery")
    expect(page.locator("#coach-text")).to_contain_text("Mastery test")
    expect(page.locator("#hint-btn")).to_be_disabled()
    expect(page.locator("#hint-btn")).to_contain_text("Hints disabled")


def test_opening_explorer_and_training_load(page: Page) -> None:
    expect(page.locator("#opening-list .opening-card").first).to_be_visible()
    page.locator("#opening-list .opening-card").first.click()
    expect(page.locator("#study-name")).not_to_contain_text("Choose a study")
    expect(page.locator("#variation-tree .variation-move").first).to_be_visible()
    page.locator("#training-start").click()
    expect(page.locator("#training-progress")).not_to_contain_text("No training session active")


def test_tactics_trainer_loads_and_starts(page: Page) -> None:
    expect(page.locator("#tactics-puzzle option")).to_have_count(3)
    page.locator("#tactics-start").click()
    expect(page.locator("#tactics-board .tactics-square")).to_have_count(64)
    expect(page.locator("#tactics-restart")).to_be_enabled()


def test_strategy_lessons_exercises_and_analyzer(page: Page) -> None:
    expect(page.locator("#strategy-lesson-list .strategy-lesson-button").first).to_be_visible()
    expect(page.locator("#strategy-exercise option")).not_to_have_count(0)
    page.locator("#strategy-start").click()
    expect(page.locator("#strategy-board .tactics-square")).to_have_count(64)
    page.locator("#analysis-run").click()
    expect(page.locator("#analysis-results")).not_to_be_empty()


def test_mobile_layout_has_no_horizontal_page_overflow(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.reload(wait_until="networkidle")
    expect(page.locator("#board .square")).to_have_count(64)
    dimensions = page.evaluate(
        "() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})"
    )
    assert dimensions["scroll"] <= dimensions["client"] + 1

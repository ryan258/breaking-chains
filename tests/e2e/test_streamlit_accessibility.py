import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


def _rgb_channels(css_color: str) -> tuple[int, int, int]:
    return tuple(
        int(channel.strip())
        for channel in css_color.removeprefix("rgb(").removesuffix(")").split(",")
    )


def _relative_luminance(css_color: str) -> float:
    channels = tuple(channel / 255 for channel in _rgb_channels(css_color))
    linear = tuple(
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    )
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _unused_loopback_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@pytest.fixture
def streamlit_url(tmp_path: Path) -> Iterator[str]:
    project_root = Path(__file__).parents[2]
    port = _unused_loopback_port()
    environment = os.environ.copy()
    environment.update(
        {
            "OPENROUTER_API_KEY": "browser-test-key-never-used",
            "FORGE_DATA_DIR": str(tmp_path / "data"),
            "FORGE_OUTPUT_DIR": str(tmp_path / "outputs"),
            "FORGE_LOG_DIR": str(tmp_path / "logs"),
        }
    )
    for role in (
        "LEAD",
        "RESEARCHER",
        "CONNECTION_FINDER",
        "SYNTHESIZER",
        "SKEPTIC",
        "EXPERIMENT_DESIGNER",
    ):
        environment[f"FORGE_MODEL_{role}"] = "test/model"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(project_root / "src/forge/ui/streamlit_app.py"),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    process = subprocess.Popen(
        command,
        cwd=project_root,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:  # noqa: S310
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.1)
    else:
        process.terminate()
        raise RuntimeError("Streamlit did not start on its loopback test address")
    try:
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture
def page() -> Iterator[Page]:
    """Use an isolated browser without pytest-playwright's async-test hook."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        yield context.new_page()
        context.close()
        browser.close()


def _prepare_decision_page(page: Page, url: str) -> None:
    page.goto(url)
    page.get_by_role("textbox", name="What are you investigating?").fill(
        "Verify the accessible decision contract."
    )
    page.get_by_role("button", name="Open case").click()
    page.get_by_role("button", name="A — Quick").click()
    expect(page.get_by_role("button", name="A — Approve live execution")).to_be_visible()


def test_ae_targets_have_names_minimum_size_logical_focus_and_visible_focus(
    page: Page,
    streamlit_url: str,
) -> None:
    _prepare_decision_page(page, streamlit_url)
    buttons = [
        page.get_by_role("button", name=f"{letter} — {label}")
        for letter, label in (
            ("A", "Approve live execution"),
            ("B", "Stop before starting"),
            ("C", "Review configuration"),
            ("D", "Use deterministic preview"),
            ("E", "Custom answer"),
        )
    ]

    for width in (320, 768, 1024, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        for button in buttons:
            box = button.bounding_box()
            assert box is not None
            assert box["width"] >= 44
            assert box["height"] >= 44
            assert box["x"] >= 3
            assert box["x"] + box["width"] <= width - 3

    page.set_viewport_size({"width": 320, "height": 900})
    buttons[1].focus()
    page.keyboard.press("Shift+Tab")
    for index, button in enumerate(buttons):
        expect(button).to_be_focused()
        style = button.evaluate(
            "element => ({"
            "style: getComputedStyle(element).outlineStyle,"
            "width: getComputedStyle(element).outlineWidth"
            "})"
        )
        assert style["style"] != "none"
        assert float(style["width"].removesuffix("px")) >= 3
        if index < len(buttons) - 1:
            page.keyboard.press("Tab")


def test_case_file_theme_has_a_dark_tactile_surface_and_readable_display_type(
    page: Page,
    streamlit_url: str,
) -> None:
    page.goto(streamlit_url)
    case_panel = page.locator(".st-key-case_start")
    expect(case_panel).to_be_visible()

    panel_style = case_panel.evaluate(
        "element => ({"
        "background: getComputedStyle(element).backgroundColor,"
        "border: getComputedStyle(element).borderTopColor,"
        "radius: getComputedStyle(element).borderTopLeftRadius"
        "})"
    )
    assert panel_style["background"] == "rgb(22, 20, 17)"
    assert _contrast_ratio(panel_style["border"], panel_style["background"]) >= 3
    assert float(panel_style["radius"].removesuffix("px")) <= 4

    seed_input = page.get_by_role("textbox", name="What are you investigating?")
    input_style = seed_input.evaluate(
        "element => ({"
        "background: getComputedStyle(element).backgroundColor,"
        "border: getComputedStyle(element).borderTopColor"
        "})"
    )
    assert _contrast_ratio(input_style["border"], input_style["background"]) >= 3

    heading = page.get_by_role("heading", name="Start a case")
    heading_style = heading.evaluate(
        "element => ({"
        "color: getComputedStyle(element).color,"
        "family: getComputedStyle(element).fontFamily"
        "})"
    )
    assert heading_style["color"] == "rgb(231, 213, 176)"
    assert "serif" in heading_style["family"].lower()


def test_ae_controls_activate_with_enter_and_space_and_expose_text_status(
    page: Page,
    streamlit_url: str,
) -> None:
    _prepare_decision_page(page, streamlit_url)
    custom = page.get_by_role("button", name="E — Custom answer")
    custom.focus()
    page.keyboard.press("Enter")
    expect(page.get_by_label("Custom answer")).to_be_visible()
    decision_panel = page.locator(".st-key-decision_panel")
    expect(decision_panel.get_by_label("Custom answer")).to_be_visible()
    expect(decision_panel.get_by_role("button", name="Submit custom answer")).to_be_visible()

    second_page = page.context.new_page()
    _prepare_decision_page(second_page, streamlit_url)
    preview = second_page.get_by_role("button", name="D — Use deterministic preview")
    preview.focus()
    second_page.keyboard.press("Space")
    focus = second_page.get_by_role("button", name="A — Trace constraints")
    expect(focus).to_be_visible()
    focus.focus()
    second_page.keyboard.press("Enter")

    expect(second_page.locator("strong").filter(has_text="Stage:")).to_be_visible()
    expect(second_page.locator("strong").filter(has_text="Status:")).to_be_visible()
    expect(second_page.locator("strong").filter(has_text="Mode:")).to_be_visible()
    expect(second_page.get_by_text("Confidence:").first).to_be_attached()


def test_ae_keys_answer_the_visible_question_without_stealing_typed_text(
    page: Page,
    streamlit_url: str,
) -> None:
    seed = "Drive the **whole** run for $5?\nSecond line"
    page.goto(streamlit_url)
    page.get_by_role("textbox", name="What are you investigating?").fill(seed)
    page.get_by_role("button", name="Open case").click()
    expect(page.get_by_role("button", name="A — Quick")).to_be_visible()

    page.keyboard.press("a")
    expect(page.get_by_role("button", name="D — Use deterministic preview")).to_be_visible()
    page.keyboard.press("d")
    expect(page.get_by_role("button", name="A — Trace constraints")).to_be_visible()

    page.keyboard.press("e")
    custom_box = page.get_by_label("Custom answer")
    expect(custom_box).to_be_visible()
    custom_box.click()
    custom_box.type("abcde stays typed text")
    expect(custom_box).to_have_value("abcde stays typed text")

    page.get_by_role("button", name="Submit custom answer").click()
    expect(page.get_by_role("button", name="A — Accept")).to_be_visible()
    page.keyboard.press("a")
    expect(page.get_by_role("button", name="A — Accept action")).to_be_visible()
    page.keyboard.press("a")
    expect(page.locator("strong").filter(has_text="Stage:")).to_be_visible()
    expect(
        page.get_by_role(
            "heading",
            name="Drive the **whole** run for $5? Second line",
            level=3,
        )
    ).to_be_visible()


def test_validation_failure_is_explained_in_text(page: Page, streamlit_url: str) -> None:
    page.goto(streamlit_url)
    page.get_by_role("button", name="Open case").click()

    expect(
        page.get_by_text('Enter a question in "What are you investigating?" before continuing.')
    ).to_be_visible()

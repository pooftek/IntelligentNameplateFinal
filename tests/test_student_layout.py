"""
test_student_layout.py — No-scroll layout regression tests for the student nameplate.

The student login and settings screens must fit one viewport (no vertical scroll) on
both a laptop (nameplate front screen visible → back panel gets ~half the height) and a
phone (front hidden → back panel full height). We assert the scroll container's content
height does not exceed its client height at both sizes.
"""
import pytest

LAPTOP = {"width": 1440, "height": 900}
PHONE = {"width": 390, "height": 844}

# scrollHeight > clientHeight means the element is scrolling — i.e. content overflowed.
OVERFLOW_JS = """(sel) => {
    const e = document.querySelector(sel);
    if (!e) return null;
    return {scrollH: e.scrollHeight, clientH: e.clientHeight};
}"""


@pytest.mark.parametrize("size", [LAPTOP, PHONE], ids=["laptop", "phone"])
def test_student_login_fits_viewport(live_server, page, size):
    """The login panel must not scroll at laptop or phone sizes."""
    page.set_viewport_size(size)
    page.goto(f"{live_server}/student", wait_until="domcontentloaded")
    page.wait_for_selector("#sleepBack", timeout=3000)
    page.dispatch_event("#sleepBack", "pointerdown")  # wake() → login screen
    page.wait_for_selector("#backLogin:not(.panel-hidden)", timeout=3000)

    box = page.evaluate(OVERFLOW_JS, "#backLogin")
    assert box is not None, "login panel not found"
    assert box["scrollH"] <= box["clientH"] + 1, f"login panel scrolls at {size}: {box}"


@pytest.mark.parametrize("size", [LAPTOP, PHONE], ids=["laptop", "phone"])
def test_student_settings_fits_viewport(live_server, page, size):
    """The settings content region must not scroll at laptop or phone sizes."""
    page.set_viewport_size(size)
    page.goto(f"{live_server}/student", wait_until="domcontentloaded")
    page.wait_for_selector("#backSettings", state="attached", timeout=3000)
    # Reveal the (static) settings panel without needing a full login flow.
    page.evaluate(
        """() => {
        document.getElementById('npRoot').className = 'np-root state-home';
        ['backLogin', 'backHome', 'backSession', 'backGrades'].forEach(id => {
            const e = document.getElementById(id);
            if (e) e.classList.add('panel-hidden');
        });
        document.getElementById('backSettings').classList.remove('panel-hidden');
    }"""
    )

    box = page.evaluate(OVERFLOW_JS, ".settings-content")
    assert box is not None, "settings content region not found"
    assert box["scrollH"] <= box["clientH"] + 1, f"settings scrolls at {size}: {box}"

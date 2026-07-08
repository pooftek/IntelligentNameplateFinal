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
# Raspberry Pi nameplate: two 1920x480 DSI panels STACKED into one 1920x960 (2:1) touchscreen.
PI = {"width": 1920, "height": 960}
TABLET = {"width": 1366, "height": 1024}
PHONE_LANDSCAPE = {"width": 926, "height": 428}

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


# display of the (body-level) on-screen keyboard: "none" when dormant, "flex" when open.
OSK_DISPLAY_JS = "() => getComputedStyle(document.getElementById('osk')).display"


def _wake_to_login(page, server):
    """Open /student and wake it to the login screen (the RFID/manual login card)."""
    page.goto(f"{server}/student", wait_until="domcontentloaded")
    page.wait_for_selector("#sleepBack", timeout=3000)
    page.dispatch_event("#sleepBack", "pointerdown")  # wake() → login screen
    page.wait_for_selector("#backLogin:not(.panel-hidden)", timeout=3000)


def test_osk_opens_and_types_on_pi(live_server, browser):
    """On the stacked 1920x960 (2:1) touch Pi, tapping a login field opens the on-screen
    keyboard and its keys type into the focused field."""
    context = browser.new_context(viewport=PI, is_mobile=True, has_touch=True)
    page = context.new_page()
    try:
        _wake_to_login(page, live_server)
        assert page.evaluate(OSK_DISPLAY_JS) == "none", "keyboard should start hidden"
        page.focus("#loginIdentifier")
        assert page.evaluate(OSK_DISPLAY_JS) != "none", "keyboard did not open on the Pi"
        assert page.evaluate("() => document.body.classList.contains('kb-open')"), \
            "login card was not shifted (body.kb-open missing)"
        # Type + shift (uppercase) + backspace all round-trip into the focused field.
        page.tap("#osk .osk-key[data-k='a']")
        assert page.input_value("#loginIdentifier") == "a"
        page.tap("#osk .osk-key[data-k='{shift}']")
        page.tap("#osk .osk-key[data-k='b']")
        assert page.input_value("#loginIdentifier") == "aB"
        page.tap("#osk .osk-key[data-k='{bksp}']")
        assert page.input_value("#loginIdentifier") == "a"
    finally:
        context.close()


@pytest.mark.parametrize("size", [TABLET, PHONE_LANDSCAPE], ids=["tablet", "phone_landscape"])
def test_osk_dormant_on_other_touch_devices(live_server, browser, size):
    """Touch devices that aren't the wide 2:1 Pi — a 4:3 tablet (fails the aspect ratio) and a
    phone held sideways (fails the min-width) — must never surface the keyboard."""
    context = browser.new_context(viewport=size, is_mobile=True, has_touch=True)
    page = context.new_page()
    try:
        _wake_to_login(page, live_server)
        page.focus("#loginIdentifier")
        assert page.evaluate(OSK_DISPLAY_JS) == "none", f"keyboard leaked onto {size}"
    finally:
        context.close()


def test_osk_dormant_on_wide_fine_pointer(live_server, browser):
    """A wide 2:1 display driven by a real pointer (mouse/trackpad → pointer:fine) must NOT get
    the touch keyboard; only pointer:coarse (the Pi's touch panel) does."""
    context = browser.new_context(viewport=PI)  # no has_touch → pointer: fine
    page = context.new_page()
    try:
        _wake_to_login(page, live_server)
        page.focus("#loginIdentifier")
        assert page.evaluate(OSK_DISPLAY_JS) == "none", "keyboard leaked onto a fine-pointer display"
    finally:
        context.close()


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

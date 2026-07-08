"""
test_tablet_layout.py — Layout regression tests for the Android tablet facelift fix.

Guards two tablet bugs:
1. My Classes (portrait): the flex-nowrap header let the title + pill buttons
   collide with the class cards below — the title must clear the first card and
   the button row must not overflow the viewport width.
2. The fixed-viewport pages (classroom, students) must fit their shell so the
   settings buttons / content sit within the viewport (no clipped bottom).

Headless Chromium resolves 100dvh == 100vh (no browser toolbar), so these assert
the fit; the 100dvh swap itself is what makes the same layout reachable under the
real tablet's browser chrome.

Round 2 (touch tests below): real tablets report desktop CSS widths (or run
desktop-site mode), so width breakpoints alone never fire — the fixes key on
`(pointer: coarse)` instead. `has_touch=True` makes Chromium report a coarse
pointer; the touch context deliberately uses a 1280×600 viewport (landscape
minus browser chrome) to exercise the released-lock overflow path.
"""
import pytest

PORTRAIT = {"width": 800, "height": 1280}
LANDSCAPE = {"width": 1280, "height": 800}
TOUCH_LANDSCAPE = {"width": 1280, "height": 600}

RECT_JS = """(sel) => {
    const e = document.querySelector(sel);
    if (!e) return null;
    const b = e.getBoundingClientRect();
    return {top: b.top, right: b.right, bottom: b.bottom, left: b.left, height: b.height};
}"""


def test_my_classes_title_clears_cards_portrait(live_server, professor_page, created_class):
    """Portrait: the 'My Classes' title must sit fully above the first card."""
    page = professor_page
    page.set_viewport_size(PORTRAIT)
    page.goto(f"{live_server}/dashboard", wait_until="networkidle")

    title = page.evaluate(RECT_JS, ".responsive-title")
    card = page.evaluate(RECT_JS, ".class-card")
    buttons = page.evaluate(RECT_JS, ".header-buttons")

    assert card is not None, "no class card rendered — created_class fixture missing"
    assert title["bottom"] <= card["top"], "page title overlaps the first class card"
    assert buttons["right"] <= PORTRAIT["width"] + 1, "header buttons overflow the viewport width"


def test_dashboard_logo_at_fold_laptop(live_server, professor_page, created_class):
    """Laptop (fine pointer), any normal window: the branding logo sits at the
    viewport bottom with no page scroll — the page must not exceed 100dvh when
    the cards fit (guards the 'logo hidden behind the taskbar' regression)."""
    page = professor_page
    for vp in ({"width": 1280, "height": 620}, {"width": 1600, "height": 800}, {"width": 1024, "height": 495}):
        page.set_viewport_size(vp)
        page.goto(f"{live_server}/dashboard", wait_until="networkidle")
        doc_h, inner_h = page.evaluate("[document.documentElement.scrollHeight, innerHeight]")
        assert doc_h <= inner_h + 1, f"{vp}: page {doc_h}px overflows {inner_h}px viewport — logo below the fold"
        branding = page.evaluate(RECT_JS, ".dashboard-branding")
        assert branding["bottom"] <= inner_h + 1, f"{vp}: branding logo below the fold"


def test_classroom_settings_within_viewport_landscape(live_server, professor_page, created_class):
    """Landscape on a normal (fine-pointer) laptop: the fixed shell stays LOCKED
    (desktop look preserved — the coarse-pointer release must not leak to laptops)
    and the settings card fits within it."""
    page = professor_page
    page.set_viewport_size(LANDSCAPE)
    page.goto(f"{live_server}/classroom/{created_class}", wait_until="networkidle")

    assert page.evaluate("getComputedStyle(document.body).overflowY") == "hidden", \
        "laptop lost the fixed-viewport lock — tablet release leaked to fine-pointer devices"
    settings = page.evaluate(RECT_JS, "#settingsCard")
    assert settings is not None, "settings card not found on classroom page"
    assert settings["bottom"] <= LANDSCAPE["height"] + 1, "settings card clipped below the viewport"


def test_students_content_fits_portrait(live_server, professor_page, created_class):
    """Portrait: the scrollable students content region must fit within the shell."""
    page = professor_page
    page.set_viewport_size(PORTRAIT)
    page.goto(f"{live_server}/classroom/{created_class}/students", wait_until="networkidle")

    content = page.evaluate(RECT_JS, ".students-content")
    assert content is not None, "students content region not found"
    assert content["bottom"] <= PORTRAIT["height"] + 1, "students content clipped below the viewport"


# ── Touch (coarse pointer) tests ──

DISPLAY_JS = "(sel) => getComputedStyle(document.querySelector(sel)).display"


@pytest.fixture
def touch_page(live_server, registered_professor, browser):
    """Logged-in page in a touch context so `(pointer: coarse)` media queries fire."""
    ctx = browser.new_context(viewport=TOUCH_LANDSCAPE, has_touch=True)
    page = ctx.new_page()
    page.goto(f"{live_server}/login", wait_until="domcontentloaded")
    page.fill("#email", registered_professor["email"])
    page.fill("#password", registered_professor["password"])
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/dashboard", timeout=15000, wait_until="domcontentloaded")
    yield page
    ctx.close()


def test_classroom_releases_lock_on_touch(live_server, touch_page, created_class):
    """Coarse pointer: the 100dvh/overflow-hidden lock releases so the page can scroll."""
    page = touch_page
    page.goto(f"{live_server}/classroom/{created_class}", wait_until="networkidle")

    assert page.evaluate("matchMedia('(pointer: coarse)').matches"), "context is not coarse-pointer"
    assert page.evaluate("getComputedStyle(document.body).overflowY") == "auto", \
        "body still overflow:hidden on touch — lock not released"

    page.locator("#settingsCard").scroll_into_view_if_needed()
    settings = page.evaluate(RECT_JS, "#settingsCard")
    assert settings["bottom"] <= TOUCH_LANDSCAPE["height"] + 1, "settings card unreachable by scrolling"


def test_single_logo_on_touch(live_server, touch_page):
    """Dashboard hides the base footer for its own branding; the auth pages now show
    only the single centered logo (no base footer, no top-left brand)."""
    page = touch_page
    page.goto(f"{live_server}/dashboard", wait_until="networkidle")
    assert page.locator(".comet-footer").count() == 0, "dashboard should not render the base footer"
    assert page.locator(".dashboard-branding img").is_visible(), "dashboard's own branding missing"

    page.goto(f"{live_server}/login", wait_until="networkidle")
    assert page.locator(".comet-footer").count() == 0, "login should not render the base footer"
    assert page.locator(".auth-topbar .brand").count() == 0, "login should not show the top-left brand"
    assert page.locator('img[src*="comet_logo"]').count() == 1, "login should show exactly one logo"


def test_landing_hides_nodes_on_touch(live_server, browser):
    """Touch at desktop width (1280 > 820): nodes and meteors must be hidden.
    Landing is public, so use an anonymous touch context (`/` redirects a logged-in
    professor to the dashboard, which has no nodes/meteors)."""
    ctx = browser.new_context(viewport=TOUCH_LANDSCAPE, has_touch=True)
    page = ctx.new_page()
    try:
        page.goto(f"{live_server}/", wait_until="networkidle")
        assert page.evaluate(DISPLAY_JS, "#nodes") == "none", "nodes visible on touch tablet"
        assert page.evaluate(DISPLAY_JS, "#meteors") == "none", "meteors visible on touch tablet"
    finally:
        ctx.close()

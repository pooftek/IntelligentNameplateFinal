"""
test_landing_layout.py — Layout regression tests for the public landing page.

Guards the short-laptop fix (1080p @ 150% Windows scaling ≈ 1280×620 CSS px):
the nameplate device must never cover the section copy or the software cards,
and the About / Inquire sections must each fit within one viewport height.
nameplate.png has transparent margins — the visible device occupies roughly
30%–78% of the image box vertically, so assertions use those visual edges.
"""

# ThinkPad-class viewport: 1920×1080 at 150% scaling, minus browser chrome
VIEWPORT = {"width": 1280, "height": 620}

DEVICE_VISUAL_TOP = 0.30
DEVICE_VISUAL_BOTTOM = 0.78

RECT_JS = """(sel) => {
    const e = document.querySelector(sel);
    const b = e.getBoundingClientRect();
    return {top: b.top, bottom: b.bottom, height: b.height};
}"""

# Content height of a section = union of its children (the section itself is
# min-height:100vh, so measuring it directly would always equal the viewport).
CONTENT_JS = """(sel) => {
    const kids = Array.from(document.querySelector(sel).children)
        .map(c => c.getBoundingClientRect());
    return Math.max(...kids.map(b => b.bottom)) - Math.min(...kids.map(b => b.top));
}"""


def scroll_to_assembled(page):
    """Land on the assembled-nameplate state, same math as the nav tab click."""
    page.evaluate("""() => {
        const stage = document.querySelector('.stage');
        const total = stage.offsetHeight - window.innerHeight;
        window.scrollTo(0, stage.offsetTop + total * 0.82);
    }""")
    page.wait_for_timeout(800)


def test_nameplate_clears_copy_and_cards(live_server, page):
    """Assembled state: section copy above the device, cards below it, all on screen."""
    page.set_viewport_size(VIEWPORT)
    page.goto(f"{live_server}/", wait_until="networkidle")
    scroll_to_assembled(page)

    device = page.evaluate(RECT_JS, ".device-wrap")
    visual_top = device["top"] + DEVICE_VISUAL_TOP * device["height"]
    visual_bottom = device["top"] + DEVICE_VISUAL_BOTTOM * device["height"]

    np_copy = page.evaluate(RECT_JS, ".np-copy")
    cards = page.evaluate(RECT_JS, ".np-cards")

    assert np_copy["bottom"] <= visual_top, "nameplate copy runs behind the device"
    assert cards["top"] >= visual_bottom, "software cards cover the device"
    assert cards["bottom"] <= VIEWPORT["height"], "software cards fall below the fold"


def test_hero_cta_clears_device(live_server, page):
    """Hero: CTA buttons sit above the device, device fully on screen."""
    page.set_viewport_size(VIEWPORT)
    page.goto(f"{live_server}/", wait_until="networkidle")
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)

    device = page.evaluate(RECT_JS, ".device-wrap")
    visual_top = device["top"] + DEVICE_VISUAL_TOP * device["height"]
    cta = page.evaluate(RECT_JS, ".cta-row")

    assert cta["bottom"] <= visual_top, "hero CTA buttons overlap the device"
    assert device["bottom"] <= VIEWPORT["height"], "hero device clipped by the fold"


def test_about_and_contact_fit_one_screen(live_server, page):
    """About and Inquire content each fit under the 11vh topbar-clearing padding."""
    page.set_viewport_size(VIEWPORT)
    page.goto(f"{live_server}/", wait_until="networkidle")

    budget = VIEWPORT["height"] - 0.11 * VIEWPORT["height"]
    for section in ("#about", "#contact"):
        page.evaluate(f"document.querySelector('{section}').scrollIntoView()")
        page.wait_for_timeout(500)
        content = page.evaluate(CONTENT_JS, section)
        assert content <= budget, f"{section} content ({content:.0f}px) taller than {budget:.0f}px"

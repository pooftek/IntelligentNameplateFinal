"""
test_seo.py — SEO metadata, crawler files, and heading/favicon regression guards.

Covers the public landing page's <head> signals (description, canonical,
Open Graph, JSON-LD), the single <h1>, the /robots.txt + /sitemap.xml routes,
and the student page favicon fix.
"""
import json
import xml.dom.minidom


def test_robots_txt(live_server, page):
    """/robots.txt is served as plain text and points at the sitemap."""
    resp = page.request.get(f"{live_server}/robots.txt")
    assert resp.status == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text()
    assert "Sitemap:" in body
    assert "Disallow: /api/" in body


def test_sitemap_xml(live_server, page):
    """/sitemap.xml is well-formed XML listing the public homepage."""
    resp = page.request.get(f"{live_server}/sitemap.xml")
    assert resp.status == 200
    assert "xml" in resp.headers["content-type"]
    body = resp.text()
    xml.dom.minidom.parseString(body)  # raises if malformed
    assert "https://cometinc.ca/" in body


def test_landing_has_single_h1(live_server, page):
    """The landing page has exactly one <h1> (the SEO heading fix)."""
    page.goto(f"{live_server}/", wait_until="domcontentloaded")
    assert page.locator("h1").count() == 1


def test_landing_head_seo_tags(live_server, page):
    """Landing head carries description, canonical, OG image, and valid JSON-LD."""
    page.goto(f"{live_server}/", wait_until="domcontentloaded")
    assert page.locator('meta[name="description"]').count() == 1
    assert page.locator('link[rel="canonical"]').get_attribute("href") == "https://cometinc.ca/"
    assert page.locator('meta[property="og:image"]').count() == 1
    ld = page.locator('script[type="application/ld+json"]').text_content()
    json.loads(ld)  # raises if not valid JSON


def test_student_page_has_favicon(live_server, page):
    """The student nameplate page carries the Comet favicon (regression guard)."""
    page.goto(f"{live_server}/student", wait_until="domcontentloaded")
    assert page.locator('link[rel="icon"]').count() >= 1

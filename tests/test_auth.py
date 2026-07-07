"""
test_auth.py — Tests for professor login, register, and logout.

Each test opens a real browser and goes through the actual UI —
exactly like a user would. If something breaks (wrong redirect,
missing error message, etc.) the test fails and tells you what went wrong.
"""
import pytest


def test_login_page_loads(live_server, page):
    """The login page should show an email login form and password recovery link."""
    page.goto(f"{live_server}/login")
    assert page.locator("#email").is_visible()
    assert page.locator("#password").is_visible()
    assert page.get_by_role("link", name="Forgot Password?").is_visible()


def test_login_page_has_no_username_field(live_server, page):
    """Login is email-only — the old username field must be gone."""
    page.goto(f"{live_server}/login")
    assert page.locator("#username").count() == 0
    assert page.locator("#email").get_attribute("type") == "email"


def test_forgot_password_shows_confirmation(live_server, registered_professor, page):
    """Submitting the forgot-password form always shows the generic success message."""
    page.goto(f"{live_server}/forgot-password")
    page.fill("#accountEmail", registered_professor["email"])
    page.click("button[type=submit]")
    page.wait_for_selector("#statusMessage:visible", timeout=5000)
    text = page.locator("#statusMessage").inner_text().lower()
    assert "account" in text and "email" in text


def test_register_new_professor(live_server, page):
    """A new professor can register and gets sent to the dashboard."""
    page.goto(f"{live_server}/register")
    page.fill("#fullName", "New Prof Test")
    page.fill("#email", "newprof@comet.test")
    page.fill("#password", "SecurePass123!")
    page.fill("#confirmPassword", "SecurePass123!")
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/dashboard", timeout=15000, wait_until="domcontentloaded")
    assert "/dashboard" in page.url


def test_register_duplicate_email(live_server, registered_professor, page):
    """Registering with an existing email should show an error."""
    page.goto(f"{live_server}/register")
    page.fill("#fullName", "Different Person")
    page.fill("#email", registered_professor["email"])
    page.fill("#password", "SecurePass123!")
    page.fill("#confirmPassword", "SecurePass123!")
    page.click("button[type=submit]")
    # Should stay on register page and show an error
    page.wait_for_selector("#errorMessage:visible", timeout=3000)
    assert page.locator("#errorMessage").is_visible()


def test_register_duplicate_full_name_succeeds(live_server, registered_professor, page):
    """Two professors may share a name — only the email must be unique."""
    page.goto(f"{live_server}/register")
    page.fill("#fullName", registered_professor["full_name"])
    page.fill("#email", "samename@comet.test")
    page.fill("#password", "SecurePass123!")
    page.fill("#confirmPassword", "SecurePass123!")
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/dashboard", timeout=15000, wait_until="domcontentloaded")
    assert "/dashboard" in page.url


def test_register_password_mismatch(live_server, page):
    """Mismatched passwords should show a client-side error."""
    page.goto(f"{live_server}/register")
    page.fill("#fullName", "Another New Prof")
    page.fill("#email", "another@comet.test")
    page.fill("#password", "password1")
    page.fill("#confirmPassword", "password2")
    page.click("button[type=submit]")
    page.wait_for_selector("#errorMessage:visible", timeout=3000)
    assert "do not match" in page.locator("#errorMessage").inner_text().lower()


def test_login_valid_credentials(live_server, registered_professor, page):
    """Login with correct credentials redirects to dashboard."""
    page.goto(f"{live_server}/login")
    page.fill("#email", registered_professor["email"])
    page.fill("#password", registered_professor["password"])
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)
    assert "/dashboard" in page.url


def test_login_invalid_password(live_server, registered_professor, page):
    """Login with wrong password should show an error message."""
    page.goto(f"{live_server}/login")
    page.fill("#email", registered_professor["email"])
    page.fill("#password", "wrongpassword")
    page.click("button[type=submit]")
    page.wait_for_selector("#errorMessage:visible", timeout=3000)
    assert page.locator("#errorMessage").is_visible()


def test_account_settings_page_loads_when_logged_in(live_server, professor_page, registered_professor):
    """Account settings shows full name and email fields when logged in as a professor."""
    professor_page.goto(f"{live_server}/preferences/account")
    professor_page.wait_for_url(f"{live_server}/preferences/account", timeout=5000)
    assert professor_page.locator("#accFullName").is_visible()
    assert professor_page.locator("#accEmail").is_visible()
    assert professor_page.locator("#accFullName").input_value() == registered_professor["full_name"]
    assert professor_page.locator("#accEmail").input_value() == registered_professor["email"]


def test_logout(live_server, professor_page):
    """Logging out redirects to the login page."""
    professor_page.goto(f"{live_server}/logout")
    professor_page.wait_for_url(f"{live_server}/login", timeout=5000)
    assert "/login" in professor_page.url


def test_protected_route_redirects_when_not_logged_in(live_server, page):
    """Visiting /dashboard without being logged in should redirect to login."""
    page.goto(f"{live_server}/dashboard")
    page.wait_for_url("**/login**", timeout=5000)
    assert "login" in page.url


@pytest.mark.parametrize("path", ["/login", "/register", "/forgot-password"])
def test_auth_pages_have_single_logo(live_server, page, path):
    """Auth pages show only the one centered logo — no top-left brand, no footer logo."""
    page.goto(f"{live_server}{path}", wait_until="domcontentloaded")
    assert page.locator('img[src*="comet_logo"]').count() == 1
    assert page.locator(".comet-footer").count() == 0
    assert page.locator(".auth-topbar .brand").count() == 0

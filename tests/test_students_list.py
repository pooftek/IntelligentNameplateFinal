"""
test_students_list.py — Tab behaviour on the class students page.

Deactivating, removing, adding, editing, or importing students must leave the
professor on the tab they were viewing (the page previously jumped tabs).
"""
import uuid


def _create_class(page):
    """Create a fresh class so tab actions never disturb the shared fixture class."""
    code = "ST" + uuid.uuid4().hex[:6].upper()
    response = page.evaluate("""async (class_code) => {
        const r = await fetch('/api/create_class', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: 'Tab Test Class', class_code})
        });
        return r.json();
    }""", code)
    assert response.get("class_id"), f"create_class failed: {response!r}"
    return response["class_id"]


def _add_student(page, cid):
    """Enroll a brand-new student with unique number/email; returns student id."""
    digits = str(int(uuid.uuid4().hex[:8], 16) % 10**9).zfill(9)
    response = page.evaluate("""async ([cid, num]) => {
        const r = await fetch(`/api/create_and_add_student/${cid}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                first_name: 'Tab', last_name: 'Tester' + num.slice(-3),
                student_number: num, email: `tab${num}@comet.test`
            })
        });
        return r.json();
    }""", [cid, digits])
    assert response.get("success"), f"create_and_add_student failed: {response!r}"
    return response["student"]["id"]


def _deactivate_via_api(page, cid, student_id):
    response = page.evaluate("""async ([cid, sid]) => {
        const r = await fetch(`/api/toggle_student_status/${cid}/${sid}`, { method: 'POST' });
        return r.json();
    }""", [cid, student_id])
    assert response.get("success"), f"toggle_student_status failed: {response!r}"


def test_deactivate_keeps_active_tab(live_server, professor_page):
    """Deactivating from the Active tab must not jump to the Inactive tab."""
    page = professor_page
    cid = _create_class(page)
    _add_student(page, cid)

    page.on("dialog", lambda d: d.accept())
    page.goto(f"{live_server}/classroom/{cid}/students", wait_until="domcontentloaded")

    row = page.locator("#activeStudentsTableBody tr[data-student-id]").first
    row.locator(".btn-status.active").click()

    # Row moves to the inactive table without a reload
    page.wait_for_selector("#inactiveStudentsTableBody tr[data-student-id]", state="attached", timeout=5000)
    assert "active" in page.locator("#activeTabBtn").get_attribute("class")
    assert page.locator("#activePanel").is_visible()


def test_remove_keeps_inactive_tab(live_server, professor_page):
    """Removing from the Inactive tab reloads the page but must land back on Inactive."""
    page = professor_page
    cid = _create_class(page)
    student_id = _add_student(page, cid)
    _deactivate_via_api(page, cid, student_id)

    page.on("dialog", lambda d: d.accept())
    page.goto(f"{live_server}/classroom/{cid}/students", wait_until="domcontentloaded")
    page.click("#inactiveTabBtn")

    row = page.locator(f"#inactiveStudentsTableBody tr[data-student-id='{student_id}']")
    row.locator(".btn-remove-student").click()

    # removeStudent() reloads the page — the old row detaching proves the new
    # DOM arrived (wait_for_load_state can return before the reload commits)
    row.wait_for(state="detached", timeout=10000)
    page.wait_for_selector("#inactiveTabBtn.active", timeout=5000)
    assert page.locator("#inactivePanel").is_visible()
    assert not page.locator("#activePanel").is_visible()

"""Every page renders for a signed-in user that has some data."""

import pytest
from conftest import char_id

from xuehanzi.models import Tag


@pytest.fixture()
def populated(app, alice):
    alice.post("/tags", data={"name": "Lesson 1"})
    with app.app_context():
        tag_id = Tag.query.one().id
        ids = {h: char_id(h) for h in ("爱", "八", "爸爸")}
    alice.post(f"/tags/{tag_id}/characters/{ids['爱']}/add")
    alice.post(f"/tags/{tag_id}/characters/{ids['八']}/add")
    alice.post(f"/characters/{ids['爱']}/progress", data={"is_known": "1", "can_write": "1"})
    alice.post(f"/characters/{ids['八']}/progress", data={"is_known": "1"})
    return alice, tag_id, ids


def test_all_pages_render(populated):
    client, tag_id, ids = populated
    paths = [
        "/",
        "/known",
        "/writable",
        "/hsk/1",
        "/hsk/6",
        "/search",
        "/search?q=ai",
        "/search?q=nothing-matches-this",
        "/tags",
        f"/tags/{tag_id}",
        f"/tags/{tag_id}/search?q=ba",
        f"/tags/{tag_id}/bulk-add",
        f"/characters/{ids['爱']}",
        f"/characters/{ids['爱']}/tags",
        "/practice/read",
        "/practice/read?marked=1",
        f"/practice/read?tags={tag_id}&marked=1",
        "/practice/write",
        "/practice/write?level=1",
        f"/practice/write?tags={tag_id}",
        "/practice/read?level=abc&tags=x",
        "/login",
    ]
    for path in paths:
        response = client.get(path, follow_redirects=False)
        assert response.status_code in (200, 302), (path, response.status_code)
        if path == "/login":
            assert response.status_code == 302  # already signed in


def test_unknown_urls_render_the_404_page(alice):
    response = alice.get("/no/such/page")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_tag_page_groups_by_status(populated):
    client, tag_id, _ = populated
    html = client.get(f"/tags/{tag_id}").data.decode()
    assert "Can read and write (1)" in html
    assert "Can read (1)" in html


def test_stroke_order_images_are_served_only_when_present(app, alice, tmp_path):
    (tmp_path / "hsk1").mkdir()
    (tmp_path / "hsk1" / "爱.png").write_bytes(b"\x89PNG fake")
    app.config["STROKE_ORDER_DIR"] = tmp_path
    with app.app_context():
        ai = char_id("爱")

    page = alice.get(f"/characters/{ai}").data.decode()
    assert "/strokeorder/hsk1/" in page
    assert alice.get("/strokeorder/hsk1/%E7%88%B1.png").status_code == 200
    assert alice.get("/strokeorder/hsk1/missing.png").status_code == 404
    assert alice.get("/strokeorder/../../etc/passwd").status_code == 404

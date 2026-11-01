"""Two users must never see or change each other's data."""

from conftest import char_id

from xuehanzi.extensions import db
from xuehanzi.models import Character, CharacterProgress, Tag, User
from xuehanzi.services import characters as chars


def mark(client, character_id, **flags):
    return client.post(f"/characters/{character_id}/progress", data=flags)


def test_progress_is_private_to_each_user(app, alice, bob):
    with app.app_context():
        ai = char_id("爱")

    mark(alice, ai, is_known="1", can_write="1")

    assert "爱".encode() in alice.get("/known").data
    assert "爱".encode() in alice.get("/writable").data
    assert "爱".encode() not in bob.get("/known").data
    assert "爱".encode() not in bob.get("/writable").data


def test_dashboard_counts_are_per_user(app, make_user, alice, bob):
    with app.app_context():
        mark(alice, char_id("爱"), is_known="1")
        alice_stats = chars.level_stats(User.get_by_username("alice"))
        bob_stats = chars.level_stats(User.get_by_username("bob"))
    assert alice_stats[0]["known"] == 1
    assert bob_stats[0]["known"] == 0
    assert alice_stats[0]["total"] == bob_stats[0]["total"] == 3


def test_marking_does_not_touch_the_other_users_progress(app, alice, bob):
    with app.app_context():
        ai = char_id("爱")
    mark(alice, ai, is_known="1")
    mark(bob, ai, can_write="1")

    with app.app_context():
        rows = {p.user.username: (p.is_known, p.can_write) for p in CharacterProgress.query.all()}
    assert rows == {"alice": (True, False), "bob": (False, True)}


def test_tags_are_private(app, alice, bob):
    alice.post("/tags", data={"name": "Lesson 1"})
    with app.app_context():
        tag = Tag.query.one()
        tag_id = tag.id

    assert b"Lesson 1" in alice.get("/tags").data
    assert b"Lesson 1" not in bob.get("/tags").data

    # Every tag URL answers 404 for somebody else's tag.
    assert bob.get(f"/tags/{tag_id}").status_code == 404
    assert bob.get(f"/tags/{tag_id}/search?q=a").status_code == 404
    assert bob.get(f"/tags/{tag_id}/bulk-add").status_code == 404
    assert bob.post(f"/tags/{tag_id}/bulk-add", data={"characters": "爱"}).status_code == 404
    assert bob.post(f"/tags/{tag_id}/delete").status_code == 404
    with app.app_context():
        ai = char_id("爱")
    assert bob.post(f"/tags/{tag_id}/characters/{ai}/add").status_code == 404

    with app.app_context():
        assert Tag.query.count() == 1
        assert Tag.query.one().characters == []


def test_tag_names_only_need_to_be_unique_per_user(app, alice, bob):
    alice.post("/tags", data={"name": "HSK words"})
    bob.post("/tags", data={"name": "HSK words"})
    duplicate = alice.post("/tags", data={"name": "hsk WORDS"}, follow_redirects=True)
    assert b"already have a tag" in duplicate.data
    with app.app_context():
        assert Tag.query.count() == 2


def test_editing_a_characters_tags_only_affects_own_tags(app, alice, bob):
    alice.post("/tags", data={"name": "A"})
    bob.post("/tags", data={"name": "B"})
    with app.app_context():
        a_tag = Tag.query.filter_by(name="A").one().id
        b_tag = Tag.query.filter_by(name="B").one().id
        ai = char_id("爱")

    alice.post(f"/characters/{ai}/tags", data={"tags": [a_tag, b_tag]})

    with app.app_context():
        assert [c.hanzi for c in db.session.get(Tag, a_tag).characters] == ["爱"]
        assert db.session.get(Tag, b_tag).characters == []  # Bob's tag untouched

    bob.post(f"/characters/{ai}/tags", data={"tags": [b_tag]})
    alice.post(f"/characters/{ai}/tags", data={})  # Alice clears her tags
    with app.app_context():
        assert db.session.get(Tag, a_tag).characters == []
        assert [c.hanzi for c in db.session.get(Tag, b_tag).characters] == ["爱"]


def test_practice_cannot_draw_from_another_users_tag(app, alice, bob):
    alice.post("/tags", data={"name": "Mine"})
    with app.app_context():
        tag_id = Tag.query.one().id
        ai = char_id("爱")
    alice.post(f"/tags/{tag_id}/characters/{ai}/add")

    own = alice.get(f"/practice/read?tags={tag_id}")
    assert "爱".encode() in own.data
    other = bob.get(f"/practice/read?tags={tag_id}")
    assert "爱".encode() not in other.data
    assert b"No characters to practise" in other.data


def test_tag_statistics_use_the_viewers_progress(app, alice, bob):
    alice.post("/tags", data={"name": "Pair"})
    with app.app_context():
        tag_id = Tag.query.one().id
        ai, ba = char_id("爱"), char_id("八")
    alice.post(f"/tags/{tag_id}/characters/{ai}/add")
    alice.post(f"/tags/{tag_id}/characters/{ba}/add")
    mark(alice, ai, is_known="1")
    mark(bob, ba, can_write="1")  # Bob's progress must not leak into Alice's numbers

    with app.app_context():
        tag = db.session.get(Tag, tag_id)
        stats = chars.tag_stats(User.get_by_username("alice"), [tag])[tag_id]
    assert stats == {"total": 2, "known": 1, "writable": 0, "new": 1}

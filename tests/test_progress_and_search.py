from conftest import char_id

from xuehanzi.extensions import db
from xuehanzi.models import CharacterProgress, User
from xuehanzi.services import characters as chars


def alice_user():
    return User.get_by_username("alice")


def test_partial_updates_leave_the_other_flag_alone(app, alice):
    with app.app_context():
        ai = char_id("爱")
    alice.post(f"/characters/{ai}/progress", data={"can_write": "1"})
    alice.post(f"/characters/{ai}/progress", data={"is_known": "1"})
    with app.app_context():
        progress = db.session.get(CharacterProgress, (alice_user().id, ai))
        assert (progress.is_known, progress.can_write) == (True, True)

    alice.post(f"/characters/{ai}/progress", data={"is_known": "0"})
    with app.app_context():
        progress = db.session.get(CharacterProgress, (alice_user().id, ai))
        assert (progress.is_known, progress.can_write) == (False, True)


def test_checkbox_form_with_hidden_fallback(app, alice):
    """The character card sends a hidden 0 before each checkbox."""
    with app.app_context():
        ai = char_id("爱")
    alice.post(
        f"/characters/{ai}/progress",
        data={"can_write": ["0", "1"], "is_known": ["0"]},
    )
    with app.app_context():
        progress = db.session.get(CharacterProgress, (alice_user().id, ai))
        assert (progress.is_known, progress.can_write) == (False, True)


def test_row_is_removed_when_everything_is_unmarked(app, alice):
    with app.app_context():
        ai = char_id("爱")
    alice.post(f"/characters/{ai}/progress", data={"is_known": "1"})
    alice.post(f"/characters/{ai}/progress", data={"is_known": "0"})
    with app.app_context():
        assert CharacterProgress.query.count() == 0


def test_unknown_character_is_ignored(alice):
    assert alice.post("/characters/9999/progress", data={"is_known": "1"}).status_code == 302
    assert alice.get("/characters/9999").status_code == 404


def test_progress_redirects_only_to_local_next(app, alice):
    with app.app_context():
        ai = char_id("爱")
    ok = alice.post(f"/characters/{ai}/progress", data={"is_known": "1", "next": "/known"})
    assert ok.headers["Location"] == "/known"
    evil = alice.post(
        f"/characters/{ai}/progress", data={"is_known": "1", "next": "//evil.example"}
    )
    assert "evil.example" not in evil.headers["Location"]


def test_read_practice_marked_only_uses_known_characters(app, alice):
    with app.app_context():
        ai = char_id("爱")
    alice.post(f"/characters/{ai}/progress", data={"is_known": "1"})
    for _ in range(5):
        assert "爱".encode() in alice.get("/practice/read?marked=1").data
    assert b"No characters to practise" in alice.get("/practice/write?marked=1").data


def test_practice_level_filter(alice):
    for _ in range(5):
        assert "吧".encode() in alice.get("/practice/read?level=2").data


def test_hsk_level_page(alice):
    assert alice.get("/hsk/1").status_code == 200
    assert alice.get("/hsk/7").status_code == 404


def test_search_by_hanzi_toneless_pinyin_and_meaning(app, alice):
    with app.app_context():
        user = alice_user()
        assert [e.character.hanzi for e in chars.search(user, "爱")["hanzi"]] == ["爱"]
        assert [e.character.hanzi for e in chars.search(user, "ai")["pinyin"]] == ["爱"]
        # "bà ba" is stored without spaces/tones, so a spaced query still works.
        assert "爸爸" in [e.character.hanzi for e in chars.search(user, "ba ba")["pinyin"]]
        assert [e.character.hanzi for e in chars.search(user, "eight")["meaning"]] == ["八"]


def test_search_treats_like_wildcards_literally(app, alice):
    with app.app_context():
        user = alice_user()
        assert [e.character.hanzi for e in chars.search(user, "100%")["meaning"]] == ["吧"]
        assert chars.search(user, "%")["meaning"] == [] or all(
            "%" in e.character.meaning for e in chars.search(user, "%")["meaning"]
        )
        assert [e.character.hanzi for e in chars.search(user, "sure_")["meaning"]] == ["吧"]
        assert chars.search(user, "sure?")["meaning"] == []


def test_search_results_show_the_users_flags(app, alice):
    with app.app_context():
        ai = char_id("爱")
    alice.post(f"/characters/{ai}/progress", data={"is_known": "1"})
    with app.app_context():
        entry = chars.search(alice_user(), "爱")["hanzi"][0]
    assert entry.is_known and not entry.can_write
    assert alice.get("/search?q=%E7%88%B1").status_code == 200


def test_bulk_add_report(app, alice):
    alice.post("/tags", data={"name": "Bulk"})
    from xuehanzi.models import Tag

    with app.app_context():
        tag_id = Tag.query.one().id
    first = alice.post(f"/tags/{tag_id}/bulk-add", data={"characters": "爱 八 不存在"})
    assert first.status_code == 200
    second = alice.post(f"/tags/{tag_id}/bulk-add", data={"characters": "爱"})
    assert b"Already in this tag" in second.data
    with app.app_context():
        assert sorted(c.hanzi for c in db.session.get(Tag, tag_id).characters) == ["八", "爱"]


def test_deleting_a_tag_keeps_characters_and_progress(app, alice):
    from xuehanzi.models import Character, Tag

    alice.post("/tags", data={"name": "Temp"})
    with app.app_context():
        tag_id = Tag.query.one().id
        ai = char_id("爱")
    alice.post(f"/tags/{tag_id}/characters/{ai}/add")
    alice.post(f"/characters/{ai}/progress", data={"is_known": "1"})
    alice.post(f"/tags/{tag_id}/delete")
    with app.app_context():
        assert Tag.query.count() == 0
        assert Character.query.count() == 4
        assert CharacterProgress.query.count() == 1

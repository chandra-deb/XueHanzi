import sqlite3

from xuehanzi.extensions import db
from xuehanzi.models import Character, CharacterProgress, Tag, User
from xuehanzi.services.legacy import import_legacy_database
from xuehanzi.services.vocabulary import seed_vocabulary


def test_seed_vocabulary_is_idempotent(app):
    with app.app_context():
        Character.query.delete()
        db.session.commit()

        created, updated = seed_vocabulary()
        assert (created, updated) == (5000, 0)
        assert Character.query.count() == 5000

        assert seed_vocabulary() == (0, 0)
        assert Character.query.count() == 5000
        # trailing ", " from the old importer is gone
        assert not Character.query.filter(Character.meaning.like("%, ")).first()


def _make_legacy_db(path):
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE character (id INTEGER PRIMARY KEY, hsk_serial INTEGER, hsk_level INTEGER,
            character TEXT, pinyin TEXT, no_tone_pinyin TEXT, meaning TEXT,
            can_write BOOLEAN, is_known BOOLEAN);
        CREATE TABLE tag (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE character_tags (tag_id INTEGER, character_id INTEGER);

        -- the old importer created every row twice
        INSERT INTO character VALUES (1, 1, 1, '爱', 'ài', 'ai', 'love', 0, 1);
        INSERT INTO character VALUES (2, 2, 1, '八', 'bā', 'ba', 'eight', 1, 0);
        INSERT INTO character VALUES (3, 1, 1, '爱', 'ài', 'ai', 'love', 0, 0);
        INSERT INTO character VALUES (4, 99, 1, '没有', 'x', 'x', 'missing', 1, 1);
        INSERT INTO tag VALUES (1, 'Hello'), (2, 'Empty');
        INSERT INTO character_tags VALUES (1, 1), (1, 3), (1, 2);
        """
    )
    con.commit()
    con.close()


def test_import_legacy_database(app, make_user, tmp_path):
    make_user("alice")
    legacy_path = tmp_path / "characters.db"
    _make_legacy_db(legacy_path)

    with app.app_context():
        user = User.get_by_username("alice")
        report = import_legacy_database(legacy_path, user)

        assert report.progress_rows == 2
        assert report.tags_created == 2
        assert report.tag_links == 2  # the duplicate legacy row maps to the same character
        assert report.unmapped == ["没有 (old id 4)"]

        progress = {
            p.character.hanzi: (p.is_known, p.can_write)
            for p in CharacterProgress.query.filter_by(user_id=user.id)
        }
        assert progress == {"爱": (True, False), "八": (False, True)}
        hello = Tag.query.filter_by(user_id=user.id, name="Hello").one()
        assert sorted(c.hanzi for c in hello.characters) == ["八", "爱"]

        # Running it again must not duplicate anything.
        again = import_legacy_database(legacy_path, user)
        assert again.tags_created == 0 and again.tag_links == 0
        assert CharacterProgress.query.count() == 2

import pytest

from xuehanzi import create_app
from xuehanzi.config import TestingConfig
from xuehanzi.extensions import db
from xuehanzi.models import Character, User


@pytest.fixture()
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Character(hsk_level=1, hsk_serial=1, hanzi="爱", pinyin="ài", meaning="to love, to like"),
                Character(hsk_level=1, hsk_serial=2, hanzi="八", pinyin="bā", meaning="eight, 8"),
                Character(hsk_level=1, hsk_serial=3, hanzi="爸爸", pinyin="bà ba", meaning="father"),
                Character(hsk_level=2, hsk_serial=151, hanzi="吧", pinyin="ba", meaning="100% sure_thing"),
            ]
        )
        db.session.commit()

    # No app context is held open while a test runs: every request must get its
    # own, exactly like in production (otherwise flask-login's cached user in
    # ``g`` would leak between clients).
    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def make_user(app):
    def _make(username="alice", password="correct-horse"):
        with app.app_context():
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user.id

    return _make


class Client:
    """A test client that remembers its own login (several can run at once)."""

    def __init__(self, app):
        self.http = app.test_client()

    def login(self, username, password="correct-horse"):
        return self.http.post(
            "/login", data={"username": username, "password": password}, follow_redirects=False
        )

    def __getattr__(self, name):
        return getattr(self.http, name)


@pytest.fixture()
def new_client(app):
    return lambda: Client(app)


@pytest.fixture()
def alice(make_user, new_client):
    make_user("alice")
    client = new_client()
    assert client.login("alice").status_code == 302
    return client


@pytest.fixture()
def bob(make_user, new_client):
    make_user("bob")
    client = new_client()
    assert client.login("bob").status_code == 302
    return client


def char_id(hanzi):
    return Character.query.filter_by(hanzi=hanzi).one().id

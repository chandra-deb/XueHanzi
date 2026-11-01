from xuehanzi.models import User


def test_anonymous_users_are_sent_to_login(new_client):
    client = new_client()
    for path in ("/", "/known", "/writable", "/tags", "/search?q=a", "/practice/read"):
        response = client.get(path)
        assert response.status_code == 302, path
        assert "/login" in response.headers["Location"], path


def test_login_page_is_public(new_client):
    assert new_client().get("/login").status_code == 200


def test_register_creates_account_and_signs_in(app, new_client):
    client = new_client()
    response = client.post(
        "/register",
        data={"username": "carol", "password": "longenough1", "confirm_password": "longenough1"},
    )
    assert response.status_code == 302
    assert client.get("/").status_code == 200
    with app.app_context():
        user = User.get_by_username("carol")
        assert user is not None
        assert user.password_hash != "longenough1"


def test_register_rejects_short_password_and_mismatch(new_client):
    client = new_client()
    short = client.post(
        "/register", data={"username": "dave", "password": "short", "confirm_password": "short"}
    )
    assert b"at least 8 characters" in short.data
    mismatch = client.post(
        "/register",
        data={"username": "dave", "password": "longenough1", "confirm_password": "different1"},
    )
    assert b"Passwords do not match" in mismatch.data


def test_usernames_are_unique_ignoring_case(make_user, new_client):
    make_user("Alice")
    response = new_client().post(
        "/register",
        data={"username": "ALICE", "password": "longenough1", "confirm_password": "longenough1"},
    )
    assert b"already taken" in response.data


def test_registration_can_be_disabled(app, new_client):
    app.config["ALLOW_REGISTRATION"] = False
    assert new_client().get("/register").status_code == 404


def test_login_with_wrong_password_fails(make_user, new_client):
    make_user("alice")
    client = new_client()
    response = client.login("alice", "wrong-password")
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data
    assert client.get("/").status_code == 302


def test_login_with_unknown_user_fails_with_same_message(new_client):
    response = new_client().login("nobody")
    assert b"Invalid username or password" in response.data


def test_login_is_case_insensitive_for_username(make_user, new_client):
    make_user("Alice")
    assert new_client().login("alice").status_code == 302


def test_logout(alice):
    assert alice.get("/").status_code == 200
    assert alice.post("/logout").status_code == 302
    assert alice.get("/").status_code == 302


def test_login_next_redirect_only_follows_local_paths(make_user, new_client):
    make_user("alice")
    client = new_client()
    response = client.http.post(
        "/login?next=https://evil.example/",
        data={"username": "alice", "password": "correct-horse"},
    )
    assert response.headers["Location"] == "/"

    client = new_client()
    response = client.http.post(
        "/login?next=/tags",
        data={"username": "alice", "password": "correct-horse"},
    )
    assert response.headers["Location"] == "/tags"

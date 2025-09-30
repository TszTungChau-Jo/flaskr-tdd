import os, pytest, json
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
os.environ["DATABASE_URL"] = f"sqlite:///{BASE_DIR / 'test.db'}"
from project.app import app, db
from project import models

TEST_DB = "test.db"

@pytest.fixture
def client():
    BASE_DIR = Path(__file__).resolve().parent.parent
    app.config["TESTING"] = True
    app.config["DATABASE"] = BASE_DIR.joinpath(TEST_DB)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR.joinpath(TEST_DB)}"

    with app.app_context():
        db.create_all()  # setup
        yield app.test_client()  # tests run here
        db.drop_all()  # teardown


def login(client, username, password):
    """Login helper function"""
    return client.post(
        "/login",
        data=dict(username=username, password=password),
        follow_redirects=True,
    )


def logout(client):
    """Logout helper function"""
    return client.get("/logout", follow_redirects=True)


def test_index(client):
    response = client.get("/", content_type="html/text")
    assert response.status_code == 200


def test_database(client):
    """initial test. ensure that the database exists"""
    tester = Path("test.db").is_file()
    assert tester


def test_empty_db(client):
    """Ensure database is blank"""
    rv = client.get("/")
    # b"..." prefix → means you’re comparing against bytes.
    assert b"No entries yet. Add some!" in rv.data


def test_login_logout(client):
    """Test login and logout using helper functions"""
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"])
    assert b"You were logged in" in rv.data
    rv = logout(client)
    assert b"You were logged out" in rv.data
    rv = login(client, app.config["USERNAME"] + "x", app.config["PASSWORD"])
    assert b"Invalid username" in rv.data
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"] + "x")
    assert b"Invalid password" in rv.data


def test_messages(client):
    """Ensure that user can post messages"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.post(
        "/add",
        data=dict(title="<Hello>", text="<strong>HTML</strong> allowed here"),
        follow_redirects=True,
    )
    assert b"No entries here so far" not in rv.data
    assert b"&lt;Hello&gt;" in rv.data
    assert b"<strong>HTML</strong> allowed here" in rv.data


# def test_delete_message(client):
#     """Ensure the messages are being deleted"""
#     rv = client.get("/delete/1")
#     data = json.loads(rv.data)
#     assert data["status"] == 0
#     login(client, app.config["USERNAME"], app.config["PASSWORD"])
#     rv = client.get("/delete/1")
#     data = json.loads(rv.data)
#     assert data["status"] == 1

def test_delete_requires_login_returns_401_and_json(client):
    # seed a post
    with app.app_context():
        p = models.Post(title="t", text="x")
        db.session.add(p)
        db.session.commit()
        post_id = p.id

    # unauthenticated delete → should be blocked with 401 and JSON message
    rv = client.get(f"/delete/{post_id}")
    assert rv.status_code == 401
    data = rv.get_json()
    assert data["status"] == 0
    assert "Please log in" in data["message"]

    # ensure the post still exists
    with app.app_context():
        assert db.session.get(models.Post, post_id) is not None


def test_delete_authenticated_succeeds(client):
    # seed a post
    with app.app_context():
        p = models.Post(title="to-delete", text="y")
        db.session.add(p)
        db.session.commit()
        post_id = p.id

    # login, then delete
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.get(f"/delete/{post_id}")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["status"] == 1

    # record should be gone
    with app.app_context():
        assert db.session.get(models.Post, post_id) is None


def test_delete_after_logout_is_blocked_again(client):
    # seed a post
    with app.app_context():
        p = models.Post(title="stay", text="z")
        db.session.add(p)
        db.session.commit()
        post_id = p.id

    # login → logout → try delete
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    logout(client)
    rv = client.get(f"/delete/{post_id}")
    assert rv.status_code == 401
    data = rv.get_json()
    assert data["status"] == 0

    # still present
    with app.app_context():
        assert db.session.get(models.Post, post_id) is not None


def test_search_no_query_returns_200(client):
    rv = client.get("/search/")
    assert rv.status_code == 200


def test_search_with_query_returns_200(client):
    rv = client.get("/search/?query=hello")
    assert rv.status_code == 200


def test_search_with_seeded_posts_is_stable(client):
    with app.app_context():
        db.session.add(models.Post(title="First", text="Lorem ipsum"))
        db.session.commit()

    rv = client.get("/search/?query=ipsum")
    assert rv.status_code == 200

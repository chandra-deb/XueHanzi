# XueHanzi

A multi-user HSK (1–6) vocabulary trainer. Every learner has their own account
with their own progress ("known" / "can write") and their own tags, on top of a
shared vocabulary list.

## Quick start

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env            # then set SECRET_KEY (see the file for how)

.venv/bin/flask db upgrade      # create the tables
.venv/bin/flask seed-vocab      # load HSK 1-6 (5000 words)
.venv/bin/flask run --debug     # http://127.0.0.1:5000
```

Open the site and create an account on the **Create an account** page. To
create accounts yourself (for example with `ALLOW_REGISTRATION=false`):

```sh
.venv/bin/flask create-user alice
```

## Moving over the old single-user database

The previous version kept everything in `instance/characters.db`. After
creating your account, copy its progress and tags into it:

```sh
.venv/bin/flask create-user alice
.venv/bin/flask import-legacy instance/characters.db --username alice
```

Characters are matched by HSK level + serial number (falling back to the hanzi
itself), duplicates created by the old importer are merged, and the command is
safe to run more than once. The old file is only read, never modified.

## Configuration

Environment variables (or a `.env` file):

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | – (required unless `--debug`) | Signs session cookies |
| `DATABASE_URL` | `sqlite:///instance/xuehanzi.db` | Any SQLAlchemy URL, e.g. PostgreSQL |
| `ALLOW_REGISTRATION` | `true` | Allow self-service sign-up |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` behind HTTPS |
| `STROKE_ORDER_DIR` | `xuehanzi/static/strokeorderDownloads` | Where stroke order images live |

For production use a real WSGI server, e.g. `gunicorn wsgi:app`, and
`flask db upgrade` on every deploy.

## Stroke order images

Images are not part of the repository. Download them with:

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/download_stroke_order.py 1 2   # levels, default: all
```

Pages simply omit images that haven't been downloaded.

## Development

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

After changing a model: `flask db migrate -m "describe the change"`, review the
generated file in `migrations/versions/`, then `flask db upgrade`.

## Project layout

```
wsgi.py                 entry point (gunicorn / flask)
xuehanzi/
  __init__.py           application factory
  config.py             settings from the environment
  models.py             User, Character, CharacterProgress, Tag
  forms.py              login / registration forms
  cli.py                flask seed-vocab | create-user | import-legacy
  views/                blueprints: auth, main, characters, practice, tags
  services/             user-scoped queries and business logic
  data/                 bundled HSK word lists (JSON)
  templates/, static/
migrations/             Alembic migrations
scripts/                one-off tooling (stroke order downloader)
tests/
```

### How multi-user works

* `Character` (the vocabulary) is shared and read-only.
* `CharacterProgress` stores one row per *(user, character)* with that user's
  `is_known` / `can_write` flags. No row means "new".
* `Tag` rows belong to one user; a tag's character links are therefore private.
* Every query goes through `xuehanzi/services/`, which always takes the
  current user. Other users' tags answer `404`.
* All state-changing actions are `POST` requests protected by CSRF tokens.

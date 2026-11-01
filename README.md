# XueHanzi (学汉字)

**A multi-user web app for learning Chinese vocabulary and handwriting, built around the HSK 1–6 word lists.**

XueHanzi gives every learner a personal account on top of a shared vocabulary of
5,000 HSK words. You decide which characters you can *recognise* and which you
can *write from memory*, group words into your own study lists, and drill
yourself with random-draw practice sessions. Your progress and lists are
private to you.

## Features

### Personal accounts
- Sign up, sign in and sign out; optional "keep me signed in".
- Every user has their own progress and tags. Nobody can see or change anyone else's data.
- Passwords are hashed, all forms are CSRF-protected, and redirects are restricted to the site itself.
- Self-service sign-up can be switched off, with accounts created from the command line instead.

### Browse the HSK vocabulary
- All of HSK 1–6 (5,000 words) with hanzi, pinyin and English meanings.
- Per-level grid view where each word is colour-coded: **new**, **known** or **can write**.
- A detail page per word with its stroke-order diagram and practice sheet (when the images are installed).

### Track what you know
- Two independent flags per word: **Known** (you can recognise/read it) and **Can write** (you can produce it from memory).
- A dashboard with totals, counts and percentages for each HSK level.
- Dedicated pages listing everything you know and everything you can write.

### Practise
- **Recall practice:** see a character, try to remember its pinyin and meaning, reveal the answer, then record "I know it" or "I don't know".
- **Writing practice:** see the pinyin and meaning, write the character on paper, reveal it together with its stroke order, then record whether you could write it.
- Choose what to draw from: a whole HSK level, one or more of your tags, or only the words you have already marked.
- Skip to another random word at any time.

### Organise with tags
- Create your own tags such as "Lesson 3", "Travel" or "Mistakes".
- Add words from search results, from a character's own page, or paste a whole list in bulk and get a report of what was added, what was already there and what wasn't found.
- Each tag shows how many of its words are new, known and writable, grouped into sections on the tag page.
- Practise a single tag or several together.

### Search
- Find words by hanzi, by pinyin typed **without tones** (`ni hao` finds 你好), or by English meaning.
- Results show your own progress, so you can mark or tag a word right from the results.

## Quick start

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env            # then set SECRET_KEY (see the file for how)

.venv/bin/flask db upgrade      # create the tables
.venv/bin/flask seed-vocab      # load HSK 1-6 (5000 words)
.venv/bin/flask run --debug     # http://127.0.0.1:5000
```

Open the site and choose **Create an account**. To create accounts yourself
(for example with `ALLOW_REGISTRATION=false`):

```sh
.venv/bin/flask create-user alice
```

### Stroke order images (optional)

The stroke-order diagrams are not stored in the repository. Download them with:

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/download_stroke_order.py 1 2   # levels, default: all
```

The downloader is resumable. Pages simply leave out images that haven't been downloaded.

## Configuration

Set these as environment variables or in a `.env` file:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | – (required unless `--debug`) | Signs session cookies |
| `DATABASE_URL` | `sqlite:///instance/xuehanzi.db` | Any SQLAlchemy URL, e.g. PostgreSQL |
| `ALLOW_REGISTRATION` | `true` | Allow self-service sign-up |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` when served over HTTPS |
| `STROKE_ORDER_DIR` | `xuehanzi/static/strokeorderDownloads` | Where the stroke-order images live |

For production, use a real WSGI server such as `gunicorn wsgi:app` and run
`flask db upgrade` on every deploy.

## Tech stack

Python · Flask · SQLAlchemy (SQLite by default, PostgreSQL supported) ·
Flask-Login · Flask-WTF · Flask-Migrate (Alembic) · Jinja2 templates · pytest

## How multi-user works

- `Character` (the vocabulary) is shared and read-only.
- `CharacterProgress` stores one row per *(user, character)* with that user's
  `is_known` / `can_write` flags. No row means "new".
- `Tag` rows belong to one user, so a tag's character links are private as well.
- Every query goes through `xuehanzi/services/`, which always takes the current
  user. Another user's tags answer `404`.
- All state-changing actions are `POST` requests protected by CSRF tokens.

## Project layout

```
wsgi.py                 entry point (gunicorn / flask)
xuehanzi/
  __init__.py           application factory
  config.py             settings from the environment
  models.py             User, Character, CharacterProgress, Tag
  forms.py              login / registration forms
  cli.py                flask seed-vocab | create-user
  views/                blueprints: auth, main, characters, practice, tags
  services/             user-scoped queries and business logic
  data/                 bundled HSK word lists (JSON)
  templates/, static/
migrations/             Alembic migrations
scripts/                stroke-order downloader
tests/
```

## Development

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

The test suite covers authentication, per-user isolation of progress and tags,
practice filters, search, bulk tagging and rendering of every page.

After changing a model, run `flask db migrate -m "describe the change"`, review
the generated file in `migrations/versions/`, then `flask db upgrade`.


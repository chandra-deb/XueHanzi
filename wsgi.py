"""Entry point for WSGI servers (``gunicorn wsgi:app``) and ``flask`` commands."""

from xuehanzi import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

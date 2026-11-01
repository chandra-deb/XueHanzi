"""``flask`` sub-commands for administration."""

import click
from flask import current_app
from flask.cli import with_appcontext

from .extensions import db
from .forms import MIN_PASSWORD_LENGTH
from .models import User
from .services import legacy
from .services.vocabulary import seed_vocabulary


@click.command("seed-vocab")
@with_appcontext
def seed_vocab_command():
    """Load (or refresh) the bundled HSK 1-6 vocabulary."""
    created, updated = seed_vocabulary()
    click.echo(f"Vocabulary ready: {created} added, {updated} updated.")


@click.command("create-user")
@click.argument("username")
@click.password_option(help="Password for the new account.")
@with_appcontext
def create_user_command(username, password):
    """Create a user account."""
    username = username.strip()
    if len(username) < 3 or len(username) > 32:
        raise click.ClickException("Username must be 3-32 characters long.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise click.ClickException(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if User.get_by_username(username):
        raise click.ClickException(f'User "{username}" already exists.')

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Created user "{username}".')


@click.command("import-legacy")
@click.argument("database", type=click.Path(exists=True, dir_okay=False))
@click.option("--username", required=True, help="Existing user who receives the data.")
@with_appcontext
def import_legacy_command(database, username):
    """Import progress and tags from the old single-user characters.db."""
    user = User.get_by_username(username)
    if user is None:
        raise click.ClickException(
            f'No user "{username}". Create it first with: flask create-user {username}'
        )

    report = legacy.import_legacy_database(database, user)
    click.echo(
        f"Imported {report.progress_rows} progress rows, "
        f"{report.tags_created} new tags ({report.tags_reused} already existed), "
        f"{report.tag_links} tag links."
    )
    if report.unmapped:
        click.echo(f"{len(report.unmapped)} characters could not be matched:")
        for item in report.unmapped[:20]:
            click.echo(f"  - {item}")


def register_commands(app):
    app.cli.add_command(seed_vocab_command)
    app.cli.add_command(create_user_command)
    app.cli.add_command(import_legacy_command)

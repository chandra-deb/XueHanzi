from flask_login import login_required


def require_login(blueprint):
    """Make every route of ``blueprint`` require a signed-in user."""

    @blueprint.before_request
    @login_required
    def _require_login():
        return None

    return blueprint

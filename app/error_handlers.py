from flask import Blueprint, redirect, render_template, request, url_for

bp = Blueprint("errors", __name__)
MOBILE_TOKENS = ("mobile", "android", "iphone", "ipad", "ipod", "webos", "blackberry")


@bp.app_errorhandler(400)
def bad_request(_error):
    return render_template("errors/400.html"), 400


@bp.app_errorhandler(401)
def unauthorised(_error):
    return render_template("errors/401.html"), 401


@bp.app_errorhandler(403)
def forbidden(_error):
    return render_template("errors/403.html"), 403


@bp.app_errorhandler(404)
def not_found(_error):
    return render_template("errors/404.html"), 404


@bp.app_errorhandler(405)
def method_not_allowed(_error):
    return render_template("errors/405.html"), 405


@bp.app_errorhandler(500)
def internal_server_error(_error):
    return render_template("errors/500.html"), 500


@bp.app_errorhandler(502)
def bad_gateway(_error):
    return render_template("errors/502.html"), 502


@bp.app_errorhandler(503)
def service_unavailable(_error):
    return render_template("errors/503.html"), 503


@bp.app_errorhandler(504)
def gateway_timeout(_error):
    return render_template("errors/504.html"), 504


@bp.before_app_request
def block_mobile_devices():
    user_agent = (request.headers.get("User-Agent") or "").lower()
    is_mobile = any(token in user_agent for token in MOBILE_TOKENS)
    if not is_mobile:
        return None

    if request.endpoint in ("static", "main.mobile_blocked"):
        return None

    return redirect(url_for("main.mobile_blocked"))

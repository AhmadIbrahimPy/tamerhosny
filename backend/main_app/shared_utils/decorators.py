from functools import wraps

from django.shortcuts import redirect


def dashboard_required(view_func):
    """Like @login_required(login_url='dashboard_app:login'), but also
    checks the session's role - plain @login_required only checks
    is_authenticated, so any signed-in session (including a public site
    signup, which has no business here) could reach every dashboard page
    once logged in anywhere, since nothing re-checked role past the
    login view itself.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from backend.main_app.models import UserAccount

        if not request.user.is_authenticated or request.user.role not in UserAccount.DASHBOARD_ROLES:
            return redirect('dashboard_app:login')
        return view_func(request, *args, **kwargs)

    return wrapper

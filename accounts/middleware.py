from django.shortcuts import redirect


class TwoFactorReenrollmentMiddleware:
    """A recovery-code login may only continue to new authenticator enrollment."""
    allowed_prefixes = ("/accounts/two-factor/", "/accounts/logout/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.session.get("two_factor_reenroll_required") and not request.path.startswith(self.allowed_prefixes):
            return redirect("two_factor_setup")
        return self.get_response(request)

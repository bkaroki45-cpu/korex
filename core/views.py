from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/home.html")


def robots_txt(request):
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    return HttpResponse(
        f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n",
        content_type="text/plain",
    )


def service_worker(request):
    response = render(request, "service-worker.js", content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def csrf_failure(request, reason=""):
    """Refresh an expired form token instead of exposing a raw 403 page."""
    messages.error(request, "Your security session expired. Please try again using the refreshed form.")
    referrer = request.META.get("HTTP_REFERER", "")
    if referrer and url_has_allowed_host_and_scheme(referrer, {request.get_host()}, require_https=request.is_secure()):
        return redirect(referrer)
    return redirect("login")

from django.http import HttpResponse
from django.shortcuts import redirect, render


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
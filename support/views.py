from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import SupportRequestForm
from .models import SupportRequest
from .security import client_fingerprint

RATE_WINDOW = timedelta(minutes=15)
MAX_REQUESTS_PER_WINDOW = 3


@require_http_methods(["GET", "POST"])
def support_request(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {"name": request.user.get_full_name() or request.user.username, "email": request.user.email}
    form = SupportRequestForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        fingerprint = client_fingerprint(request)
        recent_count = SupportRequest.objects.filter(
            source_ip_hash=fingerprint,
            created_at__gte=timezone.now() - RATE_WINDOW,
        ).count()
        if recent_count >= MAX_REQUESTS_PER_WINDOW:
            form.add_error(None, "Too many support requests were sent from this connection. Please wait 15 minutes and try again.")
        else:
            item = form.save(commit=False)
            item.source_ip_hash = fingerprint
            if request.user.is_authenticated:
                item.user = request.user
            item.save()
            messages.success(request, "Your support message has been sent. Our team will respond as soon as possible.")
            return redirect("support:request")
    return render(request, "support/request.html", {"form": form})
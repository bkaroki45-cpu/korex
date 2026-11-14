from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import SupportReplyForm, SupportRequestForm
from .models import SupportMessage, SupportRequest
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
    tickets = SupportRequest.objects.filter(user=request.user) if request.user.is_authenticated else SupportRequest.objects.none()
    return render(request, "support/portal.html", {"form": form, "requests": tickets})


@login_required
@require_http_methods(["GET", "POST"])
def support_chat(request, request_id):
    item = get_object_or_404(SupportRequest, pk=request_id, user=request.user)
    SupportMessage.objects.filter(request=item, is_staff_reply=True, read_at__isnull=True).update(read_at=timezone.now())
    form = SupportReplyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reply = form.save(commit=False)
        reply.request, reply.sender, reply.is_staff_reply = item, request.user, False
        reply.save()
        if item.status == SupportRequest.Status.RESOLVED:
            item.status = SupportRequest.Status.OPEN
            item.save(update_fields=["status", "updated_at"])
        return redirect("support:chat", request_id=item.id)
    return render(request, "support/chat_modern.html", {"ticket": item, "form": form})

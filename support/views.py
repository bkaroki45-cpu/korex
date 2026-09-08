from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SupportRequestForm


@require_http_methods(["GET", "POST"])
def support_request(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {"name": request.user.get_full_name() or request.user.username, "email": request.user.email}
    form = SupportRequestForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if request.user.is_authenticated:
            item.user = request.user
        item.save()
        messages.success(request, "Your support message has been sent. Our team will respond as soon as possible.")
        return redirect("support:request")
    return render(request, "support/request.html", {"form": form})

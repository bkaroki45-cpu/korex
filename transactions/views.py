from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Transaction


@login_required
def history(request):
    selected_type = request.GET.get("type", "")
    valid_types = {value for value, _ in Transaction.TransactionType.choices}
    transactions = Transaction.objects.filter(user=request.user)
    if selected_type in valid_types:
        transactions = transactions.filter(transaction_type=selected_type)
    else:
        selected_type = ""

    page_obj = Paginator(transactions, 25).get_page(request.GET.get("page"))
    return render(request, "transactions/history.html", {
        "page_obj": page_obj,
        "selected_type": selected_type,
        "transaction_types": Transaction.TransactionType.choices,
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import get_market_assets, get_market_news, get_market_overview


@login_required
def markets(request):
    assets = get_market_assets()
    return render(request, "markets/markets.html", {"assets": assets, "overview": get_market_overview(), "news": get_market_news()})

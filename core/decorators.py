# decorators.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from functools import wraps


def buyer_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in as a buyer to access this page.")
            return redirect('user-login')  # or your login URL
        if request.user.is_company:
            messages.error(request, "Only buyers can access this page.")
            return redirect('buyer_bid_history')  # or a 403 page
        return function(request, *args, **kwargs)

    return wrap


def company_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in as a company to access this page.")
            return redirect('user-login')
        if not request.user.is_company:
            messages.error(request, "Only companies can access this page.")
            return redirect('company_dashboard')
        return function(request, *args, **kwargs)

    return wrap

# middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class EmailVerificationRequiredMiddleware:
    """
    Middleware that redirects users to the verify_account page if they are logged in but not verified.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_verified:
            verify_url = reverse('verify_account')
            # Allow the user to access 'verify_account' or logout, but no other protected pages
            if not (request.path.startswith(verify_url) or request.path.startswith('/logout')):
                return redirect('verify_account')
        return self.get_response(request)
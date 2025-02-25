from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth import login, authenticate, logout
from django.core.mail import send_mail

from users.forms import BuyerRegistrationForm, CompanyRegistrationForm, VerifyAccountForm, LoginForm
from users.models import CompanyProfile
from .models import CustomUser, BuyerProfile, AuctionListing, Category
from .utils import generate_otp_code, send_otp_email
from .decorators import buyer_required, company_required
from .forms import AuctionForm


# Create your views here.

def buyer_register_view(request):
    if request.method == 'POST':
        form = BuyerRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Extract user fields
                email = form.cleaned_data['email']
                phone = form.cleaned_data['phone_number']
                fname = form.cleaned_data['first_name']
                lname = form.cleaned_data['last_name']
                password = form.cleaned_data['password1']

                # Create the user with is_company=False
                user = CustomUser.objects.create_user(
                    email=email,
                    phone_number=phone,
                    first_name=fname,
                    last_name=lname,
                    password=password,
                    is_company=False
                )
                # Set user as unverified and generate OTP
                user.is_verified = False
                user.verification_code = generate_otp_code()
                user.save()

                # Create the BuyerProfile
                BuyerProfile.objects.create(
                    user=user,
                    address=form.cleaned_data['address'],
                    city=form.cleaned_data['city'],
                    country=form.cleaned_data['country'],
                    date_of_birth=form.cleaned_data['date_of_birth'],
                    gender=form.cleaned_data['gender'],
                )

                send_otp_email(user.verification_code, user.email, user.full_name)

                # Log them in immediately (they'll be forced to verify)
                login(request, user)

            return redirect('verify_account')  # Once registered, go to OTP verify
    else:
        form = BuyerRegistrationForm()

    return render(request, 'bidder/buyer_register.html', {'form': form})


def company_register_view(request):
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                # Extract user fields
                email = form.cleaned_data['email']
                phone = form.cleaned_data['phone_number']
                fname = form.cleaned_data['first_name']
                lname = form.cleaned_data['last_name']
                password = form.cleaned_data['password1']

                # Create the user with is_company=True
                user = CustomUser.objects.create_user(
                    email=email,
                    phone_number=phone,
                    first_name=fname,
                    last_name=lname,
                    password=password,
                    is_company=True
                )
                # Set user as unverified and generate OTP
                user.is_verified = False
                user.verification_code = generate_otp_code()
                user.is_company = True
                user.save()

                # Create the CompanyProfile
                CompanyProfile.objects.create(
                    user=user,
                    company_name=form.cleaned_data['company_name'],
                    website=form.cleaned_data['website'],
                    description=form.cleaned_data['description'],
                    address=form.cleaned_data['address'],
                    city=form.cleaned_data['city'],
                    country=form.cleaned_data['country'],
                    registration_documents=form.cleaned_data['registration_documents'] or None,
                    logo=form.cleaned_data['logo'] or None,
                )

                # Send email with OTP
                send_otp_email(user.verification_code, user.email, user.full_name)

                # Log them in
                login(request, user)

            return redirect('verify_account')  # Once registered, go to OTP verify
    else:
        form = CompanyRegistrationForm()

    return render(request, 'company/company_register.html', {'form': form})


@login_required
def verify_account_view(request):
    """
    If user.is_verified == False, they must provide the correct OTP.
    """
    if request.user.is_verified:
        # Already verified, no need to be here
        if request.user.is_company:
            return redirect('company_dashboard')
        else:
            return redirect('buyer_bid_history')

    if request.method == 'POST':
        form = VerifyAccountForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['verification_code']
            # Compare to the logged-in user's verification_code
            if code == request.user.verification_code:
                request.user.is_verified = True
                request.user.save()
                if request.user.is_company:
                    return redirect('company_dashboard')
                else:
                    return redirect('buyer_bid_history')

            else:
                form.add_error('verification_code', 'Invalid verification code.')
    else:
        form = VerifyAccountForm()

    return render(request, 'bidder/verify_account.html', {'form': form})



def user_login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # 'username' param = email in your custom user model
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                # If not verified, you can redirect them to verify:
                if not user.is_verified:
                    return redirect('verify_account')
                else:
                    if user.is_company:
                        return redirect('company_dashboard')
                    else:
                        return redirect('buyer_bid_history')
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, 'company/login.html', {'form': form})


def user_logout_view(request):
    """
    Logs out the current user and redirects them to the login page
    (or wherever you want).
    """
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('user-login')


@buyer_required
def buyer_dashboard_view(request):
    context = {}
    return render(request, 'bidder/index.html', context)


@buyer_required
def buyer_bid_history_view(request):
    context = {}
    return render(request, 'bidder/bid_history.html', context)


@buyer_required
def buyer_listings(request):
    # 1) Get search query and category filter from GET parameters
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')


    # 2) Base queryset: only active listings, newest first
    auctions = AuctionListing.objects.filter(is_active=True).order_by('-created_at')

    # 3) If a category filter is selected, filter by category
    if category_id:
        auctions = auctions.filter(category_id=category_id)

    # 4) If there's a search query, filter by title/description/location
    if search_query:
        auctions = auctions.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    # 5) Paginate (e.g. 6 items per page)
    paginator = Paginator(auctions, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 6) Get all categories (for dropdown)
    categories = Category.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,  # so we can build a category dropdown
        'search_query': search_query,
        'selected_category': category_id,  # to keep track of the selected cat in the form
    }
    return render(request, 'bidder/listings.html', context)


@buyer_required
def buyer_watchlist(request):
    context = {}
    return render(request, 'bidder/watchlist.html', context)


@buyer_required
def buyer_notification(request):
    context = {}
    return render(request, 'bidder/notifications.html', context)


@company_required
def company_dashboard_view(request):
    context = {}
    return render(request, 'company/index.html', context)


@company_required
def company_categories_view(request):
    context = {}
    return render(request, 'company/categories.html', context)



@company_required
def company_auctions_view(request):
    company_profile = request.user.company_profile
    auctions = AuctionListing.objects.filter(company=company_profile).order_by('-created_at')

    if request.method == 'POST':
        form = AuctionForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                category = form.cleaned_data.get('category')  # may be None if not required
                title = form.cleaned_data['title']
                description = form.cleaned_data.get('description', '')
                condition = form.cleaned_data.get('condition', '')
                location = form.cleaned_data.get('location', '')
                start_price = form.cleaned_data['starting_price']
                auction_start = form.cleaned_data['auction_start']
                auction_end = form.cleaned_data['auction_end']
                cover_image = form.cleaned_data.get('cover_image')

                new_auction = AuctionListing.objects.create(
                    company=company_profile,
                    category=category,
                    title=title,
                    description=description,
                    condition=condition,
                    location=location,
                    starting_price=start_price,
                    current_price=start_price,
                    auction_start=auction_start,
                    auction_end=auction_end,
                    cover_image=cover_image
                )

            messages.success(request, "Auction created successfully.")
            return redirect('company_auctions')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AuctionForm()

    context = {
        'form': form,
        'auctions': auctions,
    }
    return render(request, 'company/my_auctions.html', context)


@company_required
def company_sales_view(request):
    context = {}
    return render(request, 'company/sales.html', context)

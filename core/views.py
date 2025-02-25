from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth import login, authenticate, logout
from django.core.mail import send_mail

from users.forms import BuyerRegistrationForm, CompanyRegistrationForm, VerifyAccountForm, LoginForm
from users.models import CompanyProfile
from .models import CustomUser, BuyerProfile, AuctionListing, Category, Bid
from .utils import generate_otp_code, send_otp_email, send_outbid_email_html, send_winner_email_html
from .decorators import buyer_required, company_required
from .forms import AuctionForm, BidForm
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


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
def buyer_auction_detail_view(request, auction_id):
    # Example: enforce user is buyer with a decorator or logic
    buyer_profile = BuyerProfile.objects.get(user=request.user)

    auction = get_object_or_404(AuctionListing, pk=auction_id)
    recent_bids = Bid.objects.filter(auction_listing=auction).order_by('-created_at')[:10]

    # If user POSTs a new bid
    if request.method == 'POST':
        form = BidForm(request.POST)
        if form.is_valid():
            bid_amount = form.cleaned_data['bid_amount']

            if not auction.is_active:
                messages.error(request, "This auction has ended.")
                return redirect('buyer-auction-detail', auction_id=auction.id)

            min_required = auction.current_price + auction.bid_increment
            if bid_amount < min_required:
                messages.error(request, f"Your bid must be at least ${min_required}.")
                return redirect('buyer-auction-detail', auction_id=auction.id)

            # Create the new bid
            new_bid = Bid.objects.create(
                user=buyer_profile,
                auction_listing=auction,
                bid_amount=bid_amount
            )
            auction.current_price = bid_amount
            auction.save()

            # Outbid logic: find the previous highest (the second-highest now)
            top_bids = Bid.objects.filter(auction_listing=auction).order_by('-bid_amount')[:2]
            if len(top_bids) == 2:
                previous_highest = top_bids[1]
                if not previous_highest:
                    previous_highest.is_outbid_notification_sent = True
                    previous_highest.save()
                    # Email them
                    outbid_user_email = previous_highest.user.user.email
                    full_name = f"{previous_highest.user.user.first_name} {previous_highest.user.user.last_name}"
                    send_outbid_email_html(
                        to_email=outbid_user_email,
                        auction_title=auction.title,
                        new_bid_amount=bid_amount,
                        fullname=full_name
                    )

            # Broadcast to WebSocket
            channel_layer = get_channel_layer()
            group_name = f"auction_{auction.id}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "new.bid",
                    "bid_amount": str(bid_amount),
                    "user_email": request.user.email,
                }
            )

            messages.success(request, "Your bid has been placed successfully.")
            return redirect('buyer-auction-detail', auction_id=auction.id)
    else:
        form = BidForm()

    context = {
        'auction': auction,
        'recent_bids': recent_bids,
        'form': form,
    }
    return render(request, 'bidder/auction_detail.html', context)


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


def company_auction_detail_view(request, auction_id):
    # Ensure this is the company's listing
    auction = get_object_or_404(
        AuctionListing,
        pk=auction_id,
        company=CompanyProfile.objects.get(user=request.user),
    )
    recent_bids = Bid.objects.filter(auction_listing=auction).order_by('-created_at')[:10]
    total_bids = auction.bids.count()
    unique_bidders_count = auction.bids.values('user').distinct().count()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'end_auction':
            if auction.is_active:
                auction.is_active = False
                auction.save()

                # Highest bid
                highest_bid = auction.bids.order_by('-bid_amount').first()
                if highest_bid:
                    # Mark the winner
                    auction.winner = highest_bid.user.user  # BuyerProfile -> .user
                    auction.save()

                    # Send winner email
                    full_name = f"{highest_bid.user.user.first_name} {highest_bid.user.user.last_name}"
                    send_winner_email_html(
                        to_email=highest_bid.user.user.email,
                        auction_title=auction.title,
                        fullname=full_name
                    )

                messages.success(request, f"Auction '{auction.title}' has been ended.")
            else:
                messages.info(request, "This auction is already inactive.")
            return redirect('company-auction-detail', auction_id=auction.id)

    context = {
        'auction': auction,
        'recent_bids': recent_bids,
        'total_bids': total_bids,
        'unique_bidders_count': unique_bidders_count,
    }
    return render(request, 'company/auction_detail.html', context)


@company_required
def company_sales_view(request):
    context = {}
    return render(request, 'company/sales.html', context)

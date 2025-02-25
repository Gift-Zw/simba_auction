from django.core.exceptions import ValidationError
from django.db import models

from users.models import TimeStampedModel, CustomUser, CompanyProfile, BuyerProfile
from django.utils import timezone


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)

    def __str__(self):
        return self.name


class AuctionListing(TimeStampedModel):
    """
    Auction listings created by approved companies.
    Contains comprehensive details such as shipping, location, and item condition.
    """
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='auction_listings')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='auction_listings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    condition = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    starting_price = models.DecimalField(max_digits=12, decimal_places=2)
    current_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bid_increment = models.DecimalField(max_digits=12, decimal_places=2, default=1.00)
    auction_start = models.DateTimeField(default=timezone.now)
    auction_end = models.DateTimeField()
    cover_image = models.ImageField(upload_to='cover_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    winner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='won_auctions')

    def __str__(self):
        return self.title

    def check_expiration(self):
        """
        Expires the auction if the current time is past the auction end.
        Intended to be called periodically (e.g., via a scheduled task).
        """
        if timezone.now() >= self.auction_end and self.is_active:
            self.is_active = False
            self.save()
            # TODO: Determine the highest bid, set the winner, and trigger notifications.


class Picture(TimeStampedModel):
    """
    Stores images for auction listings.
    """
    auction_listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE, related_name='pictures')
    image = models.ImageField(upload_to='auction_images/', blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Picture for {self.auction_listing.title}"


class Comment(TimeStampedModel):
    """
    Comments posted by users on auction listings.
    """
    user = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='comments')
    auction_listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()

    def __str__(self):
        return f"Comment by {self.user.email}"


class Bid(TimeStampedModel):
    """
    Represents a bid on an auction listing.
    Each bid must be higher than the current highest bid or the starting price.
    """
    user = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='bids')
    auction_listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE, related_name='bids')
    bid_amount = models.DecimalField(max_digits=12, decimal_places=2)


    def __str__(self):
        return f"{self.user.email} bid {self.bid_amount} on {self.auction_listing.title}"

    def clean(self):
        highest_bid = self.auction_listing.bids.order_by('-bid_amount').first()
        if highest_bid and self.bid_amount <= highest_bid.bid_amount:
            raise ValidationError("Your bid must be higher than the current highest bid.")
        if self.bid_amount < self.auction_listing.starting_price:
            raise ValidationError("Your bid must be at least the starting price.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Validate bid before saving.
        super().save(*args, **kwargs)
        # Update the auction listing's current price if this bid is the highest.
        if self.bid_amount > self.auction_listing.current_price:
            self.auction_listing.current_price = self.bid_amount
            self.auction_listing.save()
            # TODO: Notify the previous highest bidder (via email and Notification).


class Payment(TimeStampedModel):
    """
    Records payment transactions for winning bids.
    """
    auction_listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE, related_name='payments')
    bidder = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)  # e.g., PayPal, Stripe.
    currency = models.CharField(max_length=10, default='USD')
    payment_date = models.DateTimeField(default=timezone.now)
    successful = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.amount}"


class Watchlist(models.Model):
    user = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name="watchlist_items")
    auction_listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE, related_name="watchlisted_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'auction_listing')

    def __str__(self):
        return f"{self.user.username} - {self.auction_listing.name}"


class Notification(TimeStampedModel):
    """
    Stores notifications for users (e.g., outbid alerts, auction updates).
    """
    user = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'outbid', 'auction_ended'

    def __str__(self):
        return f"Notification for {self.user.email} at {self.created_at}"

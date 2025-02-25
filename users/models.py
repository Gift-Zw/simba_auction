from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils import timezone


# ------------------------------------------------------------------------------
# Common abstract model to include created and updated timestamps.
# ------------------------------------------------------------------------------
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True



class CustomUserManager(BaseUserManager):
    def create_user(self, email, phone_number, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required")
        if not phone_number:
            raise ValueError("A phone number is required")
        if not first_name or not last_name:
            raise ValueError("Both first and last names are required")
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        # TODO: Trigger sending of email verification using user.verification_code
        return user

    def create_superuser(self, email, phone_number, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, phone_number, first_name, last_name, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    # Verification fields
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    # Account type flags: True if the user is registering as a company.
    is_company = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number', 'first_name', 'last_name']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


# ------------------------------------------------------------------------------
# Profile for auction companies.
# ------------------------------------------------------------------------------
class CompanyProfile(TimeStampedModel):
    """
    Profile for auction companies.
    Companies are linked one-to-one with a CustomUser account.
    They must submit required documents and be approved before creating auctions.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='company_profile')
    company_name = models.CharField(max_length=200)
    website = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    registration_documents = models.FileField(upload_to='company_documents/')
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return self.company_name


# ------------------------------------------------------------------------------
# Profile for buyers.
# ------------------------------------------------------------------------------
class BuyerProfile(TimeStampedModel):
    """
    Profile for buyers.
    Buyers are linked one-to-one with a CustomUser account.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='buyer_profile')
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Buyer: {self.user.first_name} {self.user.last_name}"



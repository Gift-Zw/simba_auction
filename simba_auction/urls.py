"""
URL configuration for simba_auction project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('buyer/dashboard/', views.buyer_dashboard_view, name='buyer_dashboard'),
    path('buyer/bid-history/', views.buyer_bid_history_view, name='buyer_bid_history'),
    path('buyer/listings/', views.buyer_listings, name='buyer_listings'),
    path('buyer/watchlist/', views.buyer_watchlist, name='buyer_watchlist'),
    path('buyer/notifications/', views.buyer_notification, name='buyer_notifications'),
    # Company views
    path('company/dashboard/', views.company_dashboard_view, name='company_dashboard'),
    path('company/categories/', views.company_categories_view, name='company_categories'),
    path('company/auctions/', views.company_auctions_view, name='company_auctions'),
    path('company/sales/', views.company_sales_view, name='company_sales'),
    path('register/buyer/', views.buyer_register_view, name='buyer_register'),
    path('register/company/', views.company_register_view, name='company_register'),
    path('verify-account/', views.verify_account_view, name='verify_account'),
    path('login/', views.user_login_view, name='user-login'),
    path('logout/', views.user_logout_view, name='user-logout'),
    path('auction/<int:auction_id>/', views.buyer_auction_detail_view, name='buyer-auction-detail'),

    # Company detail
    path('company/auction/<int:auction_id>/', views.company_auction_detail_view, name='company-auction-detail'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

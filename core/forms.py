# forms.py
from django import forms
from .models import Category


class AuctionForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False,
                                      widget=forms.Select(attrs={'class': 'form-control'}))
    title = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control'}))
    condition = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    location = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    starting_price = forms.DecimalField(max_digits=12, decimal_places=2,
                                        widget=forms.NumberInput(attrs={'class': 'form-control'}))
    auction_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    auction_end = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    cover_image = forms.ImageField(required=True, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))


class BidForm(forms.Form):
    bid_amount = forms.DecimalField(max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'}))
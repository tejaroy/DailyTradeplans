# trades/filters.py
import django_filters
from django import forms
from .models import TradeMaster

class TradePlanFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='exact',
        label='Date',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    stock_name = django_filters.CharFilter(
        field_name='stock_name', lookup_expr='icontains', label='Ticker'
    )
    profit_or_loss = django_filters.ChoiceFilter(
        field_name='profit_or_loss',
        choices=[('Profit', 'Profit'), ('Loss', 'Loss')],
        label='P/L'
    )

    class Meta:
        model = TradeMaster
        fields = ['date', 'stock_name', 'profit_or_loss']

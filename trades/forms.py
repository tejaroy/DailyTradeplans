# trades/forms.py
from django import forms
from django.forms import ModelChoiceField, modelformset_factory
from .models import TradeMaster, TradeProfitLoss, TradeTransaction

# ----- Profit/Loss formset -----
class TradeResultForm(forms.ModelForm):
    class Meta:
        model = TradeProfitLoss
        fields = ["profit_or_loss", "profit_amount", "loss_amount"]
        widgets = {
            "profit_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "loss_amount":   forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }
    def clean(self):
        cleaned = super().clean()
        pol = cleaned.get("profit_or_loss")
        pa  = cleaned.get("profit_amount")
        la  = cleaned.get("loss_amount")
        if pol == "Profit":
            if pa in (None, ""):
                self.add_error("profit_amount", "Required when P/L is Profit.")
            cleaned["loss_amount"] = None
        elif pol == "Loss":
            if la in (None, ""):
                self.add_error("loss_amount", "Required when P/L is Loss.")
            cleaned["profit_amount"] = None
        else:
            cleaned["profit_amount"] = None
            cleaned["loss_amount"] = None
        return cleaned

TradeProfitLossFormSet = modelformset_factory(
    TradeProfitLoss,
    form=TradeResultForm,
    fields=("profit_or_loss", "profit_amount", "loss_amount"),
    extra=0,
    can_delete=False,
)

class TradeProfitLossForm(forms.ModelForm):
    class Meta:
        model = TradeProfitLoss
        fields = ['profit_or_loss','profit_amount','loss_amount']
        widgets = {
            'profit_amount': forms.NumberInput(attrs={'step':'0.01','min':'0'}),
            'loss_amount':   forms.NumberInput(attrs={'step':'0.01','min':'0'}),
        }
    def clean(self):
        cleaned = super().clean()
        pol = cleaned.get('profit_or_loss'); pa = cleaned.get('profit_amount'); la = cleaned.get('loss_amount')
        if pol == 'Profit':
            if pa in (None,''): self.add_error('profit_amount','Required when P/L is Profit.')
            cleaned['loss_amount'] = None
        elif pol == 'Loss':
            if la in (None,''): self.add_error('loss_amount','Required when P/L is Loss.')
            cleaned['profit_amount'] = None
        else:
            cleaned['profit_amount'] = None; cleaned['loss_amount'] = None
        return cleaned

# ----- Trade News formset -----
class TradeNewsForm(forms.ModelForm):
    class Meta:
        model = TradeMaster
        fields = ['news_catalyst_summary']

TradeNewsFormSet = modelformset_factory(
    TradeMaster, form=TradeNewsForm, extra=0, can_delete=False
)

# ----- Transactions -----
class TradeChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.stock_name} — {obj.option_strike_price_expiry}"  # custom labels [8]

class TradeTransactionForm(forms.ModelForm):
    trade = TradeChoiceField(queryset=TradeMaster.objects.none())  # queryset set in view per request [1]
    class Meta:
        model = TradeTransaction
        fields = ['buy_price', 'sell_price', 'quantity']
        widgets = {
            'buy_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'sell_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'quantity':  forms.NumberInput(attrs={'min': '1'}),
        }

class TradeTransactionFormPost(forms.ModelForm):
    trade = TradeChoiceField(queryset=TradeMaster.objects.none())  # queryset set in view per request [1]
    class Meta:
        model = TradeTransaction
        fields = ['trade','buy_price', 'sell_price', 'quantity']
        widgets = {
            'buy_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'sell_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'quantity':  forms.NumberInput(attrs={'min': '1'}),
        }

TradeTransactionFormSet = modelformset_factory(
    TradeTransaction,
    form=TradeTransactionForm,  # ensure formset uses the custom form [22]
    extra=0,
    can_delete=False,
)

TradeTransactionFormSetPost = modelformset_factory(
    TradeTransaction,
    form=TradeTransactionFormPost,  # ensure formset uses the custom form [22]
    extra=0,
    can_delete=False,
)

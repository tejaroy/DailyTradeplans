from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db import models
from django.db.models import Q

class TradeMaster(models.Model):
    stock_name = models.CharField(max_length=100)
    option_strike_price_expiry = models.CharField(max_length=100)
    option_buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    intraday_exit_price_target = models.DecimalField(max_digits=10, decimal_places=2)
    stop_loss_price = models.DecimalField(max_digits=10, decimal_places=2)
    support_level = models.CharField(max_length=100)
    resistance_level = models.CharField(max_length=100)
    capital_required = models.DecimalField(max_digits=12, decimal_places=2)
    max_loss_if_stop_loss_hits = models.DecimalField(max_digits=10, decimal_places=2)
    max_profit_if_target_hits = models.DecimalField(max_digits=10, decimal_places=2)
    news_catalyst_summary = models.TextField()
    created_at = models.DateField(auto_now_add=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'stock_name',
                    'option_strike_price_expiry',
                    'option_buy_price',
                    'intraday_exit_price_target',
                    'stop_loss_price',
                    'support_level',
                    'resistance_level',
                    'capital_required',
                    'news_catalyst_summary',
                ],
                name='uniq_trademaster_all_fields_except_user_status'
            ),
        ]
    
    def __str__(self):
        return self.stock_name


def tm_choices_today():
    # return a Q or dict; evaluated at form/field construction time
    return {'created_at': timezone.localdate()}

class TradeTransaction(models.Model):
    trade = models.ForeignKey(
        TradeMaster,
        on_delete=models.CASCADE,
        limit_choices_to=tm_choices_today,  # named callable, not lambda
    )
    buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    sell_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    is_ai_correct = models.BooleanField(default=False)
    profit_or_loss = models.CharField(
        max_length=10,
        choices=[('Profit', 'Profit'), ('Loss', 'Loss')]
    )
    profit_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    loss_amount   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tpl_created')  # [2]
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='tpl_updated')  # [2]
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)      



class TradeProfitLoss(models.Model):
    trade = models.ForeignKey('TradeMaster', on_delete=models.CASCADE, related_name='pls')  # per-user rows [3]
    profit_or_loss = models.CharField(max_length=10, choices=[('Profit','Profit'),('Loss','Loss')], blank=True, null=True)  # [2]
    profit_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # [2]
    loss_amount   = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # [2]
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ttpl_created')  # [2]
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ttpl_updated')  # [2]
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)      

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['trade','created_by'], name='uniq_tpl_trade_user'),  # [4]
            # Keep amounts consistent with P/L selection
            models.CheckConstraint(
                name='tpl_valid_profit_loss_amounts',
                check=(
                    (Q(profit_or_loss='Profit') & Q(profit_amount__isnull=False) & Q(loss_amount__isnull=True)) |
                    (Q(profit_or_loss='Loss')   & Q(loss_amount__isnull=False)   & Q(profit_amount__isnull=True)) |
                    (Q(profit_or_loss__isnull=True) & Q(profit_amount__isnull=True) & Q(loss_amount__isnull=True)) |
                    (Q(profit_or_loss='') & Q(profit_amount__isnull=True) & Q(loss_amount__isnull=True))
                )
            ),
        ]


class AccountSummary(TradeProfitLoss):
    class Meta:
        proxy = True
        verbose_name = "Account summary"
        verbose_name_plural = "Account summary"

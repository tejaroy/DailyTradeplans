# trades/signals.py
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F, Sum, ExpressionWrapper, DecimalField

from .models import TradeTransaction, TradeProfitLoss

SCALE = Decimal('100')  # multiply difference by 100 per requirement

def _quantize2(v: Decimal) -> Decimal:
    return (v or Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

@receiver(post_save, sender=TradeTransaction)
def propagate_tpl(sender, instance: TradeTransaction, created, **kwargs):
    # Recompute NET across all TX rows for this trade+user after commit
    def _upsert():
        expr = ExpressionWrapper(
            (F('sell_price') - F('buy_price')) * SCALE,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )  # (sell - buy) * 100 in the DB [1][4]

        agg = (TradeTransaction.objects
               .filter(trade=instance.trade, created_by=instance.created_by)
               .aggregate(net=Sum(expr)))  # net sum across rows [4]

        net = _quantize2(agg['net'] or Decimal('0'))  # 2dp rounding [5]
        if net >= 0:
            pol, profit_amt, loss_amt = 'Profit', net, None
        else:
            pol, profit_amt, loss_amt = 'Loss', None, (-net)  # absolute loss [21]

        TradeProfitLoss.objects.update_or_create(
            trade=instance.trade,
            created_by=instance.created_by,
            defaults={
                'profit_or_loss': pol,
                'profit_amount': profit_amt,
                'loss_amount': loss_amt,
                'updated_by': instance.updated_by or instance.created_by,
            },
        )  # single per-(trade,user) row reflects the net [23]

    transaction.on_commit(_upsert)  # run only after TX is durable [22]

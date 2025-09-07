# trades/views.py
from django.views.generic import ListView
from django.db.models import F, ExpressionWrapper, DecimalField
from django.utils import timezone
from .models import TradeMaster, TradeTransaction
from .filter import TradePlanFilter
from django.http import JsonResponse
from datetime import datetime
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

class DailyPlanView(ListView):
    model = TradeMaster
    template_name = 'plans/daily_plan.html'
    context_object_name = 'rows'
    paginate_by = 50  # optional pagination

    def get_queryset(self):
        # Base queryset
        qs = TradeMaster.objects.all()

        # Derived fields:
        # Risk/Share = Entry - Stop Loss
        risk_expr = ExpressionWrapper(
            F('option_buy_price') - F('stop_loss_price'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
        # Qty ≈ floor(Capital Required / Entry)
        # Note: floor is applied in template for portability
        qty_expr = ExpressionWrapper(
            F('capital_required') / F('option_buy_price'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
        qs = qs.annotate(risk_per_share=risk_expr, raw_qty=qty_expr)

        # Default date = today if none supplied
        if 'date' not in self.request.GET:
            qs = qs.filter(created_at=timezone.now().date())

        # Apply django-filter
        self.filterset = TradePlanFilter(self.request.GET or None, queryset=qs)
        return self.filterset.qs.order_by('-created_at', 'stock_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter'] = self.filterset
        # Choose heading date: requested date or today
        request_date = self.request.GET.get('date')
        from datetime import date
        ctx['heading_date'] = request_date or str(date.today())
        return ctx


def trade_news_api(request):
    fmt = '%Y-%m-%d'
    today = timezone.localdate()
    s = request.GET.get('start')
    e = request.GET.get('end')
    start = datetime.strptime(s, fmt).date() if s else today
    end = datetime.strptime(e, fmt).date() if e else today

    qs = (TradeMaster.objects
          .filter(created_at__gte=start, created_at__lte=end)
          .order_by('stock_name')
          .values('stock_name', 'news_catalyst_summary', 'created_at'))
    data = list(qs)
    return JsonResponse({'results': data})


@login_required
@require_http_methods(["GET"])
def transactions_list_api(request):
    fmt = '%Y-%m-%d'
    today = timezone.localdate()
    s = request.GET.get('start'); e = request.GET.get('end')
    start = datetime.strptime(s, fmt).date() if s else today
    end = datetime.strptime(e, fmt).date() if e else today
    qs = (TradeTransaction.objects
          .select_related('trade')
          .filter(created_at__date__gte=start,
                  created_at__date__lte=end,
                  created_by=request.user)
          .order_by('-created_at')
          .values('id', 'trade_id', 'trade__stock_name',
                  'buy_price', 'sell_price', 'quantity',
                  'is_ai_correct', 'profit_or_loss', 'created_at'))
    return JsonResponse({'results': list(qs)})

@login_required
@require_http_methods(["POST"])
def transactions_create_api(request):
    # Expect standard form-encoded body; if JSON, parse accordingly
    form = TradeTransactionForm(request.POST)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()
        return JsonResponse({'id': obj.id}, status=201)
    return JsonResponse({'errors': form.errors}, status=400)
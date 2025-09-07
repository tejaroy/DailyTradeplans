# trades/admin.py
from django.utils.safestring import mark_safe
import requests
from django.contrib import admin
from django.db.models import Sum, Count, Case, When, F, Value, DecimalField
from django.db.models.functions import TruncDate
from django.core.serializers.json import DjangoJSONEncoder
import json
from decimal import Decimal, ROUND_HALF_UP
from django.urls import reverse
from decimal import Decimal
from django.db import transaction
from django.urls import reverse
import requests
from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from django.views import View
from django.utils import timezone
from django.db.models import F, ExpressionWrapper, DecimalField
from datetime import datetime, time, timedelta
from django.shortcuts import redirect
from django.contrib import messages
from django.forms import modelformset_factory

from .models import TradeMaster, TradeTransaction, TradeProfitLoss
from .forms import (
    TradeProfitLossForm,
    TradeNewsFormSet,
    TradeTransactionFormSet,
    TradeTransactionForm,
    TradeTransactionFormSetPost
)
from django.db import transaction
from django.contrib import messages
from .models import TradeMaster


# Formset for the P/L page
TradeProfitLossFormSet = modelformset_factory(
    TradeProfitLoss, form=TradeProfitLossForm, extra=0, can_delete=False
)
# ---------------------------------------------------------------------------



class CustomUploadView(View):
    template_name = 'admin/trades/upload.html'

    def get(self, request):
        return TemplateResponse(request, self.template_name, {})

    def post(self, request):
        f = request.FILES.get('file')
        if not f:
            messages.error(request, "No file provided.")  # show error banner [21]
            return TemplateResponse(request, self.template_name, {})

        # Build absolute URL to DRF endpoint
        api_url = request.build_absolute_uri(reverse('excel_upload_api'))  # stable internal URL [15][9]

        try:
            files = {'file': (f.name, f.read(), f.content_type or 'text/csv')}  # multipart payload [1][13]
            resp = requests.post(api_url, files=files, timeout=30)  # call ExcelUploadAPIView [13]
        except Exception as e:
            messages.error(request, f"Upload failed: {e}")  # network or other error [21]
            return TemplateResponse(request, self.template_name, {})

        # Surface API result
        try:
            data = resp.json()
        except Exception:
            data = {'error': resp.text[:300]}

        if resp.ok:
            messages.success(request, data.get('success', 'Data uploaded successfully.'))  # success banner [21]
        else:
            messages.error(request, data.get('error', f"API error {resp.status_code}"))  # error banner [21]

        return TemplateResponse(request, self.template_name, {})

# ---------------------------------------------------------------------------

class TradeMasterPlanView(View):
    template_name = 'admin/trades/plan.html'

    def _dates(self, request):
        fmt = '%Y-%m-%d'
        today = timezone.localdate()
        s = request.GET.get('start')
        e = request.GET.get('end')
        start = datetime.strptime(s, fmt).date() if s else today
        end = datetime.strptime(e, fmt).date() if e else today
        return start, end  # parse once per request [18]

    def _trades(self, start, end):
        return (
            TradeMaster.objects
            .filter(created_at__gte=start, created_at__lte=end)
            .order_by('stock_name')
        )  # date-filtered base trades [18]

    def _ensure_user_tpl(self, trades, user):
        have = set(
            TradeProfitLoss.objects
            .filter(trade__in=trades, created_by=user)
            .values_list('trade_id', flat=True)
        )
        missing = [
            TradeProfitLoss(trade=t, created_by=user, updated_by=user)
            for t in trades if t.id not in have
        ]
        if missing:
            TradeProfitLoss.objects.bulk_create(missing)  # seed per-user rows [18]

    def _tpl_queryset(self, trades, user):
        return (
            TradeProfitLoss.objects
            .select_related('trade')
            .filter(trade__in=trades, created_by=user)
            .annotate(
                risk_per_share=ExpressionWrapper(
                    F('trade__option_buy_price') - F('trade__stop_loss_price'),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                qty=ExpressionWrapper(
                    F('trade__capital_required') / F('trade__option_buy_price'),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            )
            .order_by('trade__stock_name')
        )  # compute risk/qty via F and ExpressionWrapper [18]

    def get(self, request):
        start, end = self._dates(request)
        trades = list(self._trades(start, end))
        self._ensure_user_tpl(trades, request.user)
        qs_tpl = self._tpl_queryset(trades, request.user)
        formset = TradeProfitLossFormSet(queryset=qs_tpl, prefix='r')
        ctx = {**admin.site.each_context(request), 'rows': trades, 'formset': formset, 'start': start, 'end': end}
        return TemplateResponse(request, self.template_name, ctx)

    def post(self, request):
        start, end = self._dates(request)
        trades = list(self._trades(start, end))
        qs_tpl = self._tpl_queryset(trades, request.user)
        formset = TradeProfitLossFormSet(request.POST, queryset=qs_tpl, prefix='r')
        if formset.is_valid():
            objs = formset.save(commit=False)
            for obj in objs:
                obj.updated_by = request.user
                obj.save()
            messages.success(request, 'Saved.')
            return redirect(f"{request.path}?start={start}&end={end}")
        ctx = {**admin.site.each_context(request), 'rows': trades, 'formset': formset, 'start': start, 'end': end}
        return TemplateResponse(request, self.template_name, ctx)

# ---------------------------------------------------------------------------

class TradeNewsView(View):
    template_name = 'admin/trades/news.html'

    def _dates(self, request):
        fmt = '%Y-%m-%d'
        today = timezone.localdate()
        s = request.GET.get('start')
        e = request.GET.get('end')
        start = datetime.strptime(s, fmt).date() if s else today
        end = datetime.strptime(e, fmt).date() if e else today
        return start, end  # parse once [18]

    def _trades(self, start, end):
        return (TradeMaster.objects.filter(created_at__gte=start, created_at__lte=end).order_by('stock_name'))

    def get(self, request):
        start, end = self._dates(request)
        rows = self._trades(start, end)
        ctx = {**admin.site.each_context(request), 'rows': rows, 'start': start, 'end': end}
        return TemplateResponse(request, self.template_name, ctx)

    def post(self, request):
        start, end = self._dates(request)
        qs = self._trades(start, end)
        formset = TradeNewsFormSet(request.POST, queryset=qs, prefix='n')
        if formset.is_valid():
            formset.save()
            messages.success(request, "Trade news updated.")
            return redirect(f"{request.path}?start={start}&end={end}")
        ctx = {**admin.site.each_context(request), 'formset': formset, 'start': start, 'end': end}
        return TemplateResponse(request, self.template_name, ctx)

# ---------------------------------------------------------------------------

class TradeTransactionsView(View):
    template_name = 'admin/trades/transactions.html'

    def _dates(self, request):
        fmt = '%Y-%m-%d'
        today = timezone.localdate()
        s = request.GET.get('start')
        e = request.GET.get('end')
        start = datetime.strptime(s, fmt).date() if s else today
        end   = datetime.strptime(e, fmt).date() if e else today
        return start, end  # parse once [18]

    def _range(self, start, end):
        start_dt = timezone.make_aware(datetime.combine(start, time.min))
        end_dt   = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
        return start_dt, end_dt  # inclusive [start, end] as [start, next_day) [18]

    def _qs(self, request, start, end):
        start_dt, end_dt = self._range(start, end)
        return (
            TradeTransaction.objects
            .select_related('trade')  # relation-only join [21]
            .filter(created_by=request.user, created_at__gte=start_dt, created_at__lt=end_dt)
            .order_by('-created_at')
        )  # table/formset queryset [18]

    def _trade_choices(self, start, end):
        return (
            TradeMaster.objects
            .filter(created_at__gte=start, created_at__lte=end)
            .order_by('stock_name')
        )  # ModelChoiceField queryset for trade [1][8]

    def get(self, request):
        start, end = self._dates(request)
        qs = self._qs(request, start, end)
        add_form = TradeTransactionForm()
        add_form.fields['trade'].queryset = self._trade_choices(start, end)
        formset = TradeTransactionFormSet(queryset=qs, prefix='t')
        ctx = {**admin.site.each_context(request), 'rows': qs,'add_form': add_form, 'formset': formset, 'start': start, 'end': end}
        return TemplateResponse(request, self.template_name, ctx)



    def _auto_flags(self, buy, sell, qty):
        # Profit if selling price minus cost price is non-negative; scale by quantity
        amt = (Decimal(sell) - Decimal(buy)) * Decimal(qty)
        amt = amt.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if amt >= 0:
            return True, 'Profit', amt, None
        return False, 'Loss', None, (-amt)

    def post(self, request):
        try:
            start, end = self._dates(request)
            table_qs = self._qs(request, start, end)
            action = request.POST.get('action')

            if action == 'add':
                add_form = TradeTransactionForm(request.POST)
                add_form.fields['trade'].queryset = self._trade_choices(start, end)
                formset = TradeTransactionFormSet(queryset=table_qs, prefix='t')  # unbound on add

                posted_id = request.POST.get('trade')
                if posted_id and not add_form.fields['trade'].queryset.filter(pk=posted_id).exists():
                    add_form.add_error('trade', 'Selected trade is outside the current date range.')
                    ctx = {**admin.site.each_context(request), 'add_form': add_form, 'formset': formset, 'start': start, 'end': end}
                    return TemplateResponse(request, self.template_name, ctx)

                if add_form.is_valid():
                    cd = add_form.cleaned_data
                    is_ok, pol, profit_amt, loss_amt = self._auto_flags(cd['buy_price'], cd['sell_price'], cd['quantity'])  # compute all
                    obj, created = TradeTransaction.objects.get_or_create(
                        trade=cd['trade'],
                        buy_price=cd['buy_price'],
                        sell_price=cd['sell_price'],
                        quantity=cd['quantity'],
                        created_by=request.user,
                        defaults={
                            'is_ai_correct': is_ok,
                            'profit_or_loss': pol,
                            'profit_amount': profit_amt,
                            'loss_amount': loss_amt,
                            'updated_by': request.user,
                        },
                    )  # upsert add [1][4]
                    if not created:
                        obj.is_ai_correct = is_ok
                        obj.profit_or_loss = pol
                        obj.profit_amount = profit_amt
                        obj.loss_amount = loss_amt
                        obj.updated_by = request.user
                        obj.save(update_fields=['is_ai_correct', 'profit_or_loss', 'profit_amount', 'loss_amount', 'updated_by'])  # efficient update [4]
                    messages.success(request, "Transaction added or updated.")
                    return redirect(f"{request.path}?start={start}&end={end}")

                ctx = {**admin.site.each_context(request), 'add_form': add_form, 'formset': formset, 'start': start, 'end': end}
                return TemplateResponse(request, self.template_name, ctx)

            # Edit branch
            add_form = TradeTransactionForm()
            add_form.fields['trade'].queryset = self._trade_choices(start, end)
            formset = TradeTransactionFormSet(request.POST, queryset=table_qs, prefix='t')  # bound

            if formset.is_valid():
                for form in formset.forms:
                    if not form.has_changed():
                        continue
                    cd = form.cleaned_data
                    pk = form.instance.pk
                    is_ok, pol, profit_amt, loss_amt = self._auto_flags(cd['buy_price'], cd['sell_price'], cd['quantity'])  # recompute

                    if pk:
                        obj, _ = TradeTransaction.objects.update_or_create(
                            id=pk,
                            defaults={
                                'buy_price': cd['buy_price'],
                                'sell_price': cd['sell_price'],
                                'quantity': cd['quantity'],
                                'is_ai_correct': is_ok,
                                'profit_or_loss': pol,
                                'profit_amount': profit_amt,
                                'loss_amount': loss_amt,
                                'updated_by': request.user,
                            },
                        )  # atomic upsert [1][4]
                    else:
                        obj = TradeTransaction.objects.create(
                            trade=cd['trade'],
                            buy_price=cd['buy_price'],
                            sell_price=cd['sell_price'],
                            quantity=cd['quantity'],
                            is_ai_correct=is_ok,
                            profit_or_loss=pol,
                            profit_amount=profit_amt,
                            loss_amount=loss_amt,
                            created_by=request.user,
                            updated_by=request.user,
                        )
                messages.success(request, "Transactions saved.")
                return redirect(f"{request.path}?start={start}&end={end}")

            ctx = {**admin.site.each_context(request), 'add_form': add_form, 'formset': formset, 'start': start, 'end': end}
            return TemplateResponse(request, self.template_name, ctx)
        except Exception as e:
            print(e)

# ---------------------------------------------------------------------------

class TradeMasterAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}  # hide model from index; URLs still work [18]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('plan/', self.admin_site.admin_view(TradeMasterPlanView.as_view()), name='trades_plan'),
            path('upload/', self.admin_site.admin_view(CustomUploadView.as_view()), name='trades_upload'),
            path('news/', self.admin_site.admin_view(TradeNewsView.as_view()), name='trades_news'),
            path('transactions/', self.admin_site.admin_view(TradeTransactionsView.as_view()), name='trades_transactions'),
        ]
        return custom + urls

admin.site.register(TradeMaster, TradeMasterAdmin)

class HiddenTradeTransactionAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}  # hidden entry; used via custom view [18]

admin.site.register(TradeTransaction, HiddenTradeTransactionAdmin)


# def _parse_date(s: str):
#     if not s:
#         return None
#     s = s.strip()
#     for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
#         try:
#             return datetime.strptime(s, fmt).date()
#         except ValueError:
#             continue
#     return None  # ignore invalid input

# @admin.register(TradeProfitLoss)
# class TradeProfitLossAdmin(admin.ModelAdmin):
#     change_list_template = "admin/trades/tradeprofitloss/change_list.html"
#     list_display = ("trade", "created_by", "profit_or_loss", "profit_amount", "loss_amount", "updated_at")
#     list_filter = ("profit_or_loss", "created_by")
#     search_fields = ("trade__stock_name",)

#     def get_queryset(self, request):
#         qs = super().get_queryset(request).select_related("trade", "created_by")
#         start = _parse_date(request.GET.get("start"))
#         end = _parse_date(request.GET.get("end"))
#         trade_id = request.GET.get("trade")

#         if start:
#             qs = qs.filter(updated_at__date__gte=start)  # inclusive from date [3]
#         if end:
#             qs = qs.filter(updated_at__date__lte=end)    # inclusive to date [3]
#         if trade_id:
#             qs = qs.filter(trade_id=trade_id)            # trade dropdown filter [4]
#         return qs

#     def changelist_view(self, request, extra_context=None):
#         extra_context = extra_context or {}
#         extra_context["trade_choices"] = list(
#             TradeMaster.objects.values("id", "stock_name").order_by("stock_name")
#         )  # populate Trade filter choices [14]
#         return super().changelist_view(request, extra_context=extra_context)\
from django.urls import path
from .apis import ExcelUploadAPIView
from .admin import CustomUploadView
from .views import DailyPlanView,trade_news_api, transactions_create_api,transactions_list_api

from django.contrib import admin
admin.site.index_template = 'admin/custom_index.html'


urlpatterns = [
    path('api/upload/', ExcelUploadAPIView.as_view(), name='api-upload-excel'),
    path('admin/upload/', CustomUploadView.as_view(), name='admin-upload'),
    path('plans/daily/', DailyPlanView.as_view(), name='daily-plan'),
    path('api/trade-news/', trade_news_api, name='trade_news_api'),
    path('api/transactions/', transactions_list_api, name='transactions_list_api'),
    path('api/transactions/create/', transactions_create_api, name='transactions_create_api'),
    path('api/excel-upload/', ExcelUploadAPIView.as_view(), name='excel_upload_api'),
]

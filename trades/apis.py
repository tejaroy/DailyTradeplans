# trades/apis.py
from decimal import Decimal
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import pandas as pd
from .models import TradeMaster

NUMERIC_COLS = [
    'Option Buy Price (₹)',
    'Intraday Exit Price Target (₹)',
    'Stop Loss Price (₹)',
    'Capital Required (₹)',
    'Max Loss If Stop Loss Hits (₹)',
    'Max Profit If Target Hits (₹)',
]

def _to_numeric_series(s):
    # remove ₹ and commas, then coerce to number
    return pd.to_numeric(
        s.astype(str).str.replace(r'[₹,]', '', regex=True).str.strip(),
        errors='coerce'
    )

def _dec_or_none(v):
    if pd.isna(v):
        return None
    return Decimal(str(v))

class ExcelUploadAPIView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            name = file.name.lower()
            if name.endswith('.csv'):
                # parse numbers with thousands separators
                df = pd.read_csv(file, thousands=',')
            elif name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                return Response({'error': 'File must be .xlsx, .xls or .csv'}, status=status.HTTP_400_BAD_REQUEST)

            # standardize column names (optional, keeps exact headers if already matching)
            df.columns = [c.strip() for c in df.columns]

            # clean currency/commas and convert to numbers
            for col in NUMERIC_COLS:
                if col in df.columns:
                    df[col] = _to_numeric_series(df[col])

            # create rows
            for _, row in df.iterrows():
                TradeMaster.objects.create(
                    stock_name=str(row['Stock Name']).strip(),
                    option_strike_price_expiry=str(row['Option Strike Price & Expiry']).strip(),
                    option_buy_price=_dec_or_none(row['Option Buy Price (₹)']),
                    intraday_exit_price_target=_dec_or_none(row['Intraday Exit Price Target (₹)']),
                    stop_loss_price=_dec_or_none(row['Stop Loss Price (₹)']),
                    support_level=str(row.get('Support Level (₹)', '')).strip(),
                    resistance_level=str(row.get('Resistance Level (₹)', '')).strip(),
                    capital_required=_dec_or_none(row['Capital Required (₹)']),
                    max_loss_if_stop_loss_hits=_dec_or_none(row['Max Loss If Stop Loss Hits (₹)']),
                    max_profit_if_target_hits=_dec_or_none(row['Max Profit If Target Hits (₹)']),
                    news_catalyst_summary=str(row.get('News Catalyst Summary', '')).strip(),
                )

            return Response({'success': 'Data uploaded successfully'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
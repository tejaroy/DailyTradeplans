# 📈 Trading Admin Dashboard (Django)

A Django Admin–driven trading dashboard with per-user visibility, time-series summaries, KPI cards, Chart.js visuals, and a secure CSV/Excel uploader for privileged roles.

---

## 🚀 Highlights

- **Custom admin changelist**: With a top filter bar (From/To, Day/Week/Month/Year, Profit/Loss), conditional Trade dropdown, and embedded charts via template inheritance.
- **User‑scoped data**: All KPIs, charts, and grids show data only for the logged-in user.
- **Database‑level analytics**: Aggregated metrics like capital (quantity × buy_price) computed using Django ORM expressions.
- **Conditional Trade filter**: Appears only when trades exist in the current filter window.
- **Secure uploads**: Excel/CSV import is gated behind permissions and hidden for regular staff.

---

## 🗃️ Data Model

| Model | Description |
|-------|-------------|
| `TradeMaster` | Instrument metadata and reference fields like capital_required. |
| `TradeTransaction` | Per-execution rows with buy/sell prices, quantity, and profit/loss. |
| `TradeProfitLoss` | Per-user per-trade summaries for reporting and consistency. |
| `AccountSummary` | Proxy model registered in admin to render the dashboard. |

---

## 📊 Analytics Logic

- **Grouping**: Uses `TruncDay`, `TruncWeek`, `TruncMonth`, `TruncYear` for series.
- **KPIs**: ORM aggregates like `Sum`, `Count`, and `ExpressionWrapper(F("quantity") * F("buy_price"))`.
- **Defaults**: Shows "today" if no filters provided; retains GET params cleanly.

---

## 🛠️ Admin UX Features

- Template extends base admin to add:
  - KPI cards
  - Chart.js visuals
  - Trade dropdown (if applicable)
- All native admin functionality preserved (`block.super`).
- Trade dropdown appears only if relevant data exists in the current filter.

---

## 🔐 Permissions & Uploads

- **Permission-based access**:
  - Users with `can_upload_transactions` or in the "supervisor" group can upload.
  - Staff users cannot access or see the upload functionality.
- **Upload behavior**:
  - Accepts CSV/Excel
  - Parses and validates rows
  - Computes profit/loss
  - Upserts transactions
  - Displays counts for created, updated, skipped rows

---

## ⚙️ Local Setup

### Prerequisites

- Python 3.10+
- pip
- virtualenv

### Steps

```bash
# Create and activate environment
python -m venv .venv
. .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
export SECRET_KEY="change-me"  # Or set in a .env file

# Migrate and run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import json
import os
from datetime import datetime, date, timedelta
import io
import csv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

DATA_FILE = 'data.json'

# Fungsi untuk memuat data dari file JSON
def load_data():
    if not os.path.exists(DATA_FILE):
        # Data awal jika file belum ada
        default_data = {
            "transactions": [],
            "categories": [
                {"id": 1, "name": "Makan", "color": "#ff7675", "icon": "utensils", "subcategories": [{"id": 11, "name": "Warung"},{"id":12,"name":"Restoran"}]},
                {"id": 2, "name": "Transportasi", "color": "#74b9ff", "icon": "car", "subcategories": [{"id":21,"name":"Bensin"},{"id":22,"name":"Parkir"}]}
            ],
            "wallets": [
                {"id": 1, "name": "Tunai", "initial_balance": 0},
                {"id": 2, "name": "Bank A", "initial_balance": 0}
            ],
            "recurring": [],
            "budgets": [],
            "next_id": 1,
            "next_category_id": 3,
            "next_subcategory_id": 101,
            "next_wallet_id": 3
        }
        save_data(default_data)
        return default_data

    with open(DATA_FILE, 'r') as f:
        return json.load(f)

# Fungsi untuk menyimpan data ke file JSON
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Fungsi menghitung ulang saldo berdasarkan semua transaksi
def recalculate_balance(data):
    # Total balance = sum of wallet balances after applying transactions
    wallets = {w['id']: w.get('initial_balance', 0) for w in data.get('wallets', [])}
    for t in data.get('transactions', []):
        wid = t.get('wallet_id')
        if not wid:
            continue
        if t['type'] == 'income':
            wallets[wid] = wallets.get(wid, 0) + t['amount']
        else:
            wallets[wid] = wallets.get(wid, 0) - t['amount']
    return sum(wallets.values())

def recalculate_wallets(data):
    wallets = {w['id']: w.get('initial_balance', 0) for w in data.get('wallets', [])}
    for t in data.get('transactions', []):
        wid = t.get('wallet_id')
        if not wid:
            continue
        if t['type'] == 'income':
            wallets[wid] = wallets.get(wid, 0) + t['amount']
        else:
            wallets[wid] = wallets.get(wid, 0) - t['amount']
    # write back wallet balances as computed (for display)
    computed = []
    for w in data.get('wallets', []):
        computed.append({
            'id': w['id'],
            'name': w['name'],
            'balance': wallets.get(w['id'], 0)
        })
    return computed

def parse_date(dt_str):
    try:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

def compute_budget_status(data):
    """Compute spent for each budget and return list with status."""
    now = datetime.now()
    budgets = []
    for b in data.get('budgets', []):
        cat_id = b.get('category_id')
        month = b.get('month', now.month)
        year = b.get('year', now.year)
        limit = float(b.get('limit', 0))
        spent = 0.0
        for t in data.get('transactions', []):
            if t.get('type') == 'expense' and t.get('category_id') == cat_id:
                dt = parse_date(t.get('date',''))
                if not dt:
                    continue
                if dt.month == month and dt.year == year:
                    spent += float(t.get('amount', 0))
        percent = (spent / limit * 100) if limit > 0 else 0
        status = 'ok'
        if limit > 0 and spent >= limit:
            status = 'over'
        elif limit > 0 and spent >= 0.9 * limit:
            status = 'near'
        budgets.append({
            'id': b.get('id'),
            'category_id': cat_id,
            'limit': limit,
            'spent': spent,
            'percent': percent,
            'month': month,
            'year': year,
            'status': status
        })
    return budgets

def next_due_date(last_run, frequency):
    now = datetime.now()
    if last_run:
        try:
            lr = datetime.strptime(last_run, '%Y-%m-%d %H:%M:%S')
        except Exception:
            lr = None
    else:
        lr = None
    if not lr:
        return now
    if frequency == 'daily':
        return lr + timedelta(days=1)
    if frequency == 'weekly':
        return lr + timedelta(weeks=1)
    if frequency == 'monthly':
        # naive month add: add 30 days
        return lr + timedelta(days=30)
    return now

def process_recurring(data):
    """Check recurring rules and create transactions if due."""
    changed = False
    now = datetime.now()
    for r in data.get('recurring', []):
        freq = r.get('frequency')
        last = r.get('last_run')
        due = next_due_date(last, freq)
        if due <= now:
            # create transaction
            t = {
                'id': data.get('next_id', 1),
                'description': r.get('description', '') + ' (recurring)',
                'amount': float(r.get('amount', 0)),
                'type': r.get('type', 'expense'),
                'date': now.strftime('%Y-%m-%d %H:%M:%S'),
                'wallet_id': r.get('wallet_id', 1),
                'category_id': r.get('category_id', 0),
                'subcategory': r.get('subcategory','')
            }
            data.setdefault('transactions', []).append(t)
            data['next_id'] = data.get('next_id', 1) + 1
            r['last_run'] = now.strftime('%Y-%m-%d %H:%M:%S')
            changed = True
    if changed:
        save_data(data)
    return changed

@app.route('/')
def index():
    data = load_data()
    # process recurring items first (create due transactions)
    process_recurring(data)
    wallets = recalculate_wallets(data)
    balance = recalculate_balance(data)
    budgets_status = compute_budget_status(data)
    # Compute totals for charts: total income vs expense and expense per category
    income_total = 0.0
    expense_total = 0.0
    category_map = {c['id']: c.get('name', 'Umum') for c in data.get('categories', [])}
    category_totals = {}
    for t in data.get('transactions', []):
        try:
            amt = float(t.get('amount', 0))
        except Exception:
            amt = 0.0
        if t.get('type') == 'income':
            income_total += amt
        else:
            expense_total += amt
            cname = category_map.get(t.get('category_id'), 'Umum')
            category_totals[cname] = category_totals.get(cname, 0) + amt
    # flash notifications for budgets
    for b in budgets_status:
        if b['status'] == 'near':
            flash(f"Anggaran kategori {b['category_id']} mendekati batas: Rp {b['spent']:.0f} / Rp {b['limit']:.0f}", 'warning')
        elif b['status'] == 'over':
            flash(f"Anggaran kategori {b['category_id']} terlampaui: Rp {b['spent']:.0f} / Rp {b['limit']:.0f}", 'danger')
    # Prepare category breakdowns for charts
    categories = data.get('categories', [])
    # map category id -> info
    cat_map = {c['id']: {'name': c.get('name', str(c.get('id'))), 'color': c.get('color', '#888')} for c in categories}
    cat_map[0] = {'name': 'Umum', 'color': '#cccccc'}

    income_totals = {}
    expense_totals = {}
    for t in data.get('transactions', []):
        cid = t.get('category_id', 0) or 0
        try:
            amt = float(t.get('amount', 0))
        except Exception:
            amt = 0
        if t.get('type') == 'income':
            income_totals[cid] = income_totals.get(cid, 0) + amt
        else:
            expense_totals[cid] = expense_totals.get(cid, 0) + amt

    # build lists for charting (only categories with non-zero amounts)
    income_labels, income_values, income_colors = [], [], []
    for cid, amt in income_totals.items():
        if amt <= 0:
            continue
        info = cat_map.get(cid, {'name': str(cid), 'color': '#888'})
        income_labels.append(info['name'])
        income_values.append(amt)
        income_colors.append(info.get('color', '#888'))

    expense_labels, expense_values, expense_colors = [], [], []
    for cid, amt in expense_totals.items():
        if amt <= 0:
            continue
        info = cat_map.get(cid, {'name': str(cid), 'color': '#888'})
        expense_labels.append(info['name'])
        expense_values.append(amt)
        expense_colors.append(info.get('color', '#888'))

    return render_template('index.html', 
                         transactions=data['transactions'],
                         balance=balance,
                         categories=categories,
                         wallets=wallets,
                         budgets=data.get('budgets', []),
                         budgets_status=budgets_status,
                         recurring=data.get('recurring', []),
                         income_labels=income_labels,
                         income_values=income_values,
                         income_colors=income_colors,
                         expense_labels=expense_labels,
                         expense_values=expense_values,
                         expense_colors=expense_colors)

@app.route('/add_budget', methods=['POST'])
def add_budget():
    data = load_data()
    try:
        category_id = int(request.form.get('category_id', 0))
    except ValueError:
        category_id = 0
    try:
        limit = float(request.form.get('limit', '0'))
    except ValueError:
        limit = 0
    try:
        month = int(request.form.get('month', datetime.now().month))
        year = int(request.form.get('year', datetime.now().year))
    except ValueError:
        month = datetime.now().month
        year = datetime.now().year
    new_budget = {
        'id': data.get('next_category_id', 1000),
        'category_id': category_id,
        'limit': limit,
        'month': month,
        'year': year
    }
    data.setdefault('budgets', []).append(new_budget)
    # increment a standalone id tracker for budgets
    data['next_category_id'] = data.get('next_category_id', 1000) + 1
    save_data(data)
    return redirect(url_for('index'))


@app.route('/add_recurring', methods=['POST'])
def add_recurring():
    data = load_data()
    description = request.form.get('description', '').strip()
    try:
        amount = float(request.form.get('amount', '0'))
    except ValueError:
        amount = 0
    trans_type = request.form.get('type', 'expense')
    wallet_id = int(request.form.get('wallet_id', 1))
    category_id = int(request.form.get('category_id', 0))
    subcategory = request.form.get('subcategory', '')
    frequency = request.form.get('frequency', 'monthly')
    if not description or amount <= 0:
        flash('Recurring tidak valid', 'danger')
        return redirect(url_for('index'))
    r = {
        'id': data.get('next_recurring_id', 1),
        'description': description,
        'amount': amount,
        'type': trans_type,
        'wallet_id': wallet_id,
        'category_id': category_id,
        'subcategory': subcategory,
        'frequency': frequency,
        'last_run': None
    }
    data.setdefault('recurring', []).append(r)
    data['next_recurring_id'] = data.get('next_recurring_id', 1) + 1
    save_data(data)
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
def add_transaction():
    data = load_data()

    description = request.form.get('description', '').strip()
    amount_str = request.form.get('amount', '0')
    trans_type = request.form.get('type', 'expense')
    wallet_id = int(request.form.get('wallet_id', 1))
    category_id = int(request.form.get('category_id', 0))
    subcategory = request.form.get('subcategory', '')

    if not description:
        flash('Deskripsi wajib diisi', 'danger')
        return redirect(url_for('index'))

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash('Jumlah harus > 0', 'danger')
            return redirect(url_for('index'))
    except ValueError:
        flash('Jumlah tidak valid', 'danger')
        return redirect(url_for('index'))

    new_transaction = {
        'id': data.get('next_id', 1),
        'description': description,
        'amount': amount,
        'type': trans_type,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'wallet_id': wallet_id,
        'category_id': category_id,
        'subcategory': subcategory
    }

    data['transactions'].append(new_transaction)
    data['next_id'] = data.get('next_id', 1) + 1

    save_data(data)
    return redirect(url_for('index'))

@app.route('/add_wallet', methods=['POST'])
def add_wallet():
    data = load_data()
    name = request.form.get('name', '').strip()
    initial = request.form.get('initial', '0')
    try:
        initial_balance = float(initial)
    except ValueError:
        initial_balance = 0
    if not name:
        flash('Nama dompet wajib', 'danger')
        return redirect(url_for('index'))
    new_wallet = {
        'id': data.get('next_wallet_id', 3),
        'name': name,
        'initial_balance': initial_balance
    }
    data.setdefault('wallets', []).append(new_wallet)
    data['next_wallet_id'] = data.get('next_wallet_id', 3) + 1
    save_data(data)
    return redirect(url_for('index'))

@app.route('/transfer', methods=['POST'])
def transfer():
    data = load_data()
    from_id = int(request.form.get('from_wallet'))
    to_id = int(request.form.get('to_wallet'))
    amount = 0
    try:
        amount = float(request.form.get('amount', '0'))
    except ValueError:
        amount = 0
    if amount <= 0 or from_id == to_id:
        flash('Transfer tidak valid', 'danger')
        return redirect(url_for('index'))
    # Create two transactions: expense from source, income to dest
    t1 = {
        'id': data.get('next_id', 1),
        'description': f'Transfer ke {to_id}',
        'amount': amount,
        'type': 'expense',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'wallet_id': from_id,
        'category_id': 0,
        'subcategory': 'Transfer'
    }
    data['transactions'].append(t1)
    data['next_id'] = data.get('next_id', 1) + 1

    t2 = {
        'id': data.get('next_id', 1),
        'description': f'Transfer dari {from_id}',
        'amount': amount,
        'type': 'income',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'wallet_id': to_id,
        'category_id': 0,
        'subcategory': 'Transfer'
    }
    data['transactions'].append(t2)
    data['next_id'] = data.get('next_id', 1) + 1
    save_data(data)
    return redirect(url_for('index'))

@app.route('/export')
def export_csv():
    data = load_data()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['id','date','description','type','amount','wallet_id','category_id','subcategory'])
    for t in data.get('transactions', []):
        cw.writerow([t.get('id'), t.get('date'), t.get('description'), t.get('type'), t.get('amount'), t.get('wallet_id'), t.get('category_id'), t.get('subcategory')])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='transactions.csv')

@app.route('/delete/<int:transaction_id>')
def delete_transaction(transaction_id):
    data = load_data()
    # Hapus transaksi berdasarkan ID
    data['transactions'] = [t for t in data.get('transactions', []) if t.get('id') != transaction_id]
    # Recalculate balance using full data structure
    data['balance'] = recalculate_balance(data)
    save_data(data)
    return redirect(url_for('index'))

@app.route('/clear-all')
def clear_all():
    # Hapus semua transaksi but preserve categories, wallets, and other config
    data = load_data()
    data['transactions'] = []
    data['next_id'] = 1
    # Optionally reset recurring/budgets if you want; keep as-is for now
    save_data(data)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

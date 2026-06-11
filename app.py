from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import json
import os
from datetime import datetime, date
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

@app.route('/')
def index():
    data = load_data()
    wallets = recalculate_wallets(data)
    balance = recalculate_balance(data)
    return render_template('index.html', 
                         transactions=data['transactions'],
                         balance=balance,
                         categories=data.get('categories', []),
                         wallets=wallets,
                         budgets=data.get('budgets', []))

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
    data['transactions'] = [t for t in data['transactions'] if t['id'] != transaction_id]
    data['balance'] = recalculate_balance(data['transactions'])
    
    save_data(data)
    return redirect(url_for('index'))

@app.route('/clear-all')
def clear_all():
    # Hapus semua transaksi
    default_data = {
        "transactions": [],
        "balance": 0,
        "next_id": 1
    }
    save_data(default_data)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

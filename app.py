from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

DATA_FILE = 'data.json'

# Fungsi untuk memuat data dari file JSON
def load_data():
    if not os.path.exists(DATA_FILE):
        # Data awal jika file belum ada
        default_data = {
            "transactions": [],
            "balance": 0,
            "next_id": 1
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
def recalculate_balance(transactions):
    balance = 0
    for transaction in transactions:
        if transaction['type'] == 'income':
            balance += transaction['amount']
        else:
            balance -= transaction['amount']
    return balance

@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', 
                         transactions=data['transactions'],
                         balance=data['balance'])

@app.route('/add', methods=['POST'])
def add_transaction():
    data = load_data()
    
    description = request.form.get('description', '').strip()
    amount_str = request.form.get('amount', '0')
    trans_type = request.form.get('type', 'expense')
    
    # Validasi input
    if not description:
        return redirect(url_for('index'))
    
    try:
        amount = float(amount_str)
        if amount <= 0:
            return redirect(url_for('index'))
    except ValueError:
        return redirect(url_for('index'))
    
    # Buat transaksi baru
    new_transaction = {
        'id': data.get('next_id', 1),
        'description': description,
        'amount': amount,
        'type': trans_type,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    data['transactions'].append(new_transaction)
    data['next_id'] = data.get('next_id', 1) + 1
    data['balance'] = recalculate_balance(data['transactions'])
    
    save_data(data)
    return redirect(url_for('index'))

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

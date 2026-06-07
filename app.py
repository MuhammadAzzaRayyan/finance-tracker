from flask import Flask, render_template, request, redirect, url_for, jsonify
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
            "balance": 0
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

# Route halaman utama
@app.route('/')
def index():
    data = load_data()
    transactions = data['transactions']
    balance = recalculate_balance(transactions)
    
    # Urutkan transaksi dari yang terbaru
    transactions.reverse()
    
    return render_template('index.html', 
                         transactions=transactions, 
                         balance=balance)

# API untuk menambah transaksi
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    description = request.form.get('description')
    amount = float(request.form.get('amount'))
    type_trans = request.form.get('type')
    
    data = load_data()
    
    new_transaction = {
        'id': len(data['transactions']) + 1,
        'description': description,
        'amount': amount,
        'type': type_trans,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    data['transactions'].append(new_transaction)
    data['balance'] = recalculate_balance(data['transactions'])
    save_data(data)
    
    return redirect(url_for('index'))

# API untuk menghapus transaksi
@app.route('/delete_transaction/<int:transaction_id>')
def delete_transaction(transaction_id):
    data = load_data()
    data['transactions'] = [t for t in data['transactions'] if t['id'] != transaction_id]
    data['balance'] = recalculate_balance(data['transactions'])
    save_data(data)
    
    return redirect(url_for('index'))

# API untuk mendapatkan data dalam format JSON
@app.route('/api/transactions')
def api_transactions():
    data = load_data()
    return jsonify(data['transactions'])

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

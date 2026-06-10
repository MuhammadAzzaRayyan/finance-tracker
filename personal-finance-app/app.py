from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime
import re

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None

app = Flask(__name__)

DATA_FILE = 'data.json'
UPLOAD_FOLDER = 'uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "transactions": [],
            "balance": 0
        }
        save_data(default_data)
        return default_data
    
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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
    transactions = data['transactions']
    balance = recalculate_balance(transactions)
    transactions.reverse()
    return render_template('index.html', 
                         transactions=transactions, 
                         balance=balance)

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    description = request.form.get('description')
    amount = float(request.form.get('amount'))
    type_trans = request.form.get('type')
    category = request.form.get('category') or 'Lain-lain'
    date_str = request.form.get('date')
    if date_str:
        date = date_str
    else:
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data = load_data()
    
    new_transaction = {
        'id': len(data['transactions']) + 1,
        'description': description,
        'amount': amount,
        'type': type_trans,
        'category': category,
        'date': date
    }
    
    data['transactions'].append(new_transaction)
    data['balance'] = recalculate_balance(data['transactions'])
    save_data(data)
    
    return redirect(url_for('index'))


@app.route('/scan')
def scan():
    return render_template('scan.html')


def _parse_ocr_text(text):
    # Basic heuristics: merchant = first non-empty line
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    merchant = lines[0] if lines else ''

    # Find date-like strings
    date_pattern = r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})"
    date_match = re.search(date_pattern, text)
    date = date_match.group(0) if date_match else ''

    # Find currency-like numbers, choose the largest as total
    nums = re.findall(r"[\d\.,]+", text)
    cleaned = []
    for n in nums:
        s = n.replace(',', '').replace('.', '')
        if s.isdigit():
            cleaned.append(int(s))
    total = max(cleaned) if cleaned else 0
    return {
        'merchant': merchant,
        'date': date,
        'total': total
    }


@app.route('/upload_scan', methods=['POST'])
def upload_scan():
    if 'receipt' not in request.files:
        return redirect(url_for('scan'))

    file = request.files['receipt']
    if file.filename == '':
        return redirect(url_for('scan'))

    filename = file.filename
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    if not pytesseract:
        ocr_text = 'ERROR: pytesseract not installed on server.'
        parsed = {'merchant': '', 'date': '', 'total': 0}
    else:
        try:
            img = Image.open(save_path)
            ocr_text = pytesseract.image_to_string(img, lang='ind')
            parsed = _parse_ocr_text(ocr_text)
        except Exception as e:
            ocr_text = f'ERROR: {e}'
            parsed = {'merchant': '', 'date': '', 'total': 0}

    # Convert total to float in rupiah format
    total_amount = parsed.get('total', 0)

    return render_template('scan_result.html', merchant=parsed.get('merchant',''), date=parsed.get('date',''), total=total_amount, ocr_text=ocr_text)

@app.route('/delete_transaction/<int:transaction_id>')
def delete_transaction(transaction_id):
    data = load_data()
    data['transactions'] = [t for t in data['transactions'] if t['id'] != transaction_id]
    data['balance'] = recalculate_balance(data['transactions'])
    save_data(data)
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
    
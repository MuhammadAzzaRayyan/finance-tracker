from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import json
import os
from datetime import datetime
import re
from werkzeug.utils import secure_filename

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None

app = Flask(__name__)

DATA_FILE = 'data.json'
UPLOAD_FOLDER = 'uploads'

# Default categories
CATEGORIES = [
    'Makan & Minum',
    'Transportasi',
    'Belanja',
    'Tagihan',
    'Hiburan',
    'Kesehatan',
    'Lain-lain'
]

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "transactions": [],
            "balance": 0,
            "budgets": {}
        }
        save_data(default_data)
        return default_data
    
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
        # ensure budgets key exists for older data files
        if 'budgets' not in data:
            data['budgets'] = {}
            save_data(data)
        return data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def save_uploaded_file(file):
    filename = secure_filename(file.filename)
    if not filename:
        return ''
    prefix = datetime.now().strftime("%Y%m%d%H%M%S_")
    unique = prefix + filename
    path = os.path.join(UPLOAD_FOLDER, unique)
    file.save(path)
    return unique


@app.route('/uploads/<path:fname>')
def uploaded_file(fname):
    return send_from_directory(UPLOAD_FOLDER, fname)

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
    # Monthly summary per category (current month)
    now = datetime.now()
    monthly_totals = {c: 0 for c in CATEGORIES}
    for t in data['transactions']:
        try:
            dt = datetime.strptime(t['date'].split('.')[0], "%Y-%m-%d %H:%M:%S") if ' ' in t['date'] else datetime.fromisoformat(t['date'])
        except Exception:
            try:
                dt = datetime.strptime(t['date'], "%Y-%m-%d")
            except Exception:
                continue
        if dt.year == now.year and dt.month == now.month and t.get('type') == 'expense':
            cat = t.get('category') or 'Lain-lain'
            if cat not in monthly_totals:
                monthly_totals[cat] = 0
            monthly_totals[cat] += t.get('amount', 0)

    # Prepare budget status
    budgets = data.get('budgets', {})
    budget_status = {}
    alerts = []
    for cat, budget in budgets.items():
        spent = monthly_totals.get(cat, 0)
        pct = (spent / budget * 100) if budget and budget > 0 else 0
        budget_status[cat] = { 'budget': budget, 'spent': spent, 'pct': pct }
        if budget and pct >= 90:
            alerts.append({ 'category': cat, 'pct': pct })
    return render_template('index.html', 
                         transactions=transactions, 
                         balance=balance,
                         categories=CATEGORIES,
                         monthly_totals=monthly_totals,
                         budgets=budgets,
                         budget_status=budget_status,
                         alerts=alerts,
                         now=now.strftime("%Y-%m-%d %H:%M:%S"))

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

    # handle receipt file upload (from add form)
    receipt_file = None
    if 'receipt' in request.files:
        f = request.files['receipt']
        if f and f.filename:
            saved = save_uploaded_file(f)
            if saved:
                new_transaction['receipt'] = saved

    # or attach an already-uploaded scanned file via hidden field
    receipt_filename = request.form.get('receipt_filename')
    if receipt_filename:
        new_transaction['receipt'] = receipt_filename
    
    data['transactions'].append(new_transaction)
    data['balance'] = recalculate_balance(data['transactions'])
    save_data(data)
    
    return redirect(url_for('index'))


@app.route('/set_budgets', methods=['POST'])
def set_budgets():
    data = load_data()
    budgets = data.get('budgets', {})
    for c in CATEGORIES:
        val = request.form.get(c)
        try:
            budgets[c] = float(val) if val not in (None, '') else 0
        except Exception:
            budgets[c] = 0
    data['budgets'] = budgets
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

    filename = save_uploaded_file(file)
    save_path = os.path.join(UPLOAD_FOLDER, filename) if filename else None

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

    return render_template('scan_result.html', merchant=parsed.get('merchant',''), date=parsed.get('date',''), total=total_amount, ocr_text=ocr_text, categories=CATEGORIES, saved_filename=filename)

@app.route('/delete_transaction/<int:transaction_id>')
def delete_transaction(transaction_id):
    data = load_data()
    data['transactions'] = [t for t in data['transactions'] if t['id'] != transaction_id]
    data['balance'] = recalculate_balance(data['transactions'])
    save_data(data)
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
    
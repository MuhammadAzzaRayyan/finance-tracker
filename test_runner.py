from app import app, load_data, save_data, recalculate_wallets
from datetime import datetime

def reset_data():
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
        "next_wallet_id": 3,
        "next_recurring_id": 1
    }
    save_data(default_data)
    return default_data

def ok(name, cond, notes=None):
    status = 'OK' if cond else 'FAIL'
    print(f"{status}: {name}" + (f" - {notes}" if notes else ""))
    return cond

def run_tests():
    failures = 0
    reset_data()
    with app.test_client() as client:
        # Test GET /
        r = client.get('/')
        if not ok('GET / returns 200', r.status_code == 200):
            failures += 1

        # Test add transaction
        r = client.post('/add', data={'description':'Test TX','amount':'100','type':'expense','wallet_id':'1','category_id':'1','subcategory':''}, follow_redirects=True)
        if not ok('POST /add returns 200', r.status_code == 200):
            failures += 1
        data = load_data()
        has_tx = any(t.get('description') == 'Test TX' for t in data.get('transactions', []))
        if not ok('Transaction added to data.json', has_tx):
            failures += 1

        # Test delete transaction
        txs = data.get('transactions', [])
        if txs:
            tid = txs[0]['id']
            r = client.get(f'/delete/{tid}', follow_redirects=True)
            deleted = not any(t['id'] == tid for t in load_data().get('transactions', []))
            if not ok('Delete transaction', deleted):
                failures += 1

        # Test add wallet
        r = client.post('/add_wallet', data={'name':'Wallet Test','initial':'50'}, follow_redirects=True)
        d = load_data()
        wallet_added = any(w['name'] == 'Wallet Test' for w in d.get('wallets', []))
        if not ok('Add wallet', wallet_added):
            failures += 1

        # Test transfer
        # Ensure wallets 1 and 2 exist
        r = client.post('/transfer', data={'from_wallet':'1','to_wallet':'2','amount':'10'}, follow_redirects=True)
        d = load_data()
        transfers = [t for t in d.get('transactions', []) if t.get('subcategory') == 'Transfer']
        if not ok('Transfer creates two transactions', len(transfers) >= 2):
            failures += 1
        # Check export CSV
        r = client.get('/export')
        csv_ok = r.status_code == 200 and 'text/csv' in r.content_type
        if not ok('Export CSV', csv_ok):
            failures += 1

        # Test recurring: add recurring, mark last_run old, then GET / to trigger
        r = client.post('/add_recurring', data={'description':'Rec Test','amount':'5','type':'expense','wallet_id':'1','category_id':'1','frequency':'daily'}, follow_redirects=True)
        d = load_data()
        if d.get('recurring'):
            d['recurring'][0]['last_run'] = '2000-01-01 00:00:00'
            save_data(d)
            r = client.get('/', follow_redirects=True)
            d2 = load_data()
            rec_tx = any('Rec Test' in t.get('description','') for t in d2.get('transactions', []))
            if not ok('Recurring processed and transaction created', rec_tx):
                failures += 1

    print('\nSummary:')
    if failures == 0:
        print('All tests passed')
        return 0
    else:
        print(f'{failures} test(s) failed')
        return 2

if __name__ == '__main__':
    exit(run_tests())

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify
from flask_wtf.csrf import CSRFProtect, CSRFError, generate_csrf
from werkzeug.security import check_password_hash
from config import Config
import sqlite3
import sqlite3 as _sq
import os
import time
import re
import secrets
import threading
import urllib.parse
import midtransclient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# ---------- CSRF ----------
csrf = CSRFProtect(app)

@app.after_request
def inject_csrf_token(response):
    response.set_cookie('csrf_token', generate_csrf(), samesite='Strict')
    return response

@app.errorhandler(CSRFError)
def csrf_error(e):
    flash('Permintaan tidak valid (CSRF error). Coba lagi.', 'error')
    return redirect(request.referrer or url_for('index'))

# ---------- MIDTRANS SETUP ----------
snap = midtransclient.Snap(
    is_production=app.config['MIDTRANS_IS_PRODUCTION'],
    server_key=app.config['MIDTRANS_SERVER_KEY'],
    client_key=app.config['MIDTRANS_CLIENT_KEY'],
)

# ---------- SHIELD DB ----------
_SHIELD_DB = os.path.join(os.path.dirname(__file__), 'shield.db')

def _shield_init():
    with _sq.connect(_SHIELD_DB) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS req_log (
            ip TEXT NOT NULL, ts REAL NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS blocked (
            ip TEXT PRIMARY KEY, until REAL NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS login_fail (
            ip TEXT NOT NULL, ts REAL NOT NULL)''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_req_ip ON req_log(ip)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_req_ts ON req_log(ts)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_loginfail_ip ON login_fail(ip)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_loginfail_ts ON login_fail(ts)')
        db.commit()

_shield_init()

RATE_LIMIT=80; RATE_WINDOW=60; LOGIN_LIMIT=5; LOGIN_WINDOW=300
BLOCK_DURATION=600; DDOS_LIMIT=200; DDOS_BLOCK=3600
TRUSTED_PROXIES={'127.0.0.1'}

def get_ip():
    if request.remote_addr in TRUSTED_PROXIES:
        fwd = request.headers.get('X-Forwarded-For','')
        if fwd: return fwd.split(',')[0].strip()
    return request.remote_addr

def is_blocked(ip):
    with _sq.connect(_SHIELD_DB) as db:
        db.row_factory = _sq.Row
        row = db.execute('SELECT until FROM blocked WHERE ip=?',(ip,)).fetchone()
        if row:
            if time.time() < row['until']: return True
            db.execute('DELETE FROM blocked WHERE ip=?',(ip,)); db.commit()
    return False

def block_ip(ip,duration):
    with _sq.connect(_SHIELD_DB) as db:
        db.execute('INSERT OR REPLACE INTO blocked (ip,until) VALUES (?,?)',(ip,time.time()+duration)); db.commit()

def check_rate_limit(ip):
    now=time.time()
    with _sq.connect(_SHIELD_DB) as db:
        db.row_factory=_sq.Row
        db.execute('DELETE FROM req_log WHERE ts<?',(now-RATE_WINDOW,)); db.commit()
        count=db.execute('SELECT COUNT(*) as c FROM req_log WHERE ip=?',(ip,)).fetchone()['c']
        if count>=DDOS_LIMIT: block_ip(ip,DDOS_BLOCK); return False
        if count>=RATE_LIMIT:  block_ip(ip,BLOCK_DURATION); return False
        db.execute('INSERT INTO req_log (ip,ts) VALUES (?,?)',(ip,now)); db.commit()
    return True

def check_login_limit(ip):
    now=time.time()
    with _sq.connect(_SHIELD_DB) as db:
        db.row_factory=_sq.Row
        db.execute('DELETE FROM login_fail WHERE ts<?',(now-LOGIN_WINDOW,)); db.commit()
        count=db.execute('SELECT COUNT(*) as c FROM login_fail WHERE ip=?',(ip,)).fetchone()['c']
        if count>=LOGIN_LIMIT: block_ip(ip,BLOCK_DURATION); return False,0
        return True,max(0,LOGIN_LIMIT-count)

def record_login_fail(ip):
    with _sq.connect(_SHIELD_DB) as db:
        db.execute('INSERT INTO login_fail (ip,ts) VALUES (?,?)',(ip,time.time())); db.commit()

def clear_login_fail(ip):
    with _sq.connect(_SHIELD_DB) as db:
        db.execute('DELETE FROM login_fail WHERE ip=?',(ip,)); db.commit()

def _scheduled_cleanup():
    while True:
        time.sleep(300)
        try:
            with _sq.connect(_SHIELD_DB) as db:
                now=time.time()
                db.execute('DELETE FROM req_log WHERE ts<?',(now-RATE_WINDOW,))
                db.execute('DELETE FROM login_fail WHERE ts<?',(now-LOGIN_WINDOW,))
                db.execute('DELETE FROM blocked WHERE until<?',(now,))
                db.commit()
        except Exception: pass

threading.Thread(target=_scheduled_cleanup,daemon=True).start()

# ---------- VALID PACKAGES ----------
VALID_PACKAGES = {
    'Mobile Legends': [
        {'diamond':'86 Diamond',  'price':'Rp 19.000','price_int':19000},
        {'diamond':'172 Diamond', 'price':'Rp 38.000','price_int':38000},
        {'diamond':'257 Diamond', 'price':'Rp 57.000','price_int':57000},
        {'diamond':'344 Diamond', 'price':'Rp 76.000','price_int':76000},
        {'diamond':'514 Diamond', 'price':'Rp 112.000','price_int':112000},
    ],
    'Free Fire': [
        {'diamond':'70 Diamond',  'price':'Rp 15.000','price_int':15000},
        {'diamond':'140 Diamond', 'price':'Rp 29.000','price_int':29000},
        {'diamond':'355 Diamond', 'price':'Rp 72.000','price_int':72000},
        {'diamond':'720 Diamond', 'price':'Rp 143.000','price_int':143000},
    ],
    'PUBG Mobile': [
        {'diamond':'60 UC',  'price':'Rp 15.000','price_int':15000},
        {'diamond':'120 UC', 'price':'Rp 29.000','price_int':29000},
        {'diamond':'325 UC', 'price':'Rp 75.000','price_int':75000},
        {'diamond':'660 UC', 'price':'Rp 149.000','price_int':149000},
    ],
    'Roblox': [
        {'diamond':'400 Robux',  'price':'Rp 55.000','price_int':55000},
        {'diamond':'800 Robux',  'price':'Rp 109.000','price_int':109000},
        {'diamond':'1700 Robux', 'price':'Rp 219.000','price_int':219000},
    ],
    'Genshin Impact': [
        {'diamond':'60 Primogem',  'price':'Rp 15.000','price_int':15000},
        {'diamond':'300 Primogem', 'price':'Rp 75.000','price_int':75000},
        {'diamond':'980 Primogem', 'price':'Rp 149.000','price_int':149000},
    ],
    'Honkai Star Rail': [
        {'diamond':'60 Stellar Jade',  'price':'Rp 15.000','price_int':15000},
        {'diamond':'300 Stellar Jade', 'price':'Rp 75.000','price_int':75000},
        {'diamond':'980 Stellar Jade', 'price':'Rp 149.000','price_int':149000},
    ],
}

VALID_PAYMENTS = {'Dana','GoPay','OVO','ShopeePay','Bank Transfer (BCA)','Indomaret / Alfamart','QRIS','Midtrans'}
VALID_GAMES    = set(VALID_PACKAGES.keys())

def validate_package(game,diamond,price):
    if game not in VALID_PACKAGES: return False
    for pkg in VALID_PACKAGES[game]:
        if pkg['diamond']==diamond and pkg['price']==price: return True
    return False

def get_price_int(game,diamond):
    if game not in VALID_PACKAGES: return 0
    for pkg in VALID_PACKAGES[game]:
        if pkg['diamond']==diamond: return pkg['price_int']
    return 0

def sanitize(text):
    if not text: return ''
    text=str(text).strip()
    text=re.sub(r'[<>"\'%;%()+&]','',text)
    return text[:200]

def format_rupiah(amount):
    return 'Rp {:,.0f}'.format(amount).replace(',','.')

# ---------- SECURITY MIDDLEWARE ----------
@app.before_request
def security_check():
    ip=get_ip()
    if is_blocked(ip): abort(429)
    if not check_rate_limit(ip): abort(429)

@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options']  = 'nosniff'
    response.headers['X-Frame-Options']          = 'DENY'
    response.headers['X-XSS-Protection']         = '1; mode=block'
    response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Permissions-Policy']        = 'geolocation=(), microphone=(), camera=()'
    response.headers['Content-Security-Policy']   = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://app.sandbox.midtrans.com https://app.midtrans.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "frame-src https://app.sandbox.midtrans.com https://app.midtrans.com; "
        "connect-src 'self' https://app.sandbox.midtrans.com https://app.midtrans.com; "
    )
    response.headers.pop('Server', None)
    return response

# ---------- ERROR HANDLERS ----------
@app.errorhandler(429)
def too_many_requests(e): return render_template('429.html'),429
@app.errorhandler(404)
def not_found(e): return render_template('404.html'),404
@app.errorhandler(403)
def forbidden(e): return render_template('403.html'),403

# ---------- MAIN DB ----------
def get_db():
    db=sqlite3.connect(app.config['DATABASE'])
    db.row_factory=sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db=get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT NOT NULL,
            user_id TEXT NOT NULL,
            server_id TEXT,
            diamond TEXT NOT NULL,
            price TEXT NOT NULL,
            price_int INTEGER NOT NULL DEFAULT 0,
            payment TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            token TEXT NOT NULL,
            midtrans_order_id TEXT,
            snap_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Tambah kolom baru kalau DB lama
        for col in [
            'ALTER TABLE orders ADD COLUMN price_int INTEGER NOT NULL DEFAULT 0',
            'ALTER TABLE orders ADD COLUMN midtrans_order_id TEXT',
            'ALTER TABLE orders ADD COLUMN snap_token TEXT',
        ]:
            try: db.execute(col)
            except Exception: pass
        db.commit()

GAMES = [
    {'name':'Mobile Legends','icon':'💎','price':'Rp 19.000','badge':'POPULAR','image':'ml.jpg'},
    {'name':'Free Fire',      'icon':'🔥','price':'Rp 15.000','badge':'HOT',    'image':'ff.jpg'},
    {'name':'PUBG Mobile',    'icon':'🎯','price':'Rp 15.000','badge':'',        'image':'pubg.jpg'},
    {'name':'Roblox',         'icon':'🟥','price':'Rp 55.000','badge':'',        'image':'Roblox.jpg'},
    {'name':'Genshin Impact', 'icon':'✨','price':'Rp 15.000','badge':'',        'image':'genshin.jpg'},
    {'name':'Honkai Star Rail','icon':'🌟','price':'Rp 15.000','badge':'',       'image':'honkai.jpg'},
]

# ---------- ROUTES ----------
@app.route('/')
def index(): return render_template('index.html',games=GAMES)

@app.route('/game')
def game(): return render_template('game.html',games=GAMES)

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    if request.method=='POST':
        game_name = sanitize(request.form.get('game',''))
        user_id   = sanitize(request.form.get('user_id',''))
        server_id = sanitize(request.form.get('server_id',''))
        diamond   = sanitize(request.form.get('diamond',''))
        price     = sanitize(request.form.get('price',''))
        payment   = sanitize(request.form.get('payment',''))

        if not game_name or not user_id or not diamond or not price or not payment:
            flash('Semua field harus diisi!','error')
            return redirect(url_for('index'))

        if game_name not in VALID_GAMES: abort(400)
        if payment not in VALID_PAYMENTS: abort(400)
        if not validate_package(game_name,diamond,price): abort(400)

        price_int   = get_price_int(game_name,diamond)
        order_token = secrets.token_urlsafe(32)
        # ID unik untuk Midtrans — harus unik per transaksi
        midtrans_order_id = f'TRUST-{int(time.time())}-{secrets.token_hex(4).upper()}'

        db  = get_db()
        cur = db.execute(
            'INSERT INTO orders (game,user_id,server_id,diamond,price,price_int,payment,token,midtrans_order_id) VALUES (?,?,?,?,?,?,?,?,?)',
            (game_name,user_id,server_id,diamond,price,price_int,payment,order_token,midtrans_order_id)
        )
        db.commit()
        order_id = cur.lastrowid
        session[f'order_token_{order_id}'] = order_token

        # ---------- BUAT SNAP TOKEN MIDTRANS ----------
        try:
            snap_param = {
                'transaction_details': {
                    'order_id':     midtrans_order_id,
                    'gross_amount': price_int,
                },
                'item_details': [{
                    'id':       f'{game_name}-{diamond}'.replace(' ','-'),
                    'price':    price_int,
                    'quantity': 1,
                    'name':     f'{diamond} - {game_name}'[:50],
                }],
                'customer_details': {
                    'first_name': user_id,
                    'email':      'customer@trusttopup.com',
                },
                'callbacks': {
                    'finish': url_for('status', order_id=order_id, token=order_token, _external=True),
                }
            }
            snap_response = snap.create_transaction(snap_param)
            snap_token    = snap_response['token']

            db.execute('UPDATE orders SET snap_token=? WHERE id=?',(snap_token,order_id))
            db.commit()
        except Exception as e:
            app.logger.error(f'Midtrans error: {e}')
            snap_token = None

        order = {
            'id':order_id,'game':game_name,'user_id':user_id,
            'server_id':server_id,'diamond':diamond,'price':price,
            'payment':payment,'token':order_token,
            'midtrans_order_id':midtrans_order_id,'snap_token':snap_token,
        }
        return render_template('checkout.html', order=order,
                               client_key=app.config['MIDTRANS_CLIENT_KEY'],
                               is_production=app.config['MIDTRANS_IS_PRODUCTION'])

    return redirect(url_for('index'))

# ---------- MIDTRANS WEBHOOK (Notification) ----------
@app.route('/midtrans/notification', methods=['POST'])
@csrf.exempt   # Midtrans server tidak kirim CSRF token
def midtrans_notification():
    try:
        notif = snap.transactions.notification(request.json or request.get_json(force=True))
        midtrans_order_id = notif.get('order_id','')
        transaction_status= notif.get('transaction_status','')
        fraud_status      = notif.get('fraud_status','')

        # Tentukan status order berdasarkan status Midtrans
        if transaction_status == 'capture':
            new_status = 'success' if fraud_status == 'accept' else 'pending'
        elif transaction_status == 'settlement':
            new_status = 'success'
        elif transaction_status in ('cancel','deny','expire'):
            new_status = 'failed'
        elif transaction_status == 'pending':
            new_status = 'pending'
        else:
            new_status = 'pending'

        db = get_db()
        db.execute('UPDATE orders SET status=? WHERE midtrans_order_id=?',(new_status,midtrans_order_id))
        db.commit()

        return jsonify({'status':'ok'}), 200
    except Exception as e:
        app.logger.error(f'Webhook error: {e}')
        return jsonify({'status':'error'}), 500

@app.route('/status')
def status():
    order_id   = sanitize(request.args.get('order_id',''))
    token      = request.args.get('token','')
    order=None

    if order_id and order_id.isdigit():
        saved_token = session.get(f'order_token_{order_id}')
        if not saved_token or not secrets.compare_digest(saved_token,token):
            abort(403)
        db  = get_db()
        row = db.execute('SELECT * FROM orders WHERE id=? AND token=?',(order_id,token)).fetchone()
        if row: order=dict(row)
    else:
        abort(403)

    status_val = order['status'] if order else 'pending'
    return render_template('status.html',status=status_val,order=order)

@app.route('/api/order-status/<int:order_id>')
def api_order_status(order_id):
    token=request.args.get('token','')
    saved_token=session.get(f'order_token_{order_id}')
    if not saved_token or not secrets.compare_digest(saved_token,token):
        return jsonify({'error':'forbidden'}),403
    db  = get_db()
    row = db.execute('SELECT status FROM orders WHERE id=? AND token=?',(order_id,token)).fetchone()
    if not row: return jsonify({'error':'not found'}),404
    return jsonify({'status':row['status']})

@app.route('/riwayat')
def riwayat():
    if not session.get('admin'): return redirect(url_for('login'))
    db   = get_db()
    rows = db.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 50').fetchall()
    transactions=[dict(r) for r in rows]
    for t in transactions:
        t['date']=t.get('created_at','')[:10]
    return render_template('riwayat.html',transactions=transactions)

@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('admin'): return redirect(url_for('admin'))
    ip=get_ip()
    if request.method=='POST':
        allowed,remaining=check_login_limit(ip)
        if not allowed:
            flash('Terlalu banyak percobaan login. Coba lagi dalam 5 menit.','error')
            return render_template('login.html')
        username=request.form.get('username','').strip()
        password=request.form.get('password','').strip()
        if not username or not password:
            flash('Username dan password harus diisi.','error')
            return render_template('login.html')
        if username==app.config['ADMIN_USER'] and check_password_hash(app.config['ADMIN_PASS'],password):
            session.clear(); session['admin']=True; session.permanent=True
            clear_login_fail(ip)
            return redirect(url_for('admin'))
        record_login_fail(ip)
        _,remaining=check_login_limit(ip)
        flash(f'Username atau password salah. Sisa percobaan: {remaining}','error')
        time.sleep(1)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); flash('Kamu berhasil logout.','success')
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('admin'): return redirect(url_for('login'))
    db     = get_db()
    orders = [dict(r) for r in db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()]
    total  = len(orders)
    success_count = sum(1 for o in orders if o['status']=='success')
    pending_count = sum(1 for o in orders if o['status']=='pending')
    failed_count  = sum(1 for o in orders if o['status']=='failed')
    revenue_total = sum(o.get('price_int',0) for o in orders if o['status']=='success')
    stats={'total_orders':total,'success':success_count,'pending':pending_count,
           'failed':failed_count,'revenue':format_rupiah(revenue_total)}
    return render_template('admin.html',orders=orders,stats=stats)

@app.route('/admin/order/<int:order_id>/update',methods=['POST'])
def admin_update_order(order_id):
    if not session.get('admin'): return redirect(url_for('login'))
    new_status=request.form.get('status','pending')
    if new_status not in ('pending','success','failed'): abort(400)
    db=get_db()
    db.execute('UPDATE orders SET status=? WHERE id=?',(new_status,order_id)); db.commit()
    flash(f'Status order #{order_id} diupdate ke {new_status.upper()}.','success')
    return redirect(url_for('admin'))

if __name__=='__main__':
    init_db()
    app.run(debug=False,host='0.0.0.0',port=5000)

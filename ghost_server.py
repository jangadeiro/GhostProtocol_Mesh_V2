import hashlib
import json
import time
import sqlite3
import base64
import random
import socket
import threading
import sys
import logging
import traceback
import os
from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for, Response, send_file
from uuid import uuid4
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from datetime import timedelta
from markupsafe import Markup 
from jinja2 import DictLoader, Template 

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GhostCloud")

# --- YAPILANDIRMA / CONFIGURATION ---
MINING_DIFFICULTY = 4
BLOCK_REWARD = 10
DB_FILE = os.path.join(os.getcwd(), "ghost_cloud_v2.db") 
GHOST_PORT = 5000
DOMAIN_EXPIRY_SECONDS = 15552000  
STORAGE_COST_PER_MB = 0.001       

app = Flask(__name__)
app.secret_key = 'cloud_super_secret_permanency_fix_2024_03_12_FINAL' 
app.permanent_session_lifetime = timedelta(days=7) 
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 

# --- VERİTABANI YÖNETİCİSİ (Stabil) ---
class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=20) 
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE, 
                    password TEXT, 
                    name TEXT, 
                    surname TEXT, 
                    phone TEXT, 
                    email TEXT, 
                    is_verified INTEGER DEFAULT 1, 
                    verification_code TEXT, 
                    wallet_private_key TEXT, 
                    wallet_public_key TEXT UNIQUE, 
                    balance REAL DEFAULT 50
                )
            ''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, proof INTEGER, previous_hash TEXT, block_hash TEXT)''')
            # 'block_index' transactions tablosunda hala güncel mi? Emin olmak için ekledim.
            cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, is_public INTEGER DEFAULT 1)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL, method TEXT)''')
            
            if cursor.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
                self.create_genesis_block(cursor)
                
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.critical(f"DB Init Error: {e}")

    def create_genesis_block(self, cursor):
        genesis_hash = hashlib.sha256(json.dumps({'index': 1, 'timestamp': time.time()}, sort_keys=True).encode()).hexdigest()
        cursor.execute("INSERT INTO blocks (block_index, timestamp, proof, previous_hash, block_hash) VALUES (?, ?, ?, ?, ?)",
                       (1, time.time(), 1, '0', genesis_hash))
    
    def hash(self, block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# --- BLOCKCHAIN/ASSET/USER MANAGER ---
class GhostChain:
    def __init__(self, db_manager):
        self.db = db_manager
    def last_block(self):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return block
    
    def new_transaction(self, sender, recipient, amount):
        conn = self.db.get_connection()
        tx_id = str(uuid4())
        
        # 0'dan gelen (ödül) ise bakiye kontrolü yapma
        if sender != "0":
            user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender,)).fetchone()
            if not user or user['balance'] < amount:
                conn.close()
                return False, "Yetersiz bakiye veya geçersiz gönderici / Insufficient balance or invalid sender"
        
        try:
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)", (tx_id, sender, recipient, amount, time.time()))
            
            # 🔥 KRİTİK DÜZELTME: Bakiye güncellemeleri transaction ile aynı anda yapılıyor.
            if sender != "0": # Normal transfer
                 conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (amount, sender))
                 conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (amount, recipient))
            elif sender == "0": # Madencilik ödülü
                 conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (amount, recipient))
                 
            conn.commit()
            return True, tx_id
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
            
    def mine_block(self, miner_address):
        last_block = self.last_block()
        if not last_block: return False, "Genesis block not found"
        
        # 1. Proof of Work (İspatı) yap
        proof = 0
        guess = f'{last_block["proof"]}0'.encode()
        while hashlib.sha256(guess).hexdigest()[:MINING_DIFFICULTY] != "0" * MINING_DIFFICULTY:
             proof += 1
             guess = f'{last_block["proof"]}{proof}'.encode()
             
        # 2. Ödül İşlemini Oluştur (Sender="0" ile)
        # 🔥 KRİTİK DÜZELTME 1.1: Madencilik ödülü new_transaction ile yansıtılıyor
        success, tx_id = self.new_transaction(sender="0", recipient=miner_address, amount=BLOCK_REWARD)
        if not success:
            logger.error(f"Madencilik ödülü işlemi oluşturulamadı: {tx_id}")
            return False, f"Ödül işlemi hatası: {tx_id}"

        conn = self.db.get_connection()
        pending_txs = conn.execute("SELECT tx_id, sender, recipient, amount FROM transactions WHERE block_index = 0").fetchall()
        
        new_block = {
            'index': last_block['block_index'] + 1,
            'timestamp': time.time(),
            'transactions': [dict(tx) for tx in pending_txs],
            'proof': proof,
            'previous_hash': last_block['block_hash'],
        }
        new_block_hash = self.db.hash(new_block)
        
        try:
            # 3. Bloku Zincire Ekle
            conn.execute("INSERT INTO blocks (block_index, timestamp, proof, previous_hash, block_hash) VALUES (?, ?, ?, ?, ?)",
                         (new_block['index'], new_block['timestamp'], new_block['proof'], new_block['previous_hash'], new_block_hash))
            
            # 4. İşlemleri Bloğa Bağla
            tx_ids = [tx['tx_id'] for tx in pending_txs]
            if tx_ids:
                q_marks = ', '.join('?' for _ in tx_ids)
                conn.execute(f"UPDATE transactions SET block_index = ? WHERE tx_id IN ({q_marks})", (new_block['index'], *tx_ids))
                
            conn.commit()
            return True, new_block['index']
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
            
    def get_full_chain(self):
        conn = self.db.get_connection()
        blocks = [dict(row) for row in conn.execute("SELECT * FROM blocks ORDER BY block_index ASC").fetchall()]
        assets = [dict(row) for row in conn.execute("SELECT * FROM assets").fetchall()]
        conn.close()
        for a in assets:
            if isinstance(a['content'], bytes): a['content'] = base64.b64encode(a['content']).decode('utf-8')
        return {'chain': blocks, 'assets': assets, 'length': len(blocks)}

class AssetManager:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def register_asset(self, owner_key, asset_type, name, content, is_file=False):
        
        if is_file:
            # content burada FileStorage nesnesi
            content_bytes = content.read()
            size = len(content_bytes)
        else:
            # content burada string
            content_bytes = content.encode('utf-8')
            size = len(content_bytes)
            
        creation_time = time.time()
        expiry_time = creation_time + DOMAIN_EXPIRY_SECONDS
        
        conn = self.db.get_connection()
        
        if asset_type == 'domain':
            # Domain Kayıt Kontrolü
            existing = conn.execute("SELECT expiry_time FROM assets WHERE name = ? AND type = 'domain'", (name,)).fetchone()
            if existing and existing['expiry_time'] > time.time():
                conn.close()
                return False, "Domain alınmış ve süresi dolmamış. / Domain taken and not expired."
            registration_fee = 1.0 
        else:
            # Diğer varlıklar için başlangıç ücreti/kuralı
            registration_fee = 0.01 
            
        user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (owner_key,)).fetchone()
        
        if not user or user['balance'] < registration_fee:
            conn.close()
            return False, f"Yetersiz bakiye (Kayıt ücreti: {registration_fee} GHOST). / Insufficient balance."
            
        try:
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (registration_fee, owner_key))
            
            conn.execute("INSERT OR REPLACE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, is_public) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (str(uuid4()), owner_key, asset_type, name, content_bytes, size, creation_time, expiry_time, 1))
            conn.commit()
            return True, "Başarılı / Success"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
            
    def update_asset_content(self, asset_id, owner_key, new_content):
        conn = self.db.get_connection()
        try:
            result = conn.execute("UPDATE assets SET content = ?, storage_size = ? WHERE asset_id = ? AND owner_pub_key = ?",
                                  (new_content.encode('utf-8'), len(new_content.encode('utf-8')), asset_id, owner_key))
            if result.rowcount == 0:
                conn.close()
                return False, "Varlık bulunamadı veya yetki yok."
            
            conn.commit()
            return True, "İçerik başarıyla güncellendi."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def delete_asset(self, asset_id, owner_key):
        conn = self.db.get_connection()
        conn.execute("DELETE FROM assets WHERE asset_id = ? AND owner_pub_key = ?", (asset_id, owner_key))
        conn.commit()
        conn.close()
        return True

class UserManager:
    def __init__(self, db):
        self.db = db
    def register(self, username, password, name, surname, phone, email):
        try:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            pem_priv = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()).decode('utf-8')
            pem_pub = private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
            conn = self.db.get_connection()
            conn.execute('INSERT INTO users (username, password, name, surname, phone, email, is_verified, wallet_private_key, wallet_public_key, balance) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 50)', 
                            (username, password, name, surname, phone, email, pem_priv, pem_pub))
            conn.commit()
            conn.close()
            return True, pem_pub
        except Exception as e:
            return False, str(e)

# --- UYGULAMA BAŞLATMA / APP INIT ---
db = DatabaseManager(DB_FILE) 
chain = GhostChain(db)
assets_mgr = AssetManager(db)
user_mgr = UserManager(db)

# --- LAYOUT (Temel HTML/CSS) ---
LAYOUT = """
<!doctype html>
<html>
<head>
    <title>GhostProtocol Cloud</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #222; color: #eee; padding: 20px; }
        .card { background: #333; padding: 15px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #444; }
        .success { color: #4caf50; } .fail { color: #f44336; }
        a { color: #2196f3; text-decoration: none; }
        input, button, textarea { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
        .action-button { background: #4caf50; color: white; border: none; padding: 10px; margin-top: 15px; cursor: pointer; border-radius: 5px; width: 50%; display: inline-block; text-align: center;}
        .action-button.register { background: #2196f3; margin-left: 10px; }
        .msg { padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .msg.ok { background: #1e4620; color: #7fbf7f; }
        .msg.err { background: #462222; color: #f7a5a5; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #555; padding: 8px; text-align: left; font-size: 0.9em; } 
        .full-width-key { word-wrap: break-word; font-size: 0.7em; }
        .debug-info { color: #ff0; font-size: 0.8em; margin-top: 10px; padding: 5px; border: 1px dashed #555; }
        .flex-container { display: flex; justify-content: space-between; gap: 20px; }
        .flex-item { flex: 1; }
    </style>
</head>
<body>
    <h2>👻 GhostProtocol Cloud Server</h2>
    <div class="card">
        Durum / Status: <span class="{{ 'success' if internet else 'fail' }}">{{ 'ONLINE' if internet else 'OFFLINE' }}</span>
        | Peers: {{ peers|length }}
        {% if session.get('username') %}
            | 👤 {{ session['username'] }} | 💰 {{ session.get('balance', 0)|round(4) }} GHOST
            <br>
            <a href="{{ url_for('dashboard') }}">Panel / Dashboard</a> | 
            <a href="{{ url_for('mine') }}">Madencilik / Mining</a> | 
            <a href="{{ url_for('search_engine') }}">🔍 Ghost Arama / Search</a> | 
            <a href="{{ url_for('logout') }}">Çıkış / Logout</a>
        {% else %}
             <br><a href="{{ url_for('login') }}">Giriş / Login</a> | <a href="{{ url_for('register') }}">Kayıt / Register</a>
        {% endif %}
    </div>
    
    {% block content %}{% endblock %} 

</body>
</html>
"""
# --- CONTEXT İŞLEMCİ (Stabil) ---
@app.context_processor
def inject_globals():
    try:
        conn = db.get_connection()
        peers = conn.execute("SELECT * FROM mesh_peers").fetchall()
        conn.close()
        internet = True
    except:
        internet = False
        peers = []
    
    if session.get('pub_key'):
        try:
            conn = db.get_connection()
            # Bakiye güncellemeyi her request'te yapıyoruz
            user_data = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (session['pub_key'],)).fetchone()
            conn.close()
            if user_data:
                session['balance'] = user_data['balance']
        except Exception as e:
            logger.error(f"Bakiye güncellenirken hata: {e}")
            
    return dict(internet=internet, peers=peers, url_for=url_for)


# --- ROTALAR / ROUTES ---

@app.route('/')
def home():
    if session.get('username'):
        return redirect(url_for('dashboard'))
        
    return render_template_string("""
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>Blok Zinciri Omurgası / Blockchain Backbone</h3>
                <p>Bu sunucu, GhostProtocol ağının ana veri omurgasını oluşturur. Mesh düğümleri ve diğer sunucular buradan senkronize olur.</p>
                <p>Erişime devam etmek için lütfen **Giriş Yapın** veya bir **Hesap Oluşturun**.</p>
                
                <a href="{{ url_for('login') }}" class="action-button">Giriş Yap / Login</a>
                <a href="{{ url_for('register') }}" class="action-button register">Kayıt Ol / Register</a>
            </div>
        {% endblock %}
    """) 


@app.route('/chain', methods=['GET'])
def full_chain_export():
    response = chain.get_full_chain()
    return jsonify(response), 200

# -------------------------------------------------------------
# 2. ÖZELLİK: DASHBOARD VE DOMAIN YÖNETİMİ GELİŞTİRME
# -------------------------------------------------------------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('username'): 
        return redirect(url_for('login'))

    msg = ""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'register_domain':
            name = request.form['name']
            data = request.form['data']
            success, response_text = assets_mgr.register_asset(session['pub_key'], 'domain', name, data, is_file=False)
            msg = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı' if success else 'Hata'}: {response_text}</div>"
        
        elif action == 'upload_media':
            if 'file' not in request.files:
                 msg = "<div class='msg err'>Dosya alanı boş.</div>"
            else:
                file = request.files['file']
                file_name = request.form.get('media_name', file.filename)
                
                # Basit MIME tipi kontrolü
                mime_type = file.mimetype
                asset_type = 'file'
                if mime_type.startswith('image'): asset_type = 'image'
                elif mime_type.startswith('video'): asset_type = 'video'
                elif mime_type.startswith('audio'): asset_type = 'audio'
                
                success, response_text = assets_mgr.register_asset(session['pub_key'], asset_type, file_name, file, is_file=True)
                msg = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı' if success else 'Hata'}: {response_text}</div>"
        
        elif action == 'delete_asset':
            assets_mgr.delete_asset(request.form['id'], session['pub_key'])
            msg = "<div class='msg ok'>Varlık silindi / Asset deleted</div>"
            
    conn = db.get_connection()
    my_assets = conn.execute("SELECT * FROM assets WHERE owner_pub_key = ? ORDER BY creation_time DESC", (session['pub_key'],)).fetchall()
    transactions = conn.execute("SELECT * FROM transactions WHERE sender = ? OR recipient = ? ORDER BY timestamp DESC LIMIT 10", (session['pub_key'], session['pub_key'])).fetchall()
    user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (session['pub_key'],)).fetchone()
    if user:
        session['balance'] = user['balance']
    conn.close()

    data = {
        'msg': Markup(msg), 
        'pub_key': session['pub_key'],
        'balance': session.get('balance', 0),
        'assets': [dict(a) for a in my_assets], 
        'transactions': [dict(tx) for tx in transactions], 
        'username': session['username'],
        'now': time.time(),
        'domain_expiry_seconds': DOMAIN_EXPIRY_SECONDS,
        'storage_cost_per_mb': STORAGE_COST_PER_MB,
    }
    
    dashboard_template = """
    {% extends "base.html" %} 
    {% block content %}
    <div class="card">
        {{ msg }}
        <h3>💳 Cüzdanım / My Wallet</h3>
        <p><strong>Genel Anahtar (Public Key):</strong></p>
        <p class="full-width-key">{{ pub_key }} </p>
        <p><strong>Bakiye / Balance:</strong> {{ balance|round(4) }} GHOST</p>
    </div>
    
    <div class="flex-container">
        <div class="card flex-item">
            <h3>💾 .ghost Domain Kayıt (6 Ay)</h3>
            <form method="post">
                <input type="hidden" name="action" value="register_domain">
                <input name="name" placeholder="site.ghost (Kayıt Ücreti 1 GHOST)" required>
                <textarea name="data" rows="5" placeholder="HTML Site İçeriği" required></textarea>
                <button>Tescil Et ve Yayınla</button>
            </form>
        </div>
        
        <div class="card flex-item">
            <h3>🖼️ Medya Yükle (Görsel/Video/Ses)</h3>
            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="action" value="upload_media">
                <input type="text" name="media_name" placeholder="Varlık Adı (örnek: fotom.png)" required>
                <input type="file" name="file" required>
                <button>Yükle (Ücret: 0.01 GHOST)</button>
                <p style="font-size:0.8em; color: #888;">Yüklenen içeriğe, domain HTML içeriğinde <a href="{{ url_for('view_asset', asset_id='[asset_id]') }}" target="_blank">{{ url_for('view_asset', asset_id='[asset_id]') }}</a> linki ile erişebilirsiniz.</p>
            </form>
        </div>
    </div>

    <div class="card">
        <h3>Kayıtlı Varlıklarım (6 Aylık Döngü)</h3>
        <table>
            <tr>
                <th>Ad / ID</th>
                <th>Tip</th>
                <th>Boyut</th>
                <th>Kalan Süre</th>
                <th>Aylık Ücret</th>
                <th>Durum</th>
                <th>İşlem</th>
            </tr>
            {% for a in assets %}
                {% set days_left = ((a.expiry_time - now) / 86400) | int %}
                {% set status = "AKTİF" if days_left > 0 else "SÜRESİ DOLDU (Özel)" %}
                {% set size_mb = a.storage_size / (1024 * 1024) %}
                {% set fee = size_mb * storage_cost_per_mb %}
            <tr>
                <td>{{ a.name }} <br><span style="font-size: 0.7em;">ID: {{ a.asset_id[:8] }}...</span></td>
                <td>{{ a.type | upper }}</td>
                <td>{{ "%.2f"|format(size_mb) }} MB</td>
                <td style="color:{{ '#f44336' if days_left < 30 else '#4caf50' }}">{{ days_left }} Gün</td>
                <td>{{ "%.6f"|format(fee) }} GHOST/Ay</td>
                <td>{{ status }}</td>
                <td>
                    <a href="{{ url_for('view_asset', asset_id=a.asset_id) }}" target="_blank">Gör</a> | 
                    {% if a.type == 'domain' %}
                       <a href="{{ url_for('edit_asset', asset_id=a.asset_id) }}">✏️ Düzenle</a> | 
                    {% endif %}
                    <form method="post" style="display:inline">
                        <input type="hidden" name="action" value="delete_asset">
                        <input type="hidden" name="id" value="{{ a.asset_id }}">
                        <button style="color:#f44336; background:none; border:none; padding:0; cursor:pointer; width:auto;">Sil</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h3>Son İşlemlerim</h3>
        <ul>
            {% for tx in transactions %}
                {% set tx_type = "" %}
                {% set amount_display = "" %}
                {% if tx.sender == '0' %}
                    {% set tx_type = "✅ Madencilik Ödülü" %}
                    {% set amount_display = "+%.4f GHOST"|format(tx.amount) %}
                {% elif tx.sender == pub_key %}
                    {% set tx_type = "➡️ Gönderilen" %}
                    {% set amount_display = "-%.4f GHOST"|format(tx.amount) %}
                {% else %}
                    {% set tx_type = "⬅️ Alınan" %}
                    {% set amount_display = "+%.4f GHOST"|format(tx.amount) %}
                {% endif %}
            <li>
                {{ tx_type }}: <strong>{{ amount_display }}</strong> (Blok: #{{ tx.block_index }}, Kime/Kimden: {{ tx.recipient[:10] }}...{{ tx.sender[:10] }})
            </li>
            {% endfor %}
        </ul>
    </div>
    
    <div class="debug-info">
        Oturum Durumu: AKTİF. Kullanıcı: {{ username }}
    </div>
    {% endblock %}
    """
    
    return render_template_string(dashboard_template, **data)

# Yeni Rota: Varlık Düzenleme (Sadece Domainler İçin)
@app.route('/edit_asset/<asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    if not session.get('username'): return redirect(url_for('login'))
        
    conn = db.get_connection()
    asset = conn.execute("SELECT * FROM assets WHERE asset_id = ? AND owner_pub_key = ?", (asset_id, session['pub_key'])).fetchone()
    conn.close()
    
    if not asset or asset['type'] != 'domain':
        return redirect(url_for('dashboard'))

    msg = ""
    current_content = asset['content'].decode('utf-8')

    if request.method == 'POST':
        new_content = request.form['content']
        success, response_text = assets_mgr.update_asset_content(asset_id, session['pub_key'], new_content)
        if success:
            current_content = new_content
            msg = "<div class='msg ok'>İçerik Başarıyla Güncellendi.</div>"
        else:
            msg = f"<div class='msg err'>Güncelleme Hatası: {response_text}</div>"
            
    edit_template = """
    {% extends "base.html" %} 
    {% block content %}
        <div class="card">
            <h3>{{ asset.name }} Domain İçeriğini Düzenle</h3>
            {{ msg | safe }}
            <form method='post'>
                <p>Domain adı: <strong>{{ asset.name }}</strong> (ID: {{ asset.asset_id[:8] }}...)</p>
                <textarea name="content" rows="15" placeholder="HTML İçeriği" required>{{ current_content }}</textarea>
                <button>İçeriği Kaydet</button>
            </form>
            <p><a href="{{ url_for('dashboard') }}">Geri Dön</a></p>
        </div>
    {% endblock %}
    """
    
    return render_template_string(edit_template, asset=dict(asset), current_content=current_content, msg=Markup(msg))


# -------------------------------------------------------------
# 4. ÖZELLİK: GHOST ARAMA MOTORU
# -------------------------------------------------------------
@app.route('/search', methods=['GET'])
def search_engine():
    query = request.args.get('q', '').lower()
    conn = db.get_connection()
    
    if query:
        # Domain adına göre basit arama
        search_query = f"%{query}%"
        results = conn.execute("SELECT * FROM assets WHERE type = 'domain' AND name LIKE ? AND expiry_time > ?", (search_query, time.time())).fetchall()
    else:
        # Tüm aktif domainleri listele
        results = conn.execute("SELECT * FROM assets WHERE type = 'domain' AND expiry_time > ? ORDER BY creation_time DESC", (time.time(),)).fetchall()
        
    conn.close()
    
    search_template = """
    {% extends "base.html" %} 
    {% block content %}
        <div class="card">
            <h3>🔍 Ghost Arama Motoru (Aktif Domainler)</h3>
            <form method='get'>
                <input name='q' placeholder='Domain Ara (ör: blog.ghost)' value="{{ query }}">
                <button>Ara</button>
            </form>
        </div>
        
        <div class="card">
            <h4>{% if query %}Sonuçlar ({{ results | length }}){% else %}En Son Aktif Domainler{% endif %}</h4>
            <ul>
            {% for asset in results %}
                <li>
                    <strong><a href="{{ url_for('view_asset', asset_id=asset.asset_id) }}" target="_blank">{{ asset.name }}</a></strong> 
                    <span style="font-size: 0.8em; color: #aaa;">(Sahibi: {{ asset.owner_pub_key[:10] }}...)</span>
                    {% if asset.content %}
                        <p style="font-size: 0.9em; color: #bbb; margin: 5px 0 0 10px;">{{ asset.content[:150] | striptags }}...</p>
                    {% endif %}
                </li>
            {% endfor %}
            {% if not results %}
                <li>{% if query %}Aramanıza uygun aktif domain bulunamadı.{% else %}Henüz aktif domain yok.{% endif %}</li>
            {% endif %}
            </ul>
        </div>
    {% endblock %}
    """
    
    return render_template_string(search_template, results=[dict(r) for r in results], query=query)


# --- AUTH & DİĞER ROTALAR ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        success, response = user_mgr.register(
            request.form['username'], 
            request.form['password'], 
            request.form['name'], 
            request.form['surname'], 
            request.form['phone'], 
            request.form['email']
        )
        if success:
            logger.info(f"Yeni kullanıcı başarıyla kaydedildi: {request.form['username']}")
            
            return render_template_string("""
                {% extends "base.html" %} 
                {% block content %}
                    <div class='msg ok card'>
                        <h3>🎉 Kayıt Başarılı!</h3>
                        <p>Hesabınız başarıyla oluşturuldu. Lütfen giriş yapmak için aşağıdaki butona tıklayın.</p>
                        <a href="{{ url_for('login') }}"><button class="action-button" style="width:100%; margin: 15px 0;">Giriş Yap / Login</button></a>
                    </div>
                {% endblock %}
            """)
        
        return render_template_string("""
            {% extends "base.html" %} 
            {% block content %}
                <div class='msg err card'>Kayıt Hata: {{ response }}. Lütfen farklı bir kullanıcı adı deneyin. <a href="{{ url_for('register') }}">Geri</a></div>
            {% endblock %}
        """, response=response) 
    
    return render_template_string("""
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>Kayıt / Register</h3>
                <form method='post'>
                    <input name='username' placeholder='Kullanıcı Adı / Username' required>
                    <input name='password' type='password' placeholder='Şifre / Password' required>
                    <input name='name' placeholder='Ad / First Name' required>
                    <input name='surname' placeholder='Soyad / Last Name' required>
                    <input name='phone' placeholder='Tel / Phone'>
                    <input name='email' placeholder='Email' required>
                    <button>Kaydol / Register</button>
                </form>
            </div>
        {% endblock %}
    """)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = db.get_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (request.form['username'], request.form['password'])).fetchone()
        
        if user:
            session.permanent = True 
            session['username'] = user['username']
            session['pub_key'] = user['wallet_public_key']
            
            user_data_full = conn.execute("SELECT balance FROM users WHERE username = ?", (user['username'],)).fetchone()
            conn.close()
            session['balance'] = user_data_full['balance']
            
            logger.info(f"Kullanıcı {user['username']} için oturum başarıyla ayarlandı.")
            
            return render_template_string("""
                {% extends "base.html" %} 
                {% block content %}
                    <div class='msg ok card'>
                        <h3>🎉 Başarılı Giriş!</h3>
                        <p><strong>{{ session['username'] }}</strong> olarak giriş yaptınız. Artık paneli açabilirsiniz.</p>
                        <a href="{{ url_for('dashboard') }}"><button class="action-button" style="width:100%; margin: 15px 0;">Paneli Aç / Go to Dashboard</button></a>
                    </div>
                {% endblock %}
            """)
        
        conn.close()
        return render_template_string("""
            {% extends "base.html" %} 
            {% block content %}
                <div class='msg err card'>Giriş Hatalı <a href="{{ url_for('login') }}">Tekrar Dene</a></div>
            {% endblock %}
        """)
    
    return render_template_string("""
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>Giriş / Login</h3>
                <form method='post'>
                    <input name='username' placeholder='Kullanıcı Adı / Username' required>
                    <input name='password' type='password' placeholder='Şifre / Password' required>
                    <button>Giriş / Login</button>
                </form>
            </div>
        {% endblock %}
    """)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
    
@app.route('/mine')
def mine():
    if not session.get('username'): return redirect(url_for('login'))
    
    success, response = chain.mine_block(session['pub_key'])
    
    conn = db.get_connection()
    # Madencilikten sonra bakiyeyi güncellemek için tekrar çekiyoruz.
    user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (session['pub_key'],)).fetchone()
    session['balance'] = user['balance']
    conn.close()
    
    return render_template_string("""
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <div class='msg {{'ok' if success else 'err'}}'>Madencilik {{ 'Başarılı' if success else 'Başarısız' }}: {{ response }}</div>
                <h3>Madencilik / Mining</h3>
                <p>Son Blok: #{{ last_block.block_index if last_block else 'N/A'}}</p>
                <a href="{{ url_for('dashboard') }}">Cüzdana Geri Dön</a>
            </div>
        {% endblock %}
    """, success=success, response=response, last_block=chain.last_block()) 

@app.route('/view_asset/<asset_id>')
def view_asset(asset_id):
    if not asset_id: return "400: ID gerekli", 400
        
    conn = db.get_connection()
    asset = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    conn.close()
    
    if not asset: return "404: Bulunamadı", 404
        
    content_bytes = asset['content']
    asset_type = asset['type']
    
    if asset_type == 'domain' and asset['expiry_time'] < time.time():
        if asset['owner_pub_key'] != session.get('pub_key'):
            return "403: Domain süresi doldu ve yayınlanmıyor.", 403
        pass 

    if asset_type == 'domain':
        # Domainler HTML olarak yayınlanır
        return Response(content_bytes, mimetype='text/html')
    
    elif asset_type in ['image', 'video', 'audio', 'file']:
        # Medya/Dosya varlıkları doğrudan Response nesnesi ile yayınlanır
        mime_type = 'application/octet-stream'
        if asset['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif')): mime_type = f'image/{asset["name"].split(".")[-1]}'
        elif asset['name'].lower().endswith(('.mp4', '.webm')): mime_type = 'video/mp4'
        elif asset['name'].lower().endswith(('.mp3', '.wav')): mime_type = 'audio/mpeg'
        
        # Binary içeriği döndürür
        return Response(content_bytes, mimetype=mime_type)

    return render_template_string("""
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>'{{ asset.name }}' Görüntüleniyor</h3>
                <p>Tip: {{ asset.type }} (İkili dosya). Bu içerik doğrudan tarayıcıda görüntülenemez.</p>
                <p><a href="{{ url_for('dashboard') }}">Geri Dön</a></p>
            </div>
        {% endblock %}
    """, asset=dict(asset))


if __name__ == '__main__':
    # Jinja2 yükleyicisi LAYOUT değişkenini "base.html" olarak tanıyan DictLoader ile değiştiriliyor.
    app.jinja_env.loader = DictLoader({'base.html': LAYOUT})
    
    print("--- GHOST CLOUD SUNUCUSU BAŞLATILIYOR / GHOST CLOUD SERVER STARTING ---")
    print("\n✅ **TÜM KRİTİK DÜZELTMELER VE YENİ ÖZELLİKLER UYGULANDI:**")
    print("1. Madencilik ödülü (BLOCK_REWARD) bakiye güncellemesi artık düzgün çalışıyor.")
    print("2. Dashboard'a domainler için düzenleme butonu eklendi ve /edit_asset rotası oluşturuldu.")
    print("3. Dashboard'a resim/video/ses (Medya) yükleme formu eklendi.")
    print("4. /search rotası ile .ghost domain arama motoru özelliği eklendi.")
    print("Veritabanı: ghost_cloud_v2.db (Kalıcı)\n")
    
    app.run(host='0.0.0.0', port=GHOST_PORT, debug=True, use_reloader=False)

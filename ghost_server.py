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
from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for, Response
from uuid import uuid4
from werkzeug.utils import secure_filename

# --- LOGLAMA ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GhostNode")

# --- KRİPTO KÜTÜPHANESİ KONTROLÜ ---
try:
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import serialization, hashes
    CRYPTO_AVAILABLE = True
except ImportError as e:
    CRYPTO_AVAILABLE = False
    logger.error(f"Kripto Kütüphanesi Hatası: {e}")

# --- YAPILANDIRMA ---
MINING_DIFFICULTY = 4  # Madencilik Zorluğu
BLOCK_REWARD = 10      # Madencilik Ödülü
DB_FILE = os.path.join(os.getcwd(), "ghost_v5.db")
MESH_PORT = 9999
GHOST_PORT = 5000
GHOST_BEACON_MSG = b"GHOST_PROTOCOL_NODE_HERE"

app = Flask(__name__)
app.secret_key = "super_secret_mesh_key"

# --- VERİTABANI YÖNETİCİSİ ---
class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT, surname TEXT, phone TEXT, email TEXT, is_verified INTEGER DEFAULT 0, verification_code TEXT, wallet_private_key TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 0)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, proof INTEGER, previous_hash TEXT, block_hash TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, last_payment_time REAL, status TEXT DEFAULT 'active')''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL, method TEXT)''')
            
            if cursor.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
                self.create_genesis_block(cursor)
                
            conn.commit()
            conn.close()
        except Exception as e:
            logger.critical(f"DB Init Hatası: {e}")

    def create_genesis_block(self, cursor):
        genesis = {
            'index': 1,
            'timestamp': time.time(),
            'proof': 1,
            'previous_hash': '1',
            'transactions': [],
        }
        genesis_hash = self.hash(genesis)
        
        cursor.execute("INSERT INTO blocks (block_index, timestamp, proof, previous_hash, block_hash) VALUES (?, ?, ?, ?, ?)",
                       (genesis['index'], genesis['timestamp'], genesis['proof'], genesis['previous_hash'], genesis_hash))

    def hash(self, block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# --- MESH MANAGER ---
class MeshManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.running = True

    def start(self):
        t1 = threading.Thread(target=self.listen_udp_broadcast, daemon=True)
        t2 = threading.Thread(target=self.broadcast_presence, daemon=True)
        t1.start()
        t2.start()

    def register_peer(self, ip, method="WIFI"):
        try:
            conn = self.db.get_connection()
            conn.execute("INSERT OR REPLACE INTO mesh_peers (ip_address, last_seen, method) VALUES (?, ?, ?)", 
                         (ip, time.time(), method))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def broadcast_presence(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self.running:
            try:
                msg = f"{GHOST_BEACON_MSG.decode()}|{GHOST_PORT}|0.0.0.0".encode()
                sock.sendto(msg, ('<broadcast>', MESH_PORT))
                time.sleep(5)
            except Exception:
                time.sleep(10)

    def listen_udp_broadcast(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', MESH_PORT))
        except Exception as e:
            logger.error(f"UDP Bağlanamadı: {e}")
            return

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                decoded = data.decode().split('|')
                if decoded[0] == GHOST_BEACON_MSG.decode() and len(decoded) == 3:
                    peer_ip = addr[0]
                    peer_port = decoded[1]
                    self.register_peer(f"http://{peer_ip}:{peer_port}", "WIFI")
            except Exception:
                pass


# --- BLOCKCHAIN/MINING MANTIĞI ---
class GhostChain:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def last_block(self):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return block

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    def valid_proof(self, last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:MINING_DIFFICULTY] == "0" * MINING_DIFFICULTY

    def mine_block(self, miner_address):
        last_block = self.last_block()
        if not last_block:
             return False, "Genesis blok bulunamadı"

        last_proof = last_block['proof']
        proof = self.proof_of_work(last_proof)

        self.new_transaction(sender="0", recipient=miner_address, amount=BLOCK_REWARD)
        
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
            conn.execute("INSERT INTO blocks (block_index, timestamp, proof, previous_hash, block_hash) VALUES (?, ?, ?, ?, ?)",
                         (new_block['index'], new_block['timestamp'], new_block['proof'], new_block['previous_hash'], new_block_hash))
            tx_ids = [tx['tx_id'] for tx in pending_txs]
            if tx_ids:
                q_marks = ', '.join('?' for _ in tx_ids)
                conn.execute(f"UPDATE transactions SET block_index = ? WHERE tx_id IN ({q_marks})", (new_block['index'], *tx_ids))
            
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (BLOCK_REWARD, miner_address))
            conn.commit()
            return True, new_block['index']
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def new_transaction(self, sender, recipient, amount):
        conn = self.db.get_connection()
        tx_id = str(uuid4())
        
        if sender != "0":
            user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender,)).fetchone()
            if not user or user['balance'] < amount:
                conn.close()
                return False, "Yetersiz bakiye veya geçersiz gönderici"
                
        try:
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (tx_id, sender, recipient, amount, time.time()))
            conn.commit()
            return True, tx_id
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def send_ghostcoin(self, sender_key, recipient_key, amount):
        if amount <= 0: return False, "Miktar 0'dan büyük olmalı"
        
        conn = self.db.get_connection()
        sender_user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender_key,)).fetchone()
        recipient_user = conn.execute("SELECT * FROM users WHERE wallet_public_key = ?", (recipient_key,)).fetchone()
        conn.close()
        
        if not sender_user or sender_user['balance'] < amount:
            return False, "Yetersiz bakiye"
        if not recipient_user:
            return False, "Alıcı cüzdan adresi geçersiz"

        success, tx_id = self.new_transaction(sender_key, recipient_key, amount)
        if success:
            conn = self.db.get_connection()
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (amount, sender_key))
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (amount, recipient_key))
            conn.commit()
            conn.close()
            return True, f"İşlem başarılı, TX ID: {tx_id}. Yeni blokta onaylanacak."
        
        return False, tx_id

# --- DOMAIN/VARLIK YÖNETİMİ ---
class StorageBlockchain:
    def __init__(self, db_manager):
        self.db = db_manager

    def mint_domain(self, owner_pub_key, domain_name, domain_data):
        if not domain_name.endswith('.ghost'):
            return False, "Domain .ghost uzantılı olmalıdır."

        content = base64.b64encode(domain_data.encode('utf-8')).decode('utf-8')
        
        conn = self.db.get_connection()
        try:
            conn.execute('INSERT INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, last_payment_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                         (str(uuid4()), owner_pub_key, 'domain', domain_name, content, len(domain_data), time.time(), time.time()))
            conn.commit()
            return True, f"{domain_name} başarıyla kaydedildi."
        except sqlite3.IntegrityError:
            return False, "Bu domain adı zaten kayıtlı."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
            
    def update_asset(self, asset_id, owner_pub_key, new_content):
        conn = self.db.get_connection()
        asset = conn.execute("SELECT type, content FROM assets WHERE asset_id = ? AND owner_pub_key = ?", (asset_id, owner_pub_key)).fetchone()
        
        if not asset:
            conn.close()
            return False, "Varlık bulunamadı veya yetkiniz yok."

        try:
            # Domain içeriği (HTML/XML) güncelleniyor.
            if asset['type'] == 'domain':
                content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
            else:
                # Şu an için sadece domain'leri düzenliyoruz. Diğer türler için orijinal içerik korunmalı.
                content_b64 = asset['content']
                if new_content: # Eğer yeni bir içerik geldiyse (ki gelmemeli, sadece domain destekliyoruz)
                     pass 
            
            size = len(content_b64)
            
            conn.execute("UPDATE assets SET content = ?, storage_size = ?, creation_time = ? WHERE asset_id = ?",
                         (content_b64, size, time.time(), asset_id))
            conn.commit()
            return True, "Varlık içeriği başarıyla güncellendi."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def upload_asset(self, user_pub_key, mime_type, name, file_content_b64):
        try:
            size = len(file_content_b64)
            asset_type = 'file'
            if mime_type.startswith('image/'): asset_type = 'image'
            elif mime_type.startswith('video/'): asset_type = 'video'
            elif mime_type.startswith('audio/'): asset_type = 'audio'

            conn = self.db.get_connection()
            conn.execute('INSERT INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, last_payment_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                         (str(uuid4()), user_pub_key, asset_type, name, file_content_b64, size, time.time(), time.time()))
            conn.commit()
            conn.close()
            return True, "OK"
        except Exception as e:
            return False, str(e)
        
    def clone_asset(self, asset_id, new_owner_key):
        conn = self.db.get_connection()
        original = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
        conn.close()
        if original:
            return self.upload_asset(new_owner_key, original['type'], "Copy_" + original['name'], original['content'])
        return False, "Not Found"

# --- USER MANAGER ---
class UserManager:
    def __init__(self, db):
        self.db = db
    
    def register(self, username, password, name, surname, phone, email):
        if not CRYPTO_AVAILABLE: return False, "Kripto Modülü Yok"
        try:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            pem_priv = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()).decode('utf-8')
            pem_pub = private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
            verification_code = str(random.randint(100000, 999999))
            
            conn = self.db.get_connection()
            conn.execute('INSERT INTO users (username, password, name, surname, phone, email, verification_code, wallet_private_key, wallet_public_key, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 50)', 
                            (username, password, name, surname, phone, email, verification_code, pem_priv, pem_pub))
            conn.commit()
            conn.close()
            print(f"--- KOD: {verification_code} ---")
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def verify_user(self, username, code):
        conn = self.db.get_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and user['verification_code'] == code:
            conn = self.db.get_connection()
            conn.execute("UPDATE users SET is_verified = 1 WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            return True
        return False
        
# --- INIT ---
db = DatabaseManager(DB_FILE)
ghost_chain = GhostChain(db)
storage_chain = StorageBlockchain(db)
mesh = MeshManager(db)
user_mgr = UserManager(db)

# --- GLOBAL HATA YAKALAYICI VE CONTEXT ---
@app.errorhandler(500)
def internal_error(exception):
    return f"<h1>500 Sunucu Hatası</h1><pre>{traceback.format_exc()}</pre>", 500

@app.errorhandler(404)
def not_found(exception):
    return "<h1>404 Sayfa Bulunamadı</h1>", 404

@app.context_processor
def inject_vars():
    peers = []
    internet = False
    try:
        conn = db.get_connection()
        peers = conn.execute("SELECT * FROM mesh_peers WHERE last_seen > ?", (time.time() - 300,)).fetchall()
        conn.close()
        socket.create_connection(("8.8.8.8", 53), timeout=0.1)
        internet = True
    except:
        pass
    return dict(internet=internet, peers=peers)

# --- LAYOUT HTML (Tab CSS Eklendi) ---
LAYOUT = """
<!doctype html>
<html lang="tr">
<head>
    <title>GhostProtocol Cloud</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #222; color: #eee; padding: 20px; }
        .card { background: #333; padding: 15px; margin-bottom: 15px; border: 1px solid #444; border-radius: 5px; }
        a { color: #4dabf7; text-decoration: none; }
        input, button, select, textarea { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; }
        .success { color: #28a745; } .fail { color: #dc3545; }
        .msg { padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .msg.ok { background: #1e4620; color: #7fbf7f; }
        .msg.err { background: #462222; color: #f7a5a5; }
        .full-width-key { word-wrap: break-word; font-size: 0.7em; }

        /* Tab Stilleri */
        .tabs { overflow: hidden; border-bottom: 1px solid #444; margin-bottom: 15px; }
        .tabs button { 
            background-color: inherit; float: left; border: none; outline: none; 
            cursor: pointer; padding: 14px 16px; transition: 0.3s; color: #eee;
            width: auto; margin: 0; 
        }
        .tabs button:hover { background-color: #444; }
        .tabs button.active { background-color: #333; border-bottom: 3px solid #4dabf7; }
        .tabcontent { display: none; padding: 6px 0; border-top: none; }
    </style>
    <script>
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].style.display = "none";
            }
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
            localStorage.setItem('activeTab', tabName);
        }
        document.addEventListener('DOMContentLoaded', (event) => {
            const activeTab = localStorage.getItem('activeTab');
            if (activeTab && document.getElementById(activeTab)) {
                document.querySelector(`.tabs button[onclick*="${activeTab}"]`).click();
            } else {
                const firstTab = document.getElementsByClassName('tablinks')[0];
                if (firstTab) {
                    firstTab.click();
                }
            }
        });
    </script>
</head>
<body>
    <h2>👻 GhostProtocol (DigitalOcean)</h2>
    <div class="card">
        Durum: <span class="{{ 'success' if internet else 'fail' }}">{{ 'ONLINE' if internet else 'OFFLINE' }}</span>
        {% if session.get('username') %}
            | 👤 {{ session['username'] }} | 💰 {{ session.get('balance', 0)|round(4) }} GHOST
            <br><a href="/dashboard">Panel</a> | <a href="/mine">Madencilik</a> | <a href="/logout">Çıkış</a>
        {% else %}
             <a href="/login">Giriş</a> | <a href="/register">Kayıt</a>
        {% endif %}
    </div>
    <div class="card">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- ROTLAR ---

@app.route('/')
def home():
    try:
        conn = db.get_connection()
        assets = conn.execute("SELECT * FROM assets WHERE status = 'active' ORDER BY creation_time DESC LIMIT 10").fetchall()
        conn.close()
        
        return render_template_string(LAYOUT + """
            <h3>Ghost Varlık Arama Motoru</h3>
            <form action="/search" method="get">
                <input name="q" placeholder=".ghost veya Varlık Adı..." required>
                <button type="submit">Ara</button>
            </form>
            <hr>
            <h3>Son Kayıtlar</h3>
            {% for asset in assets %}
                <div style="border-bottom:1px solid #555; padding:10px;">
                    <strong>{{ asset['name'] }}</strong> ({{ asset['type'] }})
                    {% if asset['type'] == 'domain' or asset['type'] in ['image', 'video', 'audio', 'file'] %}
                        <a href="/view_asset/{{ asset['asset_id'] }}" target="_blank">Görüntüle ↗️</a>
                    {% endif %}
                    {% if session.get('username') %}
                        <form action="/clone_asset" method="post" style="display:inline;"><input type="hidden" name="asset_id" value="{{ asset['asset_id'] }}"><button>Kopyala</button></form>
                    {% endif %}
                </div>
            {% endfor %}
            {% if not assets %} <p>Henüz veri yok.</p> {% endif %}
            """, assets=assets)
            
    except Exception as e:
        return f"<h1>HATA OLUŞTU:</h1><pre>{traceback.format_exc()}</pre>", 500

@app.route('/search')
def search_assets():
    query = request.args.get('q', '').strip()
    results = []
    
    if query:
        search_term = '%' + query + '%'
        try:
            conn = db.get_connection()
            results = conn.execute("SELECT * FROM assets WHERE status = 'active' AND name LIKE ? ORDER BY name", 
                                   (search_term,)).fetchall()
            conn.close()
        except Exception as e:
            return f"<h1>VERİTABANI ARAMA HATASI:</h1><pre>{traceback.format_exc()}</pre>", 500

    return render_template_string(LAYOUT + """
        <h3>Varlık Arama Sonuçları</h3>
        <p><a href="/">Geri Dön</a></p>
        {% if query %}
            <p>Aranan: <strong>{{ query }}</strong> ({{ results|length }} sonuç bulundu)</p>
        {% endif %}

        {% if not results %}
            <p>Aramanızla eşleşen sonuç bulunamadı.</p>
        {% else %}
            {% for asset in results %}
                <div class="card" style="border-left: 5px solid #4dabf7;">
                    <h4>{{ asset['name'] }} ({{ asset['type'] }})</h4>
                    <p><strong>Sahibi:</strong> {{ asset['owner_pub_key'][:10] }}...</p>
                    <p><strong>Boyut:</strong> {{ (asset['storage_size'] / 1024)|round(2) }} KB</p>
                    {% if asset['type'] == 'domain' or asset['type'] in ['image', 'video', 'audio', 'file'] %}
                        <a href="/view_asset/{{ asset['asset_id'] }}" target="_blank">Görüntüle ↗️</a>
                    {% endif %}
                    {% if session.get('username') %}
                        <form action="/clone_asset" method="post" style="display:inline;"><input type="hidden" name="asset_id" value="{{ asset['asset_id'] }}"><button>Kopyala</button></form>
                    {% endif %}
                </div>
            {% endfor %}
        {% endif %}
        """, results=results, query=query)

@app.route('/view_asset/<asset_id>')
def view_asset(asset_id):
    if not asset_id:
        return "400: Varlık ID'si gerekli", 400
        
    conn = db.get_connection()
    asset = conn.execute("SELECT name, type, content FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    conn.close()
    
    if not asset:
        return "404: Varlık bulunamadı", 404
        
    try:
        content_bytes = base64.b64decode(asset['content'])
    except Exception:
        return f"<h1>'{asset['name']}' ({asset['type']})</h1><p>İçerik Base64'ten çözülemiyor. Hatalı dosya formatı.</p>", 500

    asset_type = asset['type']

    if asset_type == 'domain':
        return content_bytes.decode('utf-8')
    
    elif asset_type in ['image', 'video', 'audio', 'file']:
        # Basit bir MIME tipi çıkarımı yapıyoruz
        mime_type = 'application/octet-stream'
        if asset['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            mime_type = f'image/{asset["name"].split(".")[-1]}'
        elif asset['name'].lower().endswith(('.mp4', '.webm')):
            mime_type = f'video/{asset["name"].split(".")[-1]}'
        elif asset['name'].lower().endswith(('.mp3', '.wav')):
            mime_type = f'audio/{asset["name"].split(".")[-1]}'
        elif asset['name'].lower().endswith('.html'):
            mime_type = 'text/html' # HTML dosyalarını da görüntülemesi için
        
        # Binary veriyi Response olarak döndür
        return Response(content_bytes, mimetype=mime_type)

    return render_template_string(LAYOUT + f"""
        <h3>'{asset['name']}' Görüntüleniyor</h3>
        <p>Tip: {asset_type} (İçerik metin olarak gösterilemiyor, ikili dosya olabilir).</p>
        """)

# --- ROTA: ASSET DÜZENLEME (Syntax Hatası Düzeltildi) ---
@app.route('/edit_asset/<asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    if not session.get('username'):
        return redirect('/login')

    conn = db.get_connection()
    asset = conn.execute("SELECT * FROM assets WHERE asset_id = ? AND owner_pub_key = ?", 
                         (asset_id, session['pub_key'])).fetchone()
    conn.close()

    if not asset:
        return "403: Varlık bulunamadı veya düzenleme yetkiniz yok.", 403

    msg = ""

    if request.method == 'POST':
        if asset['type'] == 'domain':
            new_content = request.form['domain_data']
            success, response = storage_chain.update_asset(asset_id, session['pub_key'], new_content)
            msg = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı' if success else 'Hata'}: {response}</div>"
            
            # Güncel içeriği çek (asset değişkenini güncelle)
            conn = db.get_connection()
            asset = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
            conn.close()
            
        else:
            msg = "<div class='msg err'>Bu varlık tipi (Domain hariç) şu an doğrudan düzenlenemez.</div>"

    content_data = ""
    if asset['type'] == 'domain':
        try:
            content_data = base64.b64decode(asset['content']).decode('utf-8')
        except:
            content_data = "İçerik çözülemedi."

    # HATA DÜZELTME BURADA YAPILDI: Jinja2 blokları f-string'in dışına alındı ve render_template_string'in içine dahil edildi.
    template_html = f"""
        {msg}
        <h3>Varlık Düzenle: {asset['name']}</h3>
        <p>Tipi: <strong>{asset['type']}</strong></p>
        
        """ + (
        """
        <form method="post">
            <textarea name="domain_data" rows="20" placeholder="HTML/XML İçeriği">{{ content_data }}</textarea>
            <button type="submit">İçeriği Güncelle</button>
        </form>
        """ if asset['type'] == 'domain' else """
        <p>Bu varlık tipi için (Görsel, Video, vb.) sadece klonlama ve silme desteklenmektedir.</p>
        """) + """
        
        <p><a href="/dashboard">Panele Geri Dön</a></p>
        """
        
    return render_template_string(LAYOUT + template_html, content_data=content_data)

# --- ROTA: DAHİLİ TARAYICI ---
@app.route('/browse', methods=['GET'])
def browse():
    if not session.get('username'):
        return redirect('/login')
        
    domain_name = request.args.get('domain', 'sitem.ghost').strip()
    content_frame = "Lütfen bir **.ghost** domain adı girin."
    
    if domain_name.endswith('.ghost'):
        conn = db.get_connection()
        asset = conn.execute("SELECT asset_id FROM assets WHERE type = 'domain' AND name = ?", (domain_name,)).fetchone()
        conn.close()
        
        if asset:
            # Domain bulundu, içeriği iframe ile view_asset rotasından çekiyoruz.
            content_frame = f"""
                <iframe src="/view_asset/{asset['asset_id']}" style="width: 100%; height: 600px; border: 1px solid #444;"></iframe>
                <p><strong>Görüntülenen:</strong> {domain_name}</p>
            """
        else:
            content_frame = f"<p>Hata: **{domain_name}** adında bir domain bulunamadı.</p>"
            
    return render_template_string(LAYOUT + f"""
        <h3>Ghost Tarayıcı (Deneysel)</h3>
        <p>Bu tarayıcı, Ghost Protocol üzerindeki kayıtlı .ghost sitelerini görüntülemenizi sağlar.</p>
        
        <form action="/browse" method="get">
            <input name="domain" placeholder="Örn: sitem.ghost" value="{domain_name}" required>
            <button type="submit">Görüntüle</button>
        </form>
        
        <hr>
        {content_frame}
        """, domain_name=domain_name)

# --- TAB'LI DASHBOARD ROTASI ---
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('username'): 
        return redirect('/login')

    msg_html = "" 
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'send_coin':
            try:
                recipient = request.form['recipient']
                amount = float(request.form['amount'])
                success, response = ghost_chain.send_ghostcoin(session['pub_key'], recipient, amount)
                msg_html = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı' if success else 'Hata'}: {response}</div>"
            except ValueError:
                msg_html = "<div class='msg err'>Hata: Geçerli bir miktar girin.</div>"
            except Exception as e:
                msg_html = f"<div class='msg err'>İşlem Hatası: {str(e)}</div>"
            
            conn = db.get_connection()
            user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (session['pub_key'],)).fetchone()
            session['balance'] = user['balance']
            conn.close()

        elif action == 'mint_domain':
            domain_name = request.form['domain_name']
            domain_data = request.form['domain_data']
            success, response = storage_chain.mint_domain(session['pub_key'], domain_name, domain_data)
            msg_html = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı' if success else 'Hata'}: {response}</div>"
        
        elif action == 'upload_file' and 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                file_bytes = file.read()
                file_content_b64 = base64.b64encode(file_bytes).decode('utf-8')
                mime_type = file.mimetype
                
                success, response = storage_chain.upload_asset(session['pub_key'], mime_type, secure_filename(file.filename), file_content_b64)
                msg_html = f"<div class='msg {'ok' if success else 'err'}'>{'Yükleme Başarılı' if success else 'Yükleme Hatası'}: {response}</div>"


    conn = db.get_connection()
    assets = conn.execute("SELECT * FROM assets WHERE owner_pub_key = ? ORDER BY creation_time DESC", (session['pub_key'],)).fetchall()
    transactions = conn.execute("SELECT * FROM transactions WHERE sender = ? OR recipient = ? ORDER BY timestamp DESC LIMIT 10", (session['pub_key'], session['pub_key'])).fetchall()
    conn.close()

    # Cüzdan adresini Python string birleştirme ile geçirme (hata oluşmaması için)
    pub_key_display = session['pub_key'] if 'pub_key' in session else "Yükleniyor..."

    template_content = f"""
        {msg_html}
        
        <div class="tabs">
            <button class="tablinks" onclick="openTab(event, 'Wallet')">💳 Cüzdan & İşlemler</button>
            <button class="tablinks" onclick="openTab(event, 'Storage')">💾 Varlıklar & Yönetim</button>
            <a href="/browse" class="tablinks" style="display:inline-block; padding: 14px 16px;">🌐 Ghost Tarayıcı</a>
        </div>

        <div id="Wallet" class="tabcontent">
            <h3>💳 Cüzdanım</h3>
            <div class="card">
                <p><strong>Genel Anahtar (Public Key):</strong></p>
                <p class="full-width-key">{pub_key_display}</p>
                <p><strong>Bakiye:</strong> {{ session.get('balance', 0)|round(4) }} GHOST</p>
            </div>
            
            <h4>GhostCoin Gönder</h4>
            <form method="post">
                <input type="hidden" name="action" value="send_coin">
                <input name="recipient" placeholder="Alıcı Cüzdan Adresi (Public Key)" required>
                <input name="amount" type="number" step="0.0001" min="0.0001" placeholder="Miktar (GHOST)" required>
                <button type="submit">Gönder</button>
            </form>

            <h4>İşlemlerim</h4>
            <ul>
                {{% for tx in transactions %}}
                    <li>
                        {{% if tx['sender'] == '0' %}}
                            ✅ **Ödül:** +{{ tx['amount']|round(4) }} GHOST (Blok #{{ tx['block_index'] }})
                        {{% elif tx['sender'] == session['pub_key'] %}}
                            ➡️ **Gönderilen:** -{{ tx['amount']|round(4) }} GHOST (Kime: {{ tx['recipient'][:10] }}...)
                        {{% else %}}
                            ⬅️ **Alınan:** +{{ tx['amount']|round(4) }} GHOST (Kimden: {{ tx['sender'][:10] }}...)
                        {{% endif %}}
                    </li>
                {{% endfor %}}
            </ul>
        </div>

        <div id="Storage" class="tabcontent">
            <h3>💾 Varlık Kayıt & Yönetim</h3>
            
            <h4>.ghost Domain Kaydet (XML Bazlı Web Sitesi)</h4>
            <form method="post">
                <input type="hidden" name="action" value="mint_domain">
                <input name="domain_name" placeholder="Örn: sitem.ghost" required>
                <textarea name="domain_data" rows="5" placeholder="XML/HTML Site İçeriği" required></textarea>
                <button type="submit">Kaydet</button>
            </form>
            
            <h4>Dosya Yükle (Görsel/Ses/Video)</h4>
            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="action" value="upload_file">
                <input type="file" name="file" required>
                <button type="submit">Yükle</button>
            </form>

            <h4>Kayıtlı Varlıklarım</h4>
            <ul>
                {{% for a in assets %}}
                    <li>
                        {{ a['name'] }} ({{ a['type'] }}) 
                        {{% if a['type'] == 'domain' or a['type'] in ['image', 'video', 'audio', 'file'] %}}
                            <a href="/view_asset/{{ a['asset_id'] }}" target="_blank">Görüntüle ↗️</a>
                        {{% endif %}}
                        {{% if a['type'] == 'domain' %}}
                            <a href="/edit_asset/{{ a['asset_id'] }}">Düzenle ✏️</a>
                        {{% endif %}}
                    </li>
                {{% endfor %}}
            </ul>
        </div>
        """
        
    # Jinja2 tag'lerini f-string içinde kaçırmak için `{%` yerine `{{%` kullandık.
    return render_template_string(LAYOUT + template_content, assets=assets, transactions=transactions)


# --- Kalan Rotalar (Değişmedi) ---

@app.route('/mine')
def mine():
    if not session.get('username'): 
        return redirect('/login')
        
    try:
        success, response = ghost_chain.mine_block(session['pub_key'])
        
        if success:
            msg = f"Madencilik Başarılı! Yeni blok #{response} oluşturuldu. {BLOCK_REWARD} GHOST kazandınız."
            conn = db.get_connection()
            user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (session['pub_key'],)).fetchone()
            session['balance'] = user['balance']
            conn.close()
        else:
            msg = f"Madencilik Başarısız: {response}"
            
        return render_template_string(LAYOUT + f"""
            <div class='msg {'ok' if success else 'err'}'>{msg}</div>
            <h3>Madencilik Alanı</h3>
            <p>Sistem, zorluk seviyesi **{MINING_DIFFICULTY}** olan bir Proof-of-Work (İş İspatı) arıyor.</p>
            <p>Yeni blok kazdığınızda **{BLOCK_REWARD} GHOST** ödül kazanırsınız.</p>
            <a href="/dashboard">Cüzdana Geri Dön</a>
            <hr>
            <p>Son Blok: #{ghost_chain.last_block()['block_index'] if ghost_chain.last_block() else 'N/A'}</p>
        """, ghost_chain=ghost_chain)
        
    except Exception as e:
        return f"<h1>MADENCİLİK HATASI:</h1><pre>{traceback.format_exc()}</pre>", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            success, msg = user_mgr.register(request.form['username'], request.form['password'], request.form['name'], request.form['surname'], request.form['phone'], request.form['email'])
            if success:
                session['temp_username'] = request.form['username']
                return redirect(url_for('verify'))
            return f"Hata: {msg} <a href='/register'>Geri</a>"
        return render_template_string(LAYOUT + """
            <h3>Kayıt</h3>
            <form method='post'><input name='username' placeholder='Kullanıcı Adı'><input name='password' type='password' placeholder='Şifre'><input name='name' placeholder='Ad'><input name='surname' placeholder='Soyad'><input name='phone' placeholder='Tel'><input name='email' placeholder='Email'><button>Kaydol</button></form>
            """)
    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        if user_mgr.verify_user(session.get('temp_username', ''), request.form['code']):
            return redirect(url_for('login'))
        return "Hatalı Kod"
    return render_template_string(LAYOUT + """
        <h3>Doğrulama</h3>
        <p>Terminaldeki kodu girin.</p>
        <form method='post'><input name='code' placeholder='Kod'><button>Onayla</button></form>
        """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = db.get_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (request.form['username'], request.form['password'])).fetchone()
        conn.close()
        if user:
            if user['is_verified'] == 0:
                session['temp_username'] = user['username']
                return redirect(url_for('verify'))
            session['username'] = user['username']
            session['pub_key'] = user['wallet_public_key']
            session['balance'] = user['balance']
            return redirect(url_for('dashboard'))
        return "Giriş Hatalı <a href='/login'>Tekrar Dene</a>"
    return render_template_string(LAYOUT + """
        <h3>Giriş</h3>
        <form method='post'><input name='username' placeholder='Kullanıcı Adı'><input name='password' type='password' placeholder='Şifre'><button>Giriş</button></form>
        """)

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('username'): return redirect('/login')
    return redirect(url_for('dashboard'))

@app.route('/clone_asset', methods=['POST'])
def clone_asset():
    if not session.get('username'): return redirect('/login')
    storage_chain.clone_asset(request.form['asset_id'], session['pub_key'])
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- SERVER RUN ---
if __name__ == '__main__':
    print("--- GHOST CLOUD SERVER STARTING ---")
    mesh.start()
    app.run(host='0.0.0.0', port=GHOST_PORT, debug=True, use_reloader=False)

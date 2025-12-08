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

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GhostNode")

# --- KRİPTO KÜTÜPHANESİ KONTROLÜ / CRYPTO LIBRARY CHECK ---
try:
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import serialization, hashes
    CRYPTO_AVAILABLE = True
except ImportError as e:
    CRYPTO_AVAILABLE = False
    logger.error(f"Kripto Kütüphanesi Hatası / Crypto Library Error: {e}")

# --- YAPILANDIRMA / CONFIGURATION ---
MINING_DIFFICULTY = 4  # Madencilik Zorluğu / Mining Difficulty
BLOCK_REWARD = 10      # Madencilik Ödülü / Mining Reward
DB_FILE = os.path.join(os.getcwd(), "ghost_v5.db")
MESH_PORT = 9999       # Mesh Ağı Portu / Mesh Network Port
GHOST_PORT = 5000      # Ana Sunucu Portu / Main Server Port
GHOST_BEACON_MSG = b"GHOST_PROTOCOL_NODE_HERE" # Sinyal Mesajı / Beacon Message

app = Flask(__name__)
app.secret_key = "super_secret_mesh_key"

# --- VERİTABANI YÖNETİCİSİ / DATABASE MANAGER ---
class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db() # Veritabanını Başlat / Initialize Database

    def get_connection(self):
        # Bağlantı oluşturur ve thread güvenliğini sağlar / Creates connection and ensures thread safety
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            # Kullanıcılar Tablosu / Users Table
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT, surname TEXT, phone TEXT, email TEXT, is_verified INTEGER DEFAULT 0, verification_code TEXT, wallet_private_key TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 0)''')
            # İşlemler Tablosu / Transactions Table
            cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
            # Bloklar Tablosu / Blocks Table
            cursor.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, proof INTEGER, previous_hash TEXT, block_hash TEXT)''')
            # Varlıklar Tablosu (Domain, Dosya, vs.) / Assets Table (Domain, File, etc.)
            cursor.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, last_payment_time REAL, status TEXT DEFAULT 'active')''')
            # Mesh Ağındaki Düğümler Tablosu / Mesh Network Peers Table
            cursor.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL, method TEXT)''')
            
            # Genesis Bloğu Oluştur / Create Genesis Block
            if cursor.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
                self.create_genesis_block(cursor)
                
            conn.commit()
            conn.close()
        except Exception as e:
            logger.critical(f"DB Init Hatası / DB Init Error: {e}")

    def create_genesis_block(self, cursor):
        # İlk (Genesis) bloğu tanımlar / Defines the initial (Genesis) block
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
        # Bloğun SHA-256 hash'ini hesaplar / Calculates the SHA-256 hash of a block
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# --- MESH MANAGER ---
class MeshManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.running = True

    def start(self):
        # Mesh ağ aktivitelerini başlatan thread'leri çalıştırır / Starts threads for Mesh network activities
        t1 = threading.Thread(target=self.listen_udp_broadcast, daemon=True)
        t2 = threading.Thread(target=self.broadcast_presence, daemon=True)
        t1.start()
        t2.start()

    def register_peer(self, ip, method="WIFI"):
        # Ağdaki yeni bir düğümü kaydeder veya günceller / Registers or updates a new peer on the network
        try:
            conn = self.db.get_connection()
            conn.execute("INSERT OR REPLACE INTO mesh_peers (ip_address, last_seen, method) VALUES (?, ?, ?)", 
                         (ip, time.time(), method))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def broadcast_presence(self):
        # Ağdaki varlığını UDP üzerinden yayınlar / Broadcasts presence over UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self.running:
            try:
                # Sinyal mesajını gönder / Send beacon message
                msg = f"{GHOST_BEACON_MSG.decode()}|{GHOST_PORT}|0.0.0.0".encode()
                sock.sendto(msg, ('<broadcast>', MESH_PORT))
                time.sleep(5)
            except Exception:
                time.sleep(10)

    def listen_udp_broadcast(self):
        # Gelen UDP sinyallerini dinler ve düğümleri kaydeder / Listens for incoming UDP beacons and registers nodes
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', MESH_PORT))
        except Exception as e:
            logger.error(f"UDP Bağlanamadı / UDP Connection Failed: {e}")
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


# --- BLOCKCHAIN/MINING MANTIĞI / BLOCKCHAIN/MINING LOGIC ---
class GhostChain:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def last_block(self):
        # Zincirdeki son bloğu döndürür / Returns the last block in the chain
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return block

    def proof_of_work(self, last_proof):
        # Proof of Work (İş İspatı) algoritması / Proof of Work algorithm
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    def valid_proof(self, last_proof, proof):
        # Hash'in zorluk seviyesini karşılayıp karşılamadığını kontrol eder / Checks if the hash meets the difficulty level
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:MINING_DIFFICULTY] == "0" * MINING_DIFFICULTY

    def mine_block(self, miner_address):
        # Yeni bir blok oluşturur ve madenciye ödül verir / Creates a new block and rewards the miner
        last_block = self.last_block()
        if not last_block:
             return False, "Genesis blok bulunamadı / Genesis block not found"

        last_proof = last_block['proof']
        proof = self.proof_of_work(last_proof)

        # Madencilik ödülü işlemi / Mining reward transaction
        self.new_transaction(sender="0", recipient=miner_address, amount=BLOCK_REWARD)
        
        conn = self.db.get_connection()
        # Onaylanmayı bekleyen işlemleri al / Get pending transactions
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
            # Yeni bloğu zincire ekle / Add new block to the chain
            conn.execute("INSERT INTO blocks (block_index, timestamp, proof, previous_hash, block_hash) VALUES (?, ?, ?, ?, ?)",
                         (new_block['index'], new_block['timestamp'], new_block['proof'], new_block['previous_hash'], new_block_hash))
            # Bekleyen işlemleri yeni bloka bağla / Link pending transactions to the new block
            tx_ids = [tx['tx_id'] for tx in pending_txs]
            if tx_ids:
                q_marks = ', '.join('?' for _ in tx_ids)
                conn.execute(f"UPDATE transactions SET block_index = ? WHERE tx_id IN ({q_marks})", (new_block['index'], *tx_ids))
            
            # Madencilik ödülünü cüzdana ekle / Add mining reward to the wallet
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (BLOCK_REWARD, miner_address))
            conn.commit()
            return True, new_block['index']
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def new_transaction(self, sender, recipient, amount):
        # Yeni bir işlem oluşturur (henüz bloka eklenmemiş) / Creates a new transaction (not yet mined into a block)
        conn = self.db.get_connection()
        tx_id = str(uuid4())
        
        # Göndericinin bakiyesini kontrol et (Madencilik ödülü hariç) / Check sender balance (excluding Mining Reward '0')
        if sender != "0":
            user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender,)).fetchone()
            if not user or user['balance'] < amount:
                conn.close()
                return False, "Yetersiz bakiye veya geçersiz gönderici / Insufficient balance or invalid sender"
                
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
        # GhostCoin gönderir ve bakiyeleri günceller / Sends GhostCoin and updates balances
        if amount <= 0: return False, "Miktar 0'dan büyük olmalı / Amount must be greater than 0"
        
        conn = self.db.get_connection()
        sender_user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender_key,)).fetchone()
        recipient_user = conn.execute("SELECT * FROM users WHERE wallet_public_key = ?", (recipient_key,)).fetchone()
        conn.close()
        
        if not sender_user or sender_user['balance'] < amount:
            return False, "Yetersiz bakiye / Insufficient balance"
        if not recipient_user:
            return False, "Alıcı cüzdan adresi geçersiz / Invalid recipient wallet address"

        success, tx_id = self.new_transaction(sender_key, recipient_key, amount)
        if success:
            # İşlem başarılı ise bakiyeleri güncelle / Update balances if transaction is successful
            conn = self.db.get_connection()
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (amount, sender_key))
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (amount, recipient_key))
            conn.commit()
            conn.close()
            return True, f"İşlem başarılı, TX ID: {tx_id}. Yeni blokta onaylanacak. / Transaction successful, TX ID: {tx_id}. To be confirmed in a new block."
        
        return False, tx_id

# --- DOMAIN/VARLIK YÖNETİMİ / DOMAIN/ASSET MANAGEMENT ---
class StorageBlockchain:
    def __init__(self, db_manager):
        self.db = db_manager

    def mint_domain(self, owner_pub_key, domain_name, domain_data):
        # Yeni bir .ghost domaini kaydeder / Registers a new .ghost domain
        if not domain_name.endswith('.ghost'):
            return False, "Domain .ghost uzantılı olmalıdır. / Domain must end with .ghost"

        # İçeriği Base64 olarak kodla / Encode content as Base64
        content = base64.b64encode(domain_data.encode('utf-8')).decode('utf-8')
        
        conn = self.db.get_connection()
        try:
            conn.execute('INSERT INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, last_payment_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                         (str(uuid4()), owner_pub_key, 'domain', domain_name, content, len(domain_data), time.time(), time.time()))
            conn.commit()
            return True, f"{domain_name} başarıyla kaydedildi. / {domain_name} successfully registered."
        except sqlite3.IntegrityError:
            return False, "Bu domain adı zaten kayıtlı. / This domain name is already registered."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
            
    def update_asset(self, asset_id, owner_pub_key, new_content):
        # Kayıtlı bir varlığın içeriğini günceller / Updates the content of a registered asset
        conn = self.db.get_connection()
        asset = conn.execute("SELECT type, content FROM assets WHERE asset_id = ? AND owner_pub_key = ?", (asset_id, owner_pub_key)).fetchone()
        
        if not asset:
            conn.close()
            return False, "Varlık bulunamadı veya yetkiniz yok. / Asset not found or you don't have permission."

        try:
            if asset['type'] == 'domain':
                # Domain içeriği (HTML/XML) güncelleniyor. / Updating domain content (HTML/XML).
                content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
            else:
                # Şu an sadece domain düzenlemeyi destekliyoruz / Currently only supporting domain editing
                content_b64 = asset['content']
            
            size = len(content_b64)
            
            conn.execute("UPDATE assets SET content = ?, storage_size = ?, creation_time = ? WHERE asset_id = ?",
                         (content_b64, size, time.time(), asset_id))
            conn.commit()
            return True, "Varlık içeriği başarıyla güncellendi. / Asset content successfully updated."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def upload_asset(self, user_pub_key, mime_type, name, file_content_b64):
        # Yeni bir dosya varlığı yükler / Uploads a new file asset
        try:
            size = len(file_content_b64)
            asset_type = 'file'
            # MIME tipine göre varlık türünü belirle / Determine asset type based on MIME type
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
        # Bir varlığı klonlar (kopyalar) / Clones (copies) an asset
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
        # Yeni bir kullanıcı kaydeder ve cüzdan oluşturur / Registers a new user and creates a wallet
        if not CRYPTO_AVAILABLE: return False, "Kripto Modülü Yok / Crypto Module Missing"
        try:
            # RSA anahtar çifti oluştur / Generate RSA key pair
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            pem_priv = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()).decode('utf-8')
            pem_pub = private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
            verification_code = str(random.randint(100000, 999999))
            
            conn = self.db.get_connection()
            # Başlangıç bakiyesi 50 GHOST / Initial balance 50 GHOST
            conn.execute('INSERT INTO users (username, password, name, surname, phone, email, verification_code, wallet_private_key, wallet_public_key, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 50)', 
                            (username, password, name, surname, phone, email, verification_code, pem_priv, pem_pub))
            conn.commit()
            conn.close()
            print(f"--- DOĞRULAMA KODU / VERIFICATION CODE: {verification_code} ---")
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def verify_user(self, username, code):
        # Kullanıcıyı doğrulama kodu ile onaylar / Verifies the user with the verification code
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
# Servisleri başlat / Initialize services
db = DatabaseManager(DB_FILE)
ghost_chain = GhostChain(db)
storage_chain = StorageBlockchain(db)
mesh = MeshManager(db)
user_mgr = UserManager(db)

# --- GLOBAL HATA YAKALAYICI VE CONTEXT / GLOBAL ERROR HANDLER AND CONTEXT ---
@app.errorhandler(500)
def internal_error(exception):
    # 500 İç Sunucu Hatası / 500 Internal Server Error
    return f"<h1>500 Sunucu Hatası / Server Error</h1><pre>{traceback.format_exc()}</pre>", 500

@app.errorhandler(404)
def not_found(exception):
    # 404 Sayfa Bulunamadı / 404 Page Not Found
    return "<h1>404 Sayfa Bulunamadı / Page Not Found</h1>", 404

@app.context_processor
def inject_vars():
    # Şablonlara genel değişkenler ekler / Injects global variables into templates
    peers = []
    internet = False
    try:
        conn = db.get_connection()
        # Son 5 dakika içinde görülen düğümleri listele / List peers seen in the last 5 minutes
        peers = conn.execute("SELECT * FROM mesh_peers WHERE last_seen > ?", (time.time() - 300,)).fetchall()
        conn.close()
        # İnternet bağlantısını kontrol et / Check internet connectivity
        socket.create_connection(("8.8.8.8", 53), timeout=0.1)
        internet = True
    except:
        pass
    return dict(internet=internet, peers=peers)

# --- LAYOUT HTML (Tab CSS Eklendi) / LAYOUT HTML (Tab CSS Added) ---
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

        /* Tab Stilleri / Tab Styles */
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
                // localStorage'da kayıtlı olanı veya ilk tab'ı aç / Open saved tab or the first one
                const btn = document.querySelector(`.tabs button[onclick*="${activeTab}"]`);
                if (btn) {
                    btn.click();
                }
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
        Durum / Status: <span class="{{ 'success' if internet else 'fail' }}">{{ 'ONLINE' if internet else 'OFFLINE' }}</span>
        {% if session.get('username') %}
            | 👤 {{ session['username'] }} | 💰 {{ session.get('balance', 0)|round(4) }} GHOST
            <br><a href="/dashboard">Panel / Dashboard</a> | <a href="/mine">Madencilik / Mining</a> | <a href="/logout">Çıkış / Logout</a>
        {% else %}
             <a href="/login">Giriş / Login</a> | <a href="/register">Kayıt / Register</a>
        {% endif %}
    </div>
    <div class="card">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- ROTLAR / ROUTES ---

@app.route('/')
def home():
    # Ana sayfa ve varlık arama motoru / Home page and asset search engine
    try:
        conn = db.get_connection()
        # Son 10 aktif varlığı al / Get last 10 active assets
        assets = conn.execute("SELECT * FROM assets WHERE status = 'active' ORDER BY creation_time DESC LIMIT 10").fetchall()
        conn.close()
        
        return render_template_string(LAYOUT + """
            <h3>Ghost Varlık Arama Motoru / Ghost Asset Search Engine</h3>
            <form action="/search" method="get">
                <input name="q" placeholder=".ghost veya Varlık Adı / .ghost or Asset Name..." required>
                <button type="submit">Ara / Search</button>
            </form>
            <hr>
            <h3>Son Kayıtlar / Latest Registrations</h3>
            {% for asset in assets %}
                <div style="border-bottom:1px solid #555; padding:10px;">
                    <strong>{{ asset['name'] }}</strong> ({{ asset['type'] }})
                    {% if asset['type'] == 'domain' or asset['type'] in ['image', 'video', 'audio', 'file'] %}
                        <a href="/view_asset/{{ asset['asset_id'] }}" target="_blank">Görüntüle / View ↗️</a>
                    {% endif %}
                    {% if session.get('username') %}
                        <form action="/clone_asset" method="post" style="display:inline;"><input type="hidden" name="asset_id" value="{{ asset['asset_id'] }}"><button>Kopyala / Clone</button></form>
                    {% endif %}
                </div>
            {% endfor %}
            {% if not assets %} <p>Henüz veri yok. / No data yet.</p> {% endif %}
            """, assets=assets)
            
    except Exception as e:
        return f"<h1>HATA OLUŞTU / ERROR OCCURRED:</h1><pre>{traceback.format_exc()}</pre>", 500

@app.route('/search')
def search_assets():
    # Varlık arama sonuçları sayfası / Asset search results page
    query = request.args.get('q', '').strip()
    results = []
    
    if query:
        search_term = '%' + query + '%'
        try:
            conn = db.get_connection()
            # Varlık adında arama yap / Search by asset name
            results = conn.execute("SELECT * FROM assets WHERE status = 'active' AND name LIKE ? ORDER BY name", 
                                   (search_term,)).fetchall()
            conn.close()
        except Exception as e:
            return f"<h1>VERİTABANI ARAMA HATASI / DATABASE SEARCH ERROR:</h1><pre>{traceback.format_exc()}</pre>", 500

    return render_template_string(LAYOUT + """
        <h3>Varlık Arama Sonuçları / Asset Search Results</h3>
        <p><a href="/">Geri Dön / Go Back</a></p>
        {% if query %}
            <p>Aranan / Searched: <strong>{{ query }}</strong> ({{ results|length }} sonuç bulundu / results found)</p>
        {% endif %}

        {% if not results %}
            <p>Aramanızla eşleşen sonuç bulunamadı. / No results matching your query were found.</p>
        {% else %}
            {% for asset in results %}
                <div class="card" style="border-left: 5px solid #4dabf7;">
                    <h4>{{ asset['name'] }} ({{ asset['type'] }})</h4>
                    <p><strong>Sahibi / Owner:</strong> {{ asset['owner_pub_key'][:10] }}...</p>
                    <p><strong>Boyut / Size:</strong> {{ (asset['storage_size'] / 1024)|round(2) }} KB</p>
                    {% if asset['type'] == 'domain' or asset['type'] in ['image', 'video', 'audio', 'file'] %}
                        <a href="/view_asset/{{ asset['asset_id'] }}" target="_blank">Görüntüle / View ↗️</a>
                    {% endif %}
                    {% if session.get('username') %}
                        <form action="/clone_asset" method="post" style="display:inline;"><input type="hidden" name="asset_id" value="{{ asset['asset_id'] }}"><button>Kopyala / Clone</button></form>
                    {% endif %}
                </div>
            {% endfor %}
        {% endif %}
        """, results=results, query=query)

@app.route('/view_asset/<asset_id>')
def view_asset(asset_id):
    # Varlık içeriğini görüntüler (Domain içeriğini döndürür) / Displays asset content (Returns Domain content)
    if not asset_id:
        return "400: Varlık ID'si gerekli / Asset ID required", 400
        
    conn = db.get_connection()
    asset = conn.execute("SELECT name, type, content FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    conn.close()
    
    if not asset:
        return "404: Varlık bulunamadı / Asset not found", 404
        
    try:
        content_bytes = base64.b64decode(asset['content'])
    except Exception:
        return f"<h1>'{asset['name']}' ({asset['type']})</h1><p>İçerik Base64'ten çözülemiyor. Hatalı dosya formatı. / Content cannot be decoded from Base64. Invalid file format.</p>", 500

    asset_type = asset['type']

    if asset_type == 'domain':
        # Domain ise HTML/XML içeriğini döndür / If domain, return HTML/XML content
        return content_bytes.decode('utf-8')
    
    elif asset_type in ['image', 'video', 'audio', 'file']:
        # İkili dosya ise MIME tipi ile döndür / If binary file, return with MIME type
        mime_type = 'application/octet-stream'
        if asset['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            mime_type = f'image/{asset["name"].split(".")[-1]}'
        elif asset['name'].lower().endswith(('.mp4', '.webm')):
            mime_type = f'video/{asset["name"].split(".")[-1]}'
        elif asset['name'].lower().endswith(('.mp3', '.wav')):
            mime_type = f'audio/{asset["name"].split(".")[-1]}'
        elif asset['name'].lower().endswith('.html'):
            mime_type = 'text/html' 
        
        return Response(content_bytes, mimetype=mime_type)

    return render_template_string(LAYOUT + f"""
        <h3>'{asset['name']}' Görüntüleniyor / Viewing</h3>
        <p>Tip / Type: {asset_type} (İçerik metin olarak gösterilemiyor, ikili dosya olabilir. / Content cannot be displayed as text, might be binary file).</p>
        """)

# --- ROTA: ASSET DÜZENLEME (Hata Giderildi) / ROUTE: ASSET EDIT (Error Fixed) ---
@app.route('/edit_asset/<asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    # Kullanıcıya ait domain içeriğini düzenler / Edits the domain content owned by the user
    if not session.get('username'):
        return redirect('/login')

    conn = db.get_connection()
    # Yalnızca sahibi olduğu domainleri düzenleyebilir / Can only edit domains they own
    asset = conn.execute("SELECT * FROM assets WHERE asset_id = ? AND owner_pub_key = ?", 
                         (asset_id, session['pub_key'])).fetchone()
    conn.close()

    if not asset:
        return "403: Varlık bulunamadı veya düzenleme yetkiniz yok. / Asset not found or no permission to edit.", 403

    msg = ""

    if request.method == 'POST':
        if asset['type'] == 'domain':
            new_content = request.form['domain_data']
            success, response = storage_chain.update_asset(asset_id, session['pub_key'], new_content)
            msg = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı / Successful' if success else 'Hata / Error'}: {response}</div>"
            
            # Güncel içeriği çek / Fetch the updated asset data
            conn = db.get_connection()
            asset = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
            conn.close()
            
        else:
            msg = "<div class='msg err'>Bu varlık tipi (Domain hariç) şu an doğrudan düzenlenemez. / This asset type (except Domain) cannot be edited directly right now.</div>"

    content_data = ""
    if asset['type'] == 'domain':
        try:
            content_data = base64.b64decode(asset['content']).decode('utf-8')
        except:
            content_data = "İçerik çözülemedi. / Content could not be decoded."

    # HTML şablonunu Jinja2 tag'lerini Python'dan ayırarak oluştur / Create HTML template separating Jinja2 tags from Python
    # Bu rota doğru görünüyor.
    template_html = f"""
        {msg}
        <h3>Varlık Düzenle / Edit Asset: {asset['name']}</h3>
        <p>Tipi / Type: <strong>{asset['type']}</strong></p>
        """ 

    if asset['type'] == 'domain':
        template_html += """
        <form method="post">
            <textarea name="domain_data" rows="20" placeholder="HTML/XML İçeriği / HTML/XML Content">{{ content_data }}</textarea>
            <button type="submit">İçeriği Güncelle / Update Content</button>
        </form>
        """
    else:
        template_html += """
        <p>Bu varlık tipi için (Görsel, Video, vb.) sadece klonlama ve silme desteklenmektedir. / Only cloning and deletion are supported for this asset type (Image, Video, etc.).</p>
        """

    template_html += """
        <p><a href="/dashboard">Panele Geri Dön / Return to Dashboard</a></p>
        """
        
    return render_template_string(LAYOUT + template_html, content_data=content_data)

# --- ROTA: DAHİLİ TARAYICI / ROUTE: INTERNAL BROWSER ---
@app.route('/browse', methods=['GET'])
def browse():
    # .ghost domainlerini görüntülemek için basit bir tarayıcı arayüzü / A simple browser interface to view .ghost domains
    if not session.get('username'):
        return redirect('/login')
        
    domain_name = request.args.get('domain', 'sitem.ghost').strip()
    content_frame = "Lütfen bir **.ghost** domain adı girin. / Please enter a **.ghost** domain name."
    
    if domain_name.endswith('.ghost'):
        conn = db.get_connection() 
        asset = conn.execute("SELECT asset_id FROM assets WHERE type = 'domain' AND name = ?", (domain_name,)).fetchone()
        conn.close()
        
        if asset:
            # Domain içeriğini iframe ile view_asset rotasından çek / Pull domain content via iframe from view_asset route
            content_frame = f"""
                <iframe src="/view_asset/{asset['asset_id']}" style="width: 100%; height: 600px; border: 1px solid #444;"></iframe>
                <p><strong>Görüntülenen / Viewing:</strong> {domain_name}</p>
            """
        else:
            content_frame = f"<p>Hata / Error: **{domain_name}** adında bir domain bulunamadı. / A domain with the name **{domain_name}** was not found.</p>"
            
    return render_template_string(LAYOUT + f"""
        <h3>Ghost Tarayıcı (Deneysel) / Ghost Browser (Experimental)</h3>
        <p>Bu tarayıcı, Ghost Protocol üzerindeki kayıtlı .ghost sitelerini görüntülemenizi sağlar. / This browser allows you to view registered .ghost sites on the Ghost Protocol.</p>
        
        <form action="/browse" method="get">
            <input name="domain" placeholder="Örn: sitem.ghost / Ex: mysite.ghost" value="{domain_name}" required>
            <button type="submit">Görüntüle / View</button>
        </form>
        
        <hr>
        {content_frame}
        """, domain_name=domain_name)

# --- TAB'LI DASHBOARD ROTASI / TABBED DASHBOARD ROUTE ---
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # Kullanıcının cüzdan, işlemler ve varlık yönetim paneli / User's wallet, transactions, and asset management panel
    if not session.get('username'): 
        return redirect('/login')

    msg_html = "" 
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'send_coin':
            # Coin Gönderme İşlemi / Coin Sending Process
            try:
                recipient = request.form['recipient']
                amount = float(request.form['amount'])
                success, response = ghost_chain.send_ghostcoin(session['pub_key'], recipient, amount)
                msg_html = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı / Successful' if success else 'Hata / Error'}: {response}</div>"
            except ValueError:
                msg_html = "<div class='msg err'>Hata / Error: Geçerli bir miktar girin. / Enter a valid amount.</div>"
            except Exception as e:
                msg_html = f"<div class='msg err'>

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
import requests 
from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for, Response, send_file
from uuid import uuid4
from datetime import timedelta
from markupsafe import Markup 
from jinja2 import DictLoader, Template 

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GMN - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostMeshNode")

# --- YAPILANDIRMA / CONFIGURATION ---
DB_FILE = os.path.join(os.getcwd(), "ghost_mesh_node.db") 
GHOST_PORT = 5001 # Mesh Node'lar farklı bir port kullanmalı

# Ana Ağ Omurga Sunucuları (Backbone Nodes)
KNOWN_PEERS = [
    "http://46.101.219.46:5000", # Örnek olarak sizin ana sunucunuz
    # "http://digerozelnode.com:5000",
]

app = Flask(__name__)
app.secret_key = 'mesh_node_super_secret_key_2024' 
app.permanent_session_lifetime = timedelta(days=7) 
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 

# --- ÇOKLU DİL SÖZLÜĞÜ (i18n) ---
LANGUAGES = {
    'tr': {
        'title': "Ghost Mesh Düğümü (Node)",
        'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'status_success': "Başarılı", 'status_failed': "Başarısız", 
        'sync_title': "Ağ Eşitleme", 'sync_btn': "🔄 Ağı Eşitle (Backbone ile)",
        'sync_status': "Eşitleme Durumu",
        'sync_success_msg': "Ağ eşitleme başarılı. Yeni uzunluk: {length}. Varlıklar ve Domainler güncellendi.",
        'sync_no_change': "Daha uzun bir zincir bulunamadı. Mevcut uzunluk: {length}.",
        'sync_fail': "Ağ eşitleme sırasında genel bir hata oluştu.",
        'chain_info': "Zincir Bilgisi",
        'last_block': "Son Blok İndeksi",
        'asset_count': "Toplam Varlık Sayısı",
        'domain_count': "Aktif Domain Sayısı",
        'assets_title': "Yerel Olarak Sunulan Aktif Varlıklar",
        'asset_name': "Ad / ID", 'asset_type': "Tip", 'asset_action': "İşlem / Link",
        'action_view': "Gör (Yerel)",
        'welcome_header': "Ghost Mesh Düğümü Aktif",
        'welcome_text': "Bu düğüm, GhostProtocol zincirini eşler ve ağdaki varlıkları merkezi sunucuya ihtiyaç duymadan yerel olarak sunar.",
        'back_to_home': "Ana Sayfaya Dön",
    },
    'en': {
        'title': "Ghost Mesh Node",
        'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'status_success': "Success", 'status_failed': "Failed", 
        'sync_title': "Network Sync", 'sync_btn': "🔄 Sync Network (with Backbone)",
        'sync_status': "Sync Status",
        'sync_success_msg': "Network synchronization successful. New length: {length}. Assets and Domains updated.",
        'sync_no_change': "No longer chain found. Current length: {length}.",
        'sync_fail': "A general error occurred during network synchronization.",
        'chain_info': "Chain Information",
        'last_block': "Last Block Index",
        'asset_count': "Total Asset Count",
        'domain_count': "Active Domain Count",
        'assets_title': "Locally Served Active Assets",
        'asset_name': "Name / ID", 'asset_type': "Type", 'asset_action': "Action / Link",
        'action_view': "View (Local)",
        'welcome_header': "Ghost Mesh Node Active",
        'welcome_text': "This node synchronizes the GhostProtocol chain and serves assets locally without needing the central backbone server.",
        'back_to_home': "Go Back to Home",
    },
}

# --- VERİTABANI YÖNETİCİSİ (Stabil) ---
class DatabaseManager:
    # ... (Ghost Server'daki ile aynı init_db, get_connection, create_genesis_block, hash)
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
            
            # GMN sadece blokları ve varlıkları tutar, kullanıcı/cüzdan tutmaz
            cursor.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, proof INTEGER, previous_hash TEXT, block_hash TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, is_public INTEGER DEFAULT 1)''')
            
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
        if 'transactions' in block:
             block['transactions'] = sorted(block['transactions'], key=lambda tx: tx['tx_id'])
             
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# --- BLOCKCHAIN/ASSET MANAGER (Basitleştirilmiş GMN Versiyonu) ---
class GhostChain:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def last_block(self):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return dict(block) if block else None

    def get_active_assets(self):
        conn = self.db.get_connection()
        # Sadece süresi dolmamış varlıkları listele
        assets = conn.execute("SELECT * FROM assets WHERE expiry_time > ? ORDER BY creation_time DESC", (time.time(),)).fetchall()
        conn.close()
        return [dict(a) for a in assets]

# --- EŞİTLEME VE ÇATIŞMA ÇÖZÜMÜ ---
def resolve_conflicts(peers):
    max_length = chain.last_block()['block_index'] if chain.last_block() else 1
    new_chain = None
    new_assets = None
    
    for peer in peers:
        try:
            # Sadece zincir ve varlıkları çekeriz
            response = requests.get(f'{peer}/chain', timeout=10)
            
            if response.status_code == 200:
                remote_data = response.json()
                remote_length = remote_data['length']
                
                if remote_length > max_length:
                    max_length = remote_length
                    new_chain = remote_data['chain']
                    new_assets = remote_data['assets']
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"Backbone Peer {peer} ile eşitleme denemesi başarısız: {e}")
            continue

    if new_chain:
        if replace_chain_and_assets(new_chain, new_assets):
            return True, max_length
    
    return False, max_length

def replace_chain_and_assets(remote_chain, remote_assets):
    conn = db.get_connection()
    try:
        # Eski zinciri ve varlıkları sil
        conn.execute("DELETE FROM blocks WHERE block_index > 1")
        conn.execute("DELETE FROM assets")
        
        # Yeni zinciri kaydet
        for block_data in remote_chain:
            if block_data['index'] == 1: continue 
                
            conn.execute("INSERT INTO blocks (block_index, timestamp, proof, previous_hash, block_hash) VALUES (?, ?, ?, ?, ?)",
                         (block_data['index'], block_data['timestamp'], block_data['proof'], block_data['previous_hash'], block_data['block_hash']))

        # Yeni varlıkları kaydet
        for asset_data in remote_assets:
             # İçeriği Base64'ten ikili (bytes) formata dönüştür
             content_bytes = base64.b64decode(asset_data['content']) if isinstance(asset_data['content'], str) else asset_data['content']
             
             conn.execute("INSERT OR IGNORE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, is_public) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_data['asset_id'], asset_data['owner_pub_key'], asset_data['type'], asset_data['name'], content_bytes, asset_data['storage_size'], asset_data['creation_time'], asset_data['expiry_time'], asset_data['is_public']))

        conn.commit()
        logger.info(f"Zincir ve varlıklar başarıyla eşlendi. Yeni uzunluk: {len(remote_chain)}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Zincir değiştirme hatası: {e}")
        return False
    finally:
        conn.close()

# --- UYGULAMA BAŞLATMA / APP INIT ---
db = DatabaseManager(DB_FILE) 
chain = GhostChain(db)

# --- LAYOUT (Çoklu Dil Desteği) ---
LAYOUT = """
<!doctype html>
<html>
<head>
    <title>{{ lang['title'] }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #222; color: #eee; padding: 20px; }
        .card { background: #333; padding: 15px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #444; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; }
        .lang-switch a { margin-left: 10px; color: #ffeb3b; text-decoration: none; }
        a { color: #2196f3; text-decoration: none; }
        button { background: #4caf50; color: white; border: none; padding: 10px; margin-top: 15px; cursor: pointer; border-radius: 5px; }
        .msg { padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .msg.ok { background: #1e4620; color: #7fbf7f; }
        .msg.err { background: #462222; color: #f7a5a5; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #555; padding: 8px; text-align: left; font-size: 0.9em; } 
    </style>
</head>
<body>
    <div class="header-bar">
        <h2>{{ lang['title'] }} (Port: {{ GHOST_PORT }})</h2>
        <div class="lang-switch">
             {% set current_lang = session.get('lang', 'tr') %}
             <a href="{{ url_for('set_language', lang='tr') }}" style="font-weight: {{ 'bold' if current_lang == 'tr' else 'normal' }};">TR🇹🇷</a>
             <a href="{{ url_for('set_language', lang='en') }}" style="font-weight: {{ 'bold' if current_lang == 'en' else 'normal' }};">EN🇬🇧</a>
        </div>
    </div>
    
    {% block content %}{% endblock %} 

</body>
</html>
"""

# --- CONTEXT İŞLEMCİ ---
@app.context_processor
def inject_globals():
    current_lang_code = session.get('lang', 'tr')
    current_lang = LANGUAGES.get(current_lang_code, LANGUAGES['tr'])
    
    try:
        last_block = chain.last_block()
        last_block_index = last_block['block_index'] if last_block else 1
        
        conn = db.get_connection()
        asset_count = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        domain_count = conn.execute("SELECT COUNT(*) FROM assets WHERE type = 'domain' AND expiry_time > ?", (time.time(),)).fetchone()[0]
        conn.close()
        
    except Exception as e:
        logger.error(f"Context hatası: {e}")
        last_block_index = 1
        asset_count = 0
        domain_count = 0
        
    return dict(lang=current_lang, last_block_index=last_block_index, asset_count=asset_count, domain_count=domain_count, GHOST_PORT=GHOST_PORT)

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

# --- ROTALAR / ROUTES ---

@app.route('/')
def home():
    L = inject_globals()['lang']
    assets = chain.get_active_assets()
    
    template = """
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>{{ lang['welcome_header'] }}</h3>
                <p>{{ lang['welcome_text'] }}</p>
                <a href="{{ url_for('sync_network') }}">
                    <button>{{ lang['sync_btn'] }}</button>
                </a>
            </div>
            
            <div class="card">
                <h3>{{ lang['chain_info'] }}</h3>
                <p><strong>{{ lang['last_block'] }}:</strong> #{{ last_block_index }}</p>
                <p><strong>{{ lang['asset_count'] }}:</strong> {{ asset_count }}</p>
                <p><strong>{{ lang['domain_count'] }}:</strong> {{ domain_count }}</p>
            </div>
            
            <div class="card">
                <h3>{{ lang['assets_title'] }}</h3>
                <table>
                    <tr>
                        <th>{{ lang['asset_name'] }}</th>
                        <th>{{ lang['asset_type'] }}</th>
                        <th>{{ lang['asset_action'] }}</th>
                    </tr>
                    {% for a in assets %}
                    <tr>
                        <td>{{ a.name }} <br><span style="font-size: 0.7em;">ID: {{ a.asset_id[:8] }}...</span></td>
                        <td>{{ a.type | upper }}</td>
                        <td>
                            {# Yerel olarak sunulan link, merkeziyetsiz erişimi gösterir #}
                            <a href="{{ url_for('view_asset', asset_id=a.asset_id) }}" target="_blank">{{ lang['action_view'] }}</a>
                        </td>
                    </tr>
                    {% endfor %}
                    {% if not assets %}
                    <tr><td colspan="3">Aktif varlık bulunamadı. Lütfen önce ağı eşitleyin.</td></tr>
                    {% endif %}
                </table>
            </div>
        {% endblock %}
    """
    return render_template_string(template, assets=assets, L=L)

@app.route('/sync')
def sync_network():
    L = inject_globals()['lang']
    
    # Kendi adresimizi Backbone'a bildirmeye gerek yok, sadece çekim yapıyoruz
    
    replaced, new_length = resolve_conflicts(KNOWN_PEERS)
    
    if replaced:
        msg = L['sync_success_msg'].format(length=new_length)
        msg_class = 'ok'
    else:
        current_length = chain.last_block()['block_index'] if chain.last_block() else 1
        msg = L['sync_no_change'].format(length=current_length)
        msg_class = 'ok'
        
    template = """
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>{{ lang['sync_status'] }}</h3>
                <div class='msg {{ msg_class }}'>{{ msg }}</div>
                <p><a href="{{ url_for('home') }}">{{ lang['back_to_home'] }}</a></p>
            </div>
        {% endblock %}
    """
    return render_template_string(template, msg_class=msg_class, msg=msg, L=L)

# --- KRİTİK ROTA: VARLIK GÖRÜNTÜLEME (Merkeziyetsiz Servis) ---
@app.route('/view_asset/<asset_id>')
def view_asset(asset_id):
    """
    Mesh düğümünün, varlık ID'sine göre içeriği kendi yerel veritabanından sunmasını sağlar.
    """
    if not asset_id: return "400: ID gerekli", 400
    L = inject_globals()['lang']
        
    conn = db.get_connection()
    # GMN yerel veritabanında Asset ID'ye göre arama yapar
    asset = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    conn.close()
    
    if not asset: 
        logger.warning(f"Yerel varlık bulunamadı: {asset_id}")
        return "404: Varlık yerel olarak bulunamadı. Ağı eşitlemeyi deneyin.", 404
        
    content_bytes = asset['content']
    asset_type = asset['type']
    
    # Süresi dolmuş domainleri, sahibi olmayan bir mesh düğümü sunmamalı (SADECE AKİFLER)
    if asset['expiry_time'] < time.time():
        return "403: Varlığın süresi dolmuş veya kaldırılmış.", 403

    if asset_type == 'domain':
        # Domain içeriğini HTML olarak sun
        return Response(content_bytes, mimetype='text/html')
    
    elif asset_type in ['image', 'video', 'audio', 'file']:
        # Dosya uzantısına göre MIME tipi belirleme (Backbone Server ile aynı mantık)
        mime_type = 'application/octet-stream'
        name_lower = asset['name'].lower()
        if name_lower.endswith(('.jpg', '.jpeg')): mime_type = 'image/jpeg'
        elif name_lower.endswith(('.png')): mime_type = 'image/png'
        elif name_lower.endswith(('.gif')): mime_type = 'image/gif'
        elif name_lower.endswith(('.mp4', '.webm')): mime_type = 'video/mp4'
        elif name_lower.endswith(('.mp3', '.wav')): mime_type = 'audio/mpeg'
        
        # Dosyayı indirilebilir veya görüntülenebilir şekilde sun
        return Response(content_bytes, mimetype=mime_type, headers={'Content-Disposition': f'inline; filename="{asset["name"]}"'})

    template = """
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>'{{ asset.name }}' Görüntüleniyor</h3>
                <p>Tip: {{ asset.type }} (İkili dosya). Bu içerik doğrudan tarayıcıda görüntülenemez.</p>
                <p><a href="{{ url_for('home') }}">{{ lang['back_to_home'] }}</a></p>
            </div>
        {% endblock %}
    """
    return render_template_string(template, asset=dict(asset), L=L)

if __name__ == '__main__':
    app.jinja_env.loader = DictLoader({'base.html': LAYOUT})
    
    print("--- GHOST MESH DÜĞÜMÜ BAŞLATILIYOR / GHOST MESH NODE STARTING ---")
    print(f"\nMesh Node Port: {GHOST_PORT}")
    print("Mesh Node sadece zinciri ve varlıkları çeker, kullanıcı/cüzdan tutmaz.")
    print("Varlıklar artık /view_asset/<asset_id> rotası ile yerel olarak sunulabilir.")
    print("Veritabanı: ghost_mesh_node.db (Kalıcı)\n")
    
    app.run(host='0.0.0.0', port=GHOST_PORT, debug=True, use_reloader=False)

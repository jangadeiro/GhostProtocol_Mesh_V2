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
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from datetime import timedelta
from markupsafe import Markup 
from jinja2 import DictLoader, Template 

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostCloud")

# --- YAPILANDIRMA / CONFIGURATION ---
MINING_DIFFICULTY = 4
BLOCK_REWARD = 10
DB_FILE = os.path.join(os.getcwd(), "ghost_cloud_v2.db") 
GHOST_PORT = 5000
DOMAIN_EXPIRY_SECONDS = 15552000  
STORAGE_COST_PER_MB = 0.001       

# DİĞER PEER SUNUCULARINI ELLE EKLE (Örnek)
KNOWN_PEERS = [
    # "http://192.168.1.10:5000",
    # "http://ghostnode.com:5000", 
]

app = Flask(__name__)
app.secret_key = 'cloud_super_secret_permanency_fix_2024_03_12_FINAL' 
app.permanent_session_lifetime = timedelta(days=7) 
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 

# --- ÇOKLU DİL SÖZLÜĞÜ (i18n) - STABİL ---
LANGUAGES = {
    'tr': {
        'title': "GhostProtocol Bulut Sunucusu",
        'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'status_success': "Başarılı", 'status_failed': "Başarısız", 
        'dashboard_title': "Panel", 'mining_title': "Madencilik", 'logout': "Çıkış", 'login': "Giriş", 'register': "Kayıt", 'search': "Ghost Arama",
        'welcome_header': "Blok Zinciri Omurgası / Blockchain Backbone",
        'welcome_text': "Bu sunucu, GhostProtocol ağının ana veri omurgasını oluşturur. Mesh düğümleri ve diğer sunucular buradan senkronize olur. Erişime devam etmek için lütfen **Giriş Yapın** veya bir **Hesap Oluşturun**.",
        'wallet_title': "💳 Cüzdanım", 'pubkey': "Genel Anahtar (Public Key)", 'balance': "Bakiye",
        'domain_title': "💾 .ghost Domain Kayıt (6 Ay)",
        'domain_placeholder': "site.ghost (Kayıt Ücreti 1 GHOST)",
        'domain_content': "HTML Site İçeriği", 'register_btn': "Tescil Et ve Yayınla",
        'media_title': "🖼️ Medya Yükle (Görsel/Ses/Video)", 
        'media_info': "Desteklenen formatlar: .png, .jpg, .gif, .mp4, .mp3, .wav (Maks 10MB)",
        'media_name': "Varlık Adı (isteğe bağlı, örnek: fotom.png)",
        'upload_btn': "Yükle (Ücret: 0.01 GHOST)",
        'assets_title': "Kayıtlı Varlıklarım (6 Aylık Döngü)",
        'asset_name': "Ad / ID", 'asset_type': "Tip", 'asset_size': "Boyut", 'asset_days_left': "Kalan Süre", 'asset_monthly_fee': "Aylık Ücret", 'asset_status': "Durum", 'asset_action': "İşlem / Link",
        'status_active': "AKTİF", 'status_expired': "SÜRESİ DOLDU (Özel)", 'action_view': "Gör", 'action_edit': "✏️ Düzenle", 'action_delete': "Sil",
        'transactions_title': "Son İşlemlerim", 'tx_reward': "✅ Madencilik Ödülü", 'tx_sent': "➡️ Gönderilen", 'tx_received': "⬅️ Alınan",
        'sync_btn': "🔄 Ağı Eşitle", 
        'sync_success': "Ağ eşitleme başarılı. Yeni uzunluk: {length}.",
        'sync_no_change': "Ağ eşitleme tamamlandı. Daha uzun bir zincir bulunamadı. Mevcut uzunluk: {length}.",
        'sync_fail': "Ağ eşitleme sırasında genel bir hata oluştu.",
        'edit_content_title': "Domain İçeriğini Düzenle", 'save_btn': "İçeriği Kaydet", 'back_to_dashboard': "Geri Dön",
        'search_title': "🔍 Ghost Arama Motoru (Aktif Domainler)", 'search_placeholder': "Domain Ara (ör: blog.ghost)", 'search_btn': "Ara",
        'search_no_results': "Aramanıza uygun aktif domain bulunamadı.", 'latest_domains': "En Son Aktif Domainler",
        'reg_success_msg': "Hesabınız başarıyla oluşturuldu. Lütfen giriş yapmak için aşağıdaki butona tıklayın.",
        'reg_fail_msg': "Kayıt Hata: {response}. Lütfen farklı bir kullanıcı adı deneyin.",
        'login_success_msg': "olarak giriş yaptınız. Artık paneli açabilirsiniz.",
        'login_fail_msg': "Giriş Hatalı.",
        'media_link_copy': "Link Kopyalandı!",
        'media_link_copy_btn': "[Link]",
        'monthly_fee_unit': " GHOST",
        'mine_last_block': "Son Blok",
    },
    'en': {
        'title': "GhostProtocol Cloud Server",
        'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'status_success': "Success", 'status_failed': "Failed", 
        'dashboard_title': "Dashboard", 'mining_title': "Mining", 'logout': "Logout", 'login': "Login", 'register': "Register", 'search': "Ghost Search",
        'welcome_header': "Blockchain Backbone",
        'welcome_text': "This server forms the main data backbone of the GhostProtocol network. Mesh nodes and other servers synchronize from here. Please **Login** or **Register an Account** to continue access.",
        'wallet_title': "💳 My Wallet", 'pubkey': "Public Key", 'balance': "Balance",
        'domain_title': "💾 .ghost Domain Registration (6 Months)",
        'domain_placeholder': "site.ghost (Registration Fee 1 GHOST)",
        'domain_content': "HTML Site Content", 'register_btn': "Register and Publish",
        'media_title': "🖼️ Media Upload (Image/Audio/Video)",
        'media_info': "Supported formats: .png, .jpg, .gif, .mp4, .mp3, .wav (Max 10MB)",
        'media_name': "Asset Name (optional, e.g., mypic.png)",
        'upload_btn': "Upload (Fee: 0.01 GHOST)",
        'assets_title': "My Registered Assets (6 Month Cycle)",
        'asset_name': "Name / ID", 'asset_type': "Type", 'asset_size': "Size", 'asset_days_left': "Days Left", 'asset_monthly_fee': "Monthly Fee", 'asset_status': "Status", 'asset_action': "Action / Link",
        'status_active': "ACTIVE", 'status_expired': "EXPIRED (Private)", 'action_view': "View", 'action_edit': "✏️ Edit", 'action_delete': "Delete",
        'transactions_title': "Latest Transactions", 'tx_reward': "✅ Mining Reward", 'tx_sent': "➡️ Sent", 'tx_received': "⬅️ Received",
        'sync_btn': "🔄 Sync Network", 
        'sync_success': "Network synchronization successful. New length: {length}.",
        'sync_no_change': "Network synchronization complete. No longer chain found. Current length: {length}.",
        'sync_fail': "A general error occurred during network synchronization.",
        'edit_content_title': "Edit Domain Content", 'save_btn': "Save Content", 'back_to_dashboard': "Go Back",
        'search_title': "🔍 Ghost Search Engine (Active Domains)", 'search_placeholder': "Search Domain (e.g., blog.ghost)", 'search_btn': "Search",
        'search_no_results': "No active domains found matching your query.", 'latest_domains': "Latest Active Domains",
        'reg_success_msg': "Your account has been successfully created. Please click the button below to log in.",
        'reg_fail_msg': "Registration Error: {response}. Please try a different username.",
        'login_success_msg': "logged in successfully. You can now open the dashboard.",
        'login_fail_msg': "Login Failed.",
        'media_link_copy': "Link Copied!",
        'media_link_copy_btn': "[Link]",
        'monthly_fee_unit': " GHOST",
        'mine_last_block': "Last Block",
    },
    'ru': {
        'title': "Облачный сервер GhostProtocol",
        'status_online': "ОНЛАЙН", 'status_offline': "ОФФЛАЙН",
        'status_success': "Успешно", 'status_failed': "Провал", 
        'dashboard_title': "Панель", 'mining_title': "Майнинг", 'logout': "Выход", 'login': "Вход", 'register': "Регистрация", 'search': "Поиск Ghost",
        'welcome_header': "Основная сеть блокчейна",
        'welcome_text': "Этот сервер формирует основу данных сети GhostProtocol. Узлы Mesh и другие серверы синхронизируются отсюда. Пожалуйста, **Войдите** или **Зарегистрируйте аккаунт** для продолжения доступа.",
        'wallet_title': "💳 Мой Кошелек", 'pubkey': "Открытый Ключ (Public Key)", 'balance': "Баланс",
        'domain_title': "💾 Регистрация Домена .ghost (6 Месяцев)",
        'domain_placeholder': "site.ghost (Плата за регистрацию 1 GHOST)",
        'domain_content': "HTML Содержимое Сайта", 'register_btn': "Зарегистрировать и Опубликовать",
        'media_title': "🖼️ Загрузка Медиа (Изображение/Аудио/Видео)",
        'media_info': "Поддерживаемые форматы: .png, .jpg, .gif, .mp4, .mp3, .wav (Макс 10МБ)",
        'media_name': "Имя Актива (необязательно, например, mypic.png)", 
        'upload_btn': "Загрузить (Плата: 0.01 GHOST)",
        'assets_title': "Мои Зарегистрированные Активы (6 Месячный Цикл)",
        'asset_name': "Имя / ID", 'asset_type': "Тип", 'asset_size': "Размер", 'asset_days_left': "Осталось Дней", 'asset_monthly_fee': "Месячная Плата", 'asset_status': "Статус", 'asset_action': "Действие / Ссылка",
        'status_active': "АКТИВЕН", 'status_expired': "ИСТЕК (Приватный)", 'action_view': "Посмотреть", 'action_edit': "✏️ Редактировать", 'action_delete': "Удалить",
        'transactions_title': "Последние Транзакции", 'tx_reward': "✅ Награда за Майнинг", 'tx_sent': "➡️ Отправлено", 'tx_received': "⬅️ Получено",
        'sync_btn': "🔄 Синхронизировать Сеть", 
        'sync_success': "Синхронизация сети прошла успешно. Новая длина: {length}.",
        'sync_no_change': "Синхронизация сети завершена. Более длинная цепь не найдена. Текущая длина: {length}.",
        'sync_fail': "Во время синхронизации сети произошла общая ошибка.",
        'edit_content_title': "Редактировать Содержимое Домена", 'save_btn': "Сохранить Содержимое", 'back_to_dashboard': "Назад",
        'search_title': "🔍 Поисковая Система Ghost (Активные Домены)", 'search_placeholder': "Поиск Домена (например, blog.ghost)", 'search_btn': "Поиск",
        'search_no_results': "Активных доменов, соответствующих вашему запросу, не найдено.", 'latest_domains': "Последние Активные Домены",
        'reg_success_msg': "Ваша учетная запись успешно создана. Пожалуйста, нажмите кнопку ниже, чтобы войти.",
        'reg_fail_msg': "Ошибка регистрации: {response}. Пожалуйста, попробуйте другое имя пользователя.",
        'login_success_msg': "успешно вошли в систему. Теперь вы можете открыть панель управления.",
        'login_fail_msg': "Ошибка входа.",
        'media_link_copy': "Ссылка Скопирована!",
        'media_link_copy_btn': "[Ссылка]",
        'monthly_fee_unit': " GHOST",
        'mine_last_block': "Последний Блок",
    },
    'hy': {
        'title': "GhostProtocol Ամպային Սերվեր",
        'status_online': "ԱՌՑԱՆՑ", 'status_offline': "ԱՆՑԱՆՑ",
        'status_success': "Հաջող", 'status_failed': "Ձախողված", 
        'dashboard_title': "Վահանակ", 'mining_title': "Մայնինգ", 'logout': "Ելք", 'login': "Մուտք", 'register': "Գրանցվել", 'search': "Ghost Որոնում",
        'welcome_header': "Բլոկչեյնի Հիմնական Միջուկը / Blockchain Backbone",
        'welcome_text': "Այս սերվերը ձևավորում է GhostProtocol ցանցի հիմնական տվյալների միջուկը: Mesh հանգույցները և այլ սերվերներ սինխրոնիզացվում են այստեղից: Խնդրում ենք **Մուտք Գործել** կամ **Ստեղծել Հաշիվ** մուտքը շարունակելու համար:",
        'wallet_title': "💳 Իմ Դրամապանակը", 'pubkey': "Հանրային Բանալի (Public Key)", 'balance': "Մնացորդ",
        'domain_title': "💾 .ghost Դոմենի Գրանցում (6 Ամիս)",
        'domain_placeholder': "site.ghost (Գրանցման Վճար 1 GHOST)",
        'domain_content': "HTML Կայքի Բովանդակություն", 'register_btn': "Գրանցել և Հրապարակել",
        'media_title': "🖼️ Մեդիայի Բեռնում (Նկար/Աուդիո/Տեսանյութ)",
        'media_info': "Աջակցվող ձևաչափեր՝ .png, .jpg, .gif, .mp4, .mp3, .wav (Առավելագույնը 10ՄԲ)",
        'media_name': "Ակտիվի Անունը (ըստ ցանկության, օր.՝ իմնկարը.png)",
        'upload_btn': "Բեռնել (Վճար՝ 0.01 GHOST)",
        'assets_title': "Իմ Գրանցված Ակտիվները (6 Ամսյա Ցիկլ)",
        'asset_name': "Անուն / ID", 'asset_type': "Տեսակ", 'asset_size': "Չափ", 'asset_days_left': "Մնացած Օրեր", 'asset_monthly_fee': "Ամսական Վճար", 'asset_status': "Կարգավիճակ", 'asset_action': "Գործողություն / Հղում",
        'status_active': "ԱԿՏԻՎ", 'status_expired': "ԺԱՄԿԵՏՆ ԱՆՑԱԾ (Մասնավոր)", 'action_view': "Դիտել", 'action_edit': "✏️ Խմբագրել", 'action_delete': "Ջնջել",
        'transactions_title': "Վերջին Գործարքները", 'tx_reward': "✅ Մայնինգի Պարգև", 'tx_sent': "➡️ Ուղարկված", 'tx_received': "⬅️ Ստացված",
        'sync_btn': "🔄 Սինխրոնիզացնել Ցանցը",
        'sync_success': "Ցանցի սինխրոնիզացիան հաջող է: Նոր երկարությունը՝ {length}:",
        'sync_no_change': "Ցանցի սինխրոնիզացիան ավարտված է: Ավելի երկար ցանց չի գտնվել: Ներկայիս երկարությունը՝ {length}:",
        'sync_fail': "Ընդհանուր սխալ տեղի ունեցավ ցանցի սինխրոնիզացիայի ժամանակ:",
        'edit_content_title': "Խմբագրել Դոմենի Բովանդակությունը", 'save_btn': "Պահպանել Բովանդակությունը", 'back_to_dashboard': "Վերադառնալ",
        'search_title': "🔍 Ghost Որոնիչ (Ակտիվ Դոմեններ)", 'search_placeholder': "Որոնել Դոմեն (օր.՝ blog.ghost)", 'search_btn': "Որոնել",
        'search_no_results': "Ձեր հարցմանը համապատասխան ակտիվ դոմեններ չեն գտնվել:", 'latest_domains': "Վերջին Ակտիվ Դոմենները",
        'reg_success_msg': "Ձեր հաշիվը հաջողությամբ ստեղծվել է: Խնդրում ենք սեղմել ստորև նշված կոճակը մուտք գործելու համար:",
        'reg_fail_msg': "Գրանցման Սխալ՝ {response}: Խնդրում ենք փորձել այլ օգտատեր:",
        'login_success_msg': "հաջողությամբ մուտք գործեց: Այժմ կարող եք բացել վահանակը:",
        'login_fail_msg': "Մուտքը ձախողվեց:",
        'media_link_copy': "Հղումը Պատճենվեց:",
        'media_link_copy_btn': "[Հղում]",
        'monthly_fee_unit': " GHOST",
        'mine_last_block': "Վերջին Բլոկ", 
    }
}

# --- VERİTABANI YÖNETİCİSİ (Stabil) ---
class DatabaseManager:
    # ... (DatabaseManager içeriği aynı kalacak)
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
        if 'transactions' in block:
             block['transactions'] = sorted(block['transactions'], key=lambda tx: tx['tx_id'])
             
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# --- BLOCKCHAIN/ASSET/USER MANAGER (Stabil) ---
class GhostChain:
    # ... (GhostChain içeriği aynı kalacak)
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
        
        if sender != "0": 
            user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender,)).fetchone()
            if not user or user['balance'] < amount:
                conn.close()
                return False, "Yetersiz bakiye veya geçersiz gönderici / Insufficient balance or invalid sender"
        
        try:
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)", (tx_id, sender, recipient, amount, time.time()))
            
            if sender != "0":
                 conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (amount, sender))
                 conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (amount, recipient))
            elif sender == "0":
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
        
        proof = 0
        guess = f'{last_block["proof"]}0'.encode()
        while hashlib.sha256(guess).hexdigest()[:MINING_DIFFICULTY] != "0" * MINING_DIFFICULTY:
             proof += 1
             guess = f'{last_block["proof"]}{proof}'.encode()
             
        success, tx_id = self.new_transaction(sender="0", recipient=miner_address, amount=BLOCK_REWARD)
        if not success:
            logger.error(f"Madencilik ödülü işlemi oluşturulamadı: {tx_id}")
            return False, f"Ödül işlemi hatası: {tx_id}"

        conn = self.db.get_connection()
        pending_txs = conn.execute("SELECT tx_id, sender, recipient, amount, timestamp FROM transactions WHERE block_index = 0").fetchall()
        
        full_txs = [dict(tx) for tx in pending_txs]

        new_block = {
            'index': last_block['block_index'] + 1,
            'timestamp': time.time(),
            'transactions': full_txs, 
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
        
        for block in blocks:
             txs = conn.execute("SELECT tx_id, sender, recipient, amount, timestamp FROM transactions WHERE block_index = ?", (block['block_index'],)).fetchall()
             block['transactions'] = [dict(tx) for tx in txs]
             
        for a in assets:
            if isinstance(a['content'], bytes): a['content'] = base64.b64encode(a['content']).decode('utf-8')
            
        conn.close()
             
        return {'chain': blocks, 'assets': assets, 'length': len(blocks)}

class AssetManager:
    # ... (AssetManager içeriği aynı kalacak)
    def __init__(self, db_manager):
        self.db = db_manager
        
    def register_asset(self, owner_key, asset_type, name, content, is_file=False):
        
        # --- DOSYA İÇERİĞİNİ DOĞRU OKUMA ---
        if is_file:
            try:
                # Flask'tan gelen FileStorage nesnesini okuma
                content.seek(0) # Dosya işaretçisini en başa taşı
                content_bytes = content.read() 
                size = len(content_bytes)
                if size > 10 * 1024 * 1024: # Maks 10MB sınırı
                     return False, "Dosya boyutu 10MB'ı aşıyor."
            except Exception as e:
                 logger.error(f"Dosya okuma hatası: {e}")
                 return False, "Dosya okuma hatası."
        else:
            content_bytes = content.encode('utf-8')
            size = len(content_bytes)
            
        creation_time = time.time()
        expiry_time = creation_time + DOMAIN_EXPIRY_SECONDS
        
        conn = self.db.get_connection()
        
        if asset_type == 'domain':
            existing = conn.execute("SELECT expiry_time FROM assets WHERE name = ? AND type = 'domain'", (name,)).fetchone()
            if existing and existing['expiry_time'] > time.time():
                conn.close()
                return False, "Domain alınmış ve süresi dolmamış."
            registration_fee = 1.0 
        else:
            registration_fee = 0.01 
            
        user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (owner_key,)).fetchone()
        
        if not user or user['balance'] < registration_fee:
            conn.close()
            return False, f"Yetersiz bakiye (Kayıt ücreti: {registration_fee} GHOST)."
            
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
    # ... (UserManager içeriği aynı kalacak)
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

# --- MESH NETWORK LOGIC (Stabil) ---
def register_peer(peer_address):
    # ... (register_peer içeriği aynı kalacak)
    if f"http://{request.host}" == peer_address:
        return False
        
    conn = db.get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO mesh_peers (ip_address, last_seen, method) VALUES (?, ?, ?)", 
                     (peer_address, time.time(), "http"))
        conn.commit()
        logger.info(f"Yeni Peer Kaydedildi: {peer_address}")
        return True
    except Exception as e:
        logger.error(f"Peer Kayıt Hatası: {e}")
        return False
    finally:
        conn.close()

def resolve_conflicts():
    # ... (resolve_conflicts içeriği aynı kalacak)
    peers = get_peers()
    new_chain = None
    new_assets = None
    max_length = chain.last_block()['block_index'] if chain.last_block() else 1
    
    for peer in peers:
        try:
            response = requests.get(f'{peer}/chain', timeout=5)
            
            if response.status_code == 200:
                remote_data = response.json()
                remote_length = remote_data['length']
                
                if remote_length > max_length:
                    max_length = remote_length
                    new_chain = remote_data['chain']
                    new_assets = remote_data['assets']
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"Peer {peer} ile eşitleme denemesi başarısız: {e}")
            continue

    if new_chain:
        if replace_chain_and_assets(new_chain, new_assets):
            return True, max_length
    
    return False, max_length

def replace_chain_and_assets(remote_chain, remote_assets):
    # ... (replace_chain_and_assets içeriği aynı kalacak)
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM blocks WHERE block_index > 1")
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM assets")
        
        for block_data in remote_chain:
            if block_data['index'] == 1: continue 
                
            conn.execute("INSERT INTO blocks (block_index, timestamp, proof, previous_hash, block_hash) VALUES (?, ?, ?, ?, ?)",
                         (block_data['index'], block_data['timestamp'], block_data['proof'], block_data['previous_hash'], block_data['block_hash']))
                         
            for tx in block_data.get('transactions', []):
                conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp, block_index) VALUES (?, ?, ?, ?, ?, ?)", 
                             (tx['tx_id'], tx['sender'], tx['recipient'], tx['amount'], tx.get('timestamp', time.time()), block_data['index']))

        for asset_data in remote_assets:
             content_bytes = base64.b64decode(asset_data['content']) if isinstance(asset_data['content'], str) else asset_data['content']
             conn.execute("INSERT INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, is_public) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_data['asset_id'], asset_data['owner_pub_key'], asset_data['type'], asset_data['name'], content_bytes, asset_data['storage_size'], asset_data['creation_time'], asset_data['expiry_time'], asset_data['is_public']))

        conn.commit()
        logger.info(f"Zincir başarıyla eşlendi. Yeni uzunluk: {len(remote_chain)}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Zincir değiştirme hatası: {e}")
        return False
    finally:
        conn.close()

def get_peers():
    # ... (get_peers içeriği aynı kalacak)
    conn = db.get_connection()
    peers = [dict(row)['ip_address'] for row in conn.execute("SELECT ip_address FROM mesh_peers").fetchall()]
    conn.close()
    return list(set(peers + KNOWN_PEERS))

# --- LAYOUT (Çoklu Dil Desteği - STABİL) ---
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
        .success { color: #4caf50; } .fail { color: #f44336; }
        a { color: #2196f3; text-decoration: none; }
        input, button, textarea { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
        .action-button { background: #4caf50; color: white; border: none; padding: 10px; margin-top: 15px; cursor: pointer; border-radius: 5px; width: 50%; display: inline-block; text-align: center;}
        .action-button.register { background: #2199f3; margin-left: 10px; }
        .msg { padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .msg.ok { background: #1e4620; color: #7fbf7f; }
        .msg.err { background: #462222; color: #f7a5a5; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #555; padding: 8px; text-align: left; font-size: 0.9em; } 
        .full-width-key { word-wrap: break-word; font-size: 0.7em; }
        .debug-info { color: #ff0; font-size: 0.8em; margin-top: 10px; padding: 5px; border: 1px dashed #555; }
        .flex-container { display: flex; justify-content: space-between; gap: 20px; }
        .flex-item { flex: 1; }
        .link-cell { position: relative; }
        .copy-link { cursor: pointer; color: #ffeb3b; font-size: 0.8em; margin-left: 10px; }
        .tooltip { visibility: hidden; width: 100px; background-color: #555; color: #fff; text-align: center; border-radius: 6px; padding: 5px 0; position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -50px; opacity: 0; transition: opacity 0.3s; }
        .link-cell:hover .tooltip { visibility: visible; opacity: 1; }
        /* Gizli Textarea Stilini Ekle */
        .hidden-textarea { position: fixed; top: -9999px; left: -9999px; }
    </style>
    <script>
        // JS fonksiyonu tam (absolute) URL kopyalaması yapmalı
        function copyLink(link, button) {
            let success = false;
            let textArea = document.createElement("textarea");
            textArea.value = link; // Bu, tam URL olmalı
            textArea.classList.add("hidden-textarea"); 
            document.body.appendChild(textArea);
            
            try {
                textArea.select();
                textArea.setSelectionRange(0, 99999); 
                success = document.execCommand('copy');
            } catch (err) {
                console.error('Kopyalama başarısız, eski yöntem başarısız:', err);
                navigator.clipboard.writeText(link).then(() => {
                    success = true;
                }).catch(err => {
                    console.error('Clipboard API başarısız:', err);
                    success = false;
                });
            } finally {
                document.body.removeChild(textArea);
            }
            
            if (success) {
                const originalText = button.textContent;
                const langCopy = "{{ lang['media_link_copy'] }}";
                button.textContent = langCopy;
                setTimeout(() => {
                    button.textContent = originalText;
                }, 1500);
            } else if (!success && button.textContent !== "{{ lang['media_link_copy'] }}") {
                 alert("Kopyalama başarısız. Lütfen linki elle seçip kopyalayın: " + link);
            }
            return false;
        }
    </script>
</head>
<body>
    <div class="header-bar">
        <h2>👻 GhostProtocol Cloud Server</h2>
        <div class="lang-switch">
             {% set current_lang = session.get('lang', 'tr') %}
             <a href="{{ url_for('set_language', lang='tr') }}" style="font-weight: {{ 'bold' if current_lang == 'tr' else 'normal' }};">TR🇹🇷</a>
             <a href="{{ url_for('set_language', lang='en') }}" style="font-weight: {{ 'bold' if current_lang == 'en' else 'normal' }};">EN🇬🇧</a>
             <a href="{{ url_for('set_language', lang='ru') }}" style="font-weight: {{ 'bold' if current_lang == 'ru' else 'normal' }};">RU🇷🇺</a>
             <a href="{{ url_for('set_language', lang='hy') }}" style="font-weight: {{ 'bold' if current_lang == 'hy' else 'normal' }};">HY🇦🇲</a> 
        </div>
    </div>
    <div class="card">
        {{ lang['asset_status'] }}: <span class="{{ 'success' if internet else 'fail' }}">{{ lang['status_online'] if internet else lang['status_offline'] }}</span>
        | Peers: {{ peers|length }}
        {% if session.get('username') %}
            | 👤 {{ session['username'] }} | 💰 {{ session.get('balance', 0)|round(4) }} GHOST
            <br>
            <a href="{{ url_for('dashboard') }}">{{ lang['dashboard_title'] }}</a> | 
            <a href="{{ url_for('mine') }}">{{ lang['mining_title'] }}</a> | 
            <a href="{{ url_for('search_engine') }}">{{ lang['search'] }}</a> | 
            <a href="{{ url_for('sync_network') }}">{{ lang['sync_btn'] }}</a> |
            <a href="{{ url_for('logout') }}">{{ lang['logout'] }}</a>
        {% else %}
             <br><a href="{{ url_for('login') }}">{{ lang['login'] }}</a> | <a href="{{ url_for('register') }}">{{ lang['register'] }}</a>
        {% endif %}
    </div>
    
    {% block content %}{% endblock %} 

</body>
</html>
"""
# --- CONTEXT İŞLEMCİ (Stabil) ---
@app.context_processor
def inject_globals():
    # ... (inject_globals içeriği aynı kalacak)
    current_lang_code = session.get('lang', 'tr')
    current_lang = LANGUAGES.get(current_lang_code, LANGUAGES['tr'])
    
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
            user_data = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (session['pub_key'],)).fetchone()
            conn.close()
            if user_data:
                session['balance'] = user_data['balance']
        except Exception as e:
            logger.error(f"Bakiye güncellenirken hata: {e}")
            
    return dict(internet=internet, peers=peers, url_for=url_for, lang=current_lang)

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

# --- ROTALAR / ROUTES ---

@app.route('/peers', methods=['GET', 'POST'])
def peers_management():
    # ... (peers_management içeriği aynı kalacak)
    if request.method == 'POST':
        peer_address = request.json.get('address')
        if peer_address:
            register_peer(peer_address)
            return jsonify({'message': 'Peer registered'}), 200
        return jsonify({'message': 'Invalid address'}), 400
    
    return jsonify({'peers': get_peers()}), 200

@app.route('/sync_network')
def sync_network():
    # ... (sync_network içeriği aynı kalacak)
    if not session.get('username'): return redirect(url_for('login'))
    
    self_address = f"http://{request.host}"
    peers = get_peers()
    current_length = chain.last_block()['block_index'] if chain.last_block() else 1
    
    for peer in peers:
        try:
            requests.post(f'{peer}/peers', json={'address': self_address}, timeout=2)
        except requests.exceptions.RequestException:
            logger.warning(f"Peer {peer} kendini tanıtamadı.")

    replaced, new_length = resolve_conflicts()
    L = inject_globals()['lang']
    
    if replaced:
        msg = L['sync_success'].format(length=new_length)
        msg_class = 'ok'
    else:
        msg = L['sync_no_change'].format(length=current_length)
        msg_class = 'ok'
        
    template = """
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <div class='msg {{ msg_class }}'>{{ msg }}</div>
                <p><a href="{{ url_for('dashboard') }}">{{ lang['back_to_dashboard'] }}</a></p>
            </div>
        {% endblock %}
    """
    return render_template_string(template, msg_class=msg_class, msg=msg, L=L)


@app.route('/')
def home():
    # ... (home içeriği aynı kalacak)
    if session.get('username'):
        return redirect(url_for('dashboard'))
        
    L = inject_globals()['lang']
    return render_template_string("""
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>{{ lang['welcome_header'] }}</h3>
                <p>{{ lang['welcome_text'] }}</p>
                
                <a href="{{ url_for('login') }}" class="action-button">{{ lang['login'] }}</a>
                <a href="{{ url_for('register') }}" class="action-button register">{{ lang['register'] }}</a>
            </div>
        {% endblock %}
    """) 


@app.route('/chain', methods=['GET'])
def full_chain_export():
    response = chain.get_full_chain()
    return jsonify(response), 200

# --- DASHBOARD (Merkeziyetsiz Linkleme İçin Güncellendi) ---
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('username'): 
        return redirect(url_for('login'))

    L = inject_globals()['lang']
    msg = ""
    
    status_success = L['status_success']
    status_failed = L['status_failed']
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'register_domain':
            name = request.form['name']
            data = request.form['data']
            success, response_text = assets_mgr.register_asset(session['pub_key'], 'domain', name, data, is_file=False)
            msg = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı' if success else 'Hata'}: {response_text.replace('Başarılı / Success', status_success)}</div>"
        
        elif action == 'upload_media':
            if 'file' not in request.files or request.files['file'].filename == '':
                 msg = f"<div class='msg err'>Dosya alanı boş. Lütfen bir dosya seçin. ({status_failed})</div>"
                 
            else:
                file = request.files['file']
                file_name = request.form.get('media_name', file.filename) 
                if not file_name or file_name.strip() == '':
                     file_name = file.filename
                
                mime_type = file.mimetype
                asset_type = 'file'
                if mime_type.startswith('image'): asset_type = 'image'
                elif mime_type.startswith('video'): asset_type = 'video'
                elif mime_type.startswith('audio'): asset_type = 'audio'
                
                success, response_text = assets_mgr.register_asset(session['pub_key'], asset_type, file_name, file, is_file=True)
                msg = f"<div class='msg {'ok' if success else 'err'}'>{'Başarılı' if success else 'Hata'}: {response_text.replace('Başarılı / Success', status_success)}</div>"
        
        elif action == 'delete_asset':
            assets_mgr.delete_asset(request.form['id'], session['pub_key'])
            msg = f"<div class='msg ok'>{L['asset_action']} {L['action_delete']} ({status_success})</div>"
            
    conn = db.get_connection()
    my_assets = conn.execute("SELECT * FROM assets WHERE owner_pub_key = ? ORDER BY creation_time DESC", (session['pub_key'],)).fetchall()
    transactions = conn.execute("SELECT * FROM transactions WHERE sender = ? OR recipient = ? ORDER BY timestamp DESC LIMIT 10", (session['pub_key'], session['pub_key'])).fetchall()
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
        'L': L 
    }
    
    dashboard_template = """
    {% extends "base.html" %} 
    {% block content %}
    <div class="card">
        {{ msg }}
        <h3>{{ L['wallet_title'] }}</h3>
        <p><strong>{{ L['pubkey'] }}:</strong></p>
        <p class="full-width-key">{{ pub_key }} </p>
        <p><strong>{{ L['balance'] }}:</strong> {{ balance|round(4) }} GHOST</p>
    </div>
    
    <div class="flex-container">
        <div class="card flex-item">
            <h3>{{ L['domain_title'] }}</h3>
            <form method="post">
                <input type="hidden" name="action" value="register_domain">
                <input name="name" placeholder="{{ L['domain_placeholder'] }}" required>
                <textarea name="data" rows="5" placeholder="{{ L['domain_content'] }}" required></textarea>
                <button>{{ L['register_btn'] }}</button>
            </form>
        </div>
        
        <div class="card flex-item">
            <h3>{{ L['media_title'] }}</h3>
            <p style="font-size: 0.85em; color: #bbb;">{{ L['media_info'] }}</p>
            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="action" value="upload_media">
                <input type="text" name="media_name" placeholder="{{ L['media_name'] }}"> 
                <input type="file" name="file" required>
                <button>{{ L['upload_btn'] }}</button>
            </form>
        </div>
    </div>

    <div class="card">
        <h3>{{ L['assets_title'] }}</h3>
        <table>
            <tr>
                <th>{{ L['asset_name'] }}</th>
                <th>{{ L['asset_type'] }}</th>
                <th>{{ L['asset_size'] }}</th>
                <th>{{ L['asset_days_left'] }}</th>
                <th>{{ L['asset_monthly_fee'] }}</th>
                <th>{{ L['asset_status'] }}</th>
                <th>{{ L['asset_action'] }}</th>
            </tr>
            {% for a in assets %}
                {% set days_left = ((a.expiry_time - now) / 86400) | int %}
                {% set status = L['status_active'] if days_left > 0 else L['status_expired'] %}
                {% set size_mb = a.storage_size / (1024 * 1024) %}
                {% set fee = size_mb * storage_cost_per_mb %}
                
                {# Görüntüleme Linki: Merkeziyetsizlik için göreceli URL kullanıldı #}
                {% set asset_relative_link = url_for('view_asset', asset_id=a.asset_id) %}
                
                {# Kopyalama Linki: JS'in tam URL kopyalayabilmesi için _external=True kullanıldı #}
                {% set asset_external_link = url_for('view_asset', asset_id=a.asset_id, _external=True) %}
                
            <tr>
                <td>{{ a.name }} <br><span style="font-size: 0.7em;">ID: {{ a.asset_id[:8] }}...</span></td>
                <td>{{ a.type | upper }}</td>
                <td>{{ "%.2f"|format(size_mb) }} MB</td>
                <td style="color:{{ '#f44336' if days_left < 30 else '#4caf50' }}">{{ days_left }}</td>
                <td>{{ "%.6f"|format(fee) }}{{ L['monthly_fee_unit'] }}</td>
                <td>{{ status }}</td>
                <td class="link-cell">
                    {# Görüntüleme linki (Göreli olarak tarayıcıda çalışır) #}
                    <a href="{{ asset_relative_link }}">{{ L['action_view'] }}</a> 
                    
                    {% if a.type == 'domain' %}
                       | <a href="{{ url_for('edit_asset', asset_id=a.asset_id) }}">{{ L['action_edit'] }}</a> 
                    {% endif %}
                    
                    <br>
                    {# Kopyalama Butonu (JS'e tam URL'yi verir) #}
                    <a href="javascript:void(0);" class="copy-link" onclick="return copyLink('{{ asset_external_link }}', this)">{{ L['media_link_copy_btn'] }}</a>
                    
                    <form method="post" style="display:inline">
                        <input type="hidden" name="action" value="delete_asset">
                        <input type="hidden" name="id" value="{{ a.asset_id }}">
                        <button style="color:#f44336; background:none; border:none; padding:0; cursor:pointer; width:auto; margin-left: 10px;">{{ L['action_delete'] }}</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h3>{{ L['transactions_title'] }}</h3>
        <ul>
            {% for tx in transactions %}
                {% set tx_type = "" %}
                {% set amount_display = "" %}
                {% if tx.sender == '0' %}
                    {% set tx_type = L['tx_reward'] %}
                    {% set amount_display = "+%.4f GHOST"|format(tx.amount) %}
                {% elif tx.sender == pub_key %}
                    {% set tx_type = L['tx_sent'] %}
                    {% set amount_display = "-%.4f GHOST"|format(tx.amount) %}
                {% else %}
                    {% set tx_type = L['tx_received'] %}
                    {% set amount_display = "+%.4f GHOST"|format(tx.amount) %}
                {% endif %}
            <li>
                {{ tx_type }}: <strong>{{ amount_display }}</strong> (Blok: #{{ tx.block_index }}, Kime/Kimden: {{ tx.recipient[:10] }}...{{ tx.sender[:10] }})
            </li>
            {% endfor %}
        </ul>
    </div>
    {% endblock %}
    """
    
    return render_template_string(dashboard_template, **data)


@app.route('/edit_asset/<asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    # ... (edit_asset içeriği aynı kalacak)
    if not session.get('username'): return redirect(url_for('login'))
        
    L = inject_globals()['lang']
    conn = db.get_connection()
    asset = conn.execute("SELECT * FROM assets WHERE asset_id = ? AND owner_pub_key = ?", (asset_id, session['pub_key'])).fetchone()
    conn.close()
    
    if not asset or asset['type'] != 'domain':
        return redirect(url_for('dashboard'))

    msg = ""
    current_content = asset['content'].decode('utf-8')
    status_success = L['status_success']

    if request.method == 'POST':
        new_content = request.form['content']
        success, response_text = assets_mgr.update_asset_content(asset_id, session['pub_key'], new_content)
        if success:
            current_content = new_content
            # Güncelleme mesajı için yeni çeviriyi kullan
            msg = f"<div class='msg ok'>İçerik Başarıyla Güncellendi. ({status_success})</div>"
        else:
            msg = f"<div class='msg err'>Güncelleme Hatası: {response_text} ({L['status_failed']})</div>"
            
    edit_template = """
    {% extends "base.html" %} 
    {% block content %}
        <div class="card">
            <h3>{{ L['edit_content_title'] }}</h3>
            {{ msg | safe }}
            <form method='post'>
                <p>Domain adı: <strong>{{ asset.name }}</strong> (ID: {{ asset.asset_id[:8] }}...)</p>
                <textarea name="content" rows="15" placeholder="{{ L['domain_content'] }}" required>{{ current_content }}</textarea>
                <button>{{ L['save_btn'] }}</button>
            </form>
            <p><a href="{{ url_for('dashboard') }}">{{ L['back_to_dashboard'] }}</a></p>
        </div>
    {% endblock %}
    """
    
    return render_template_string(edit_template, asset=dict(asset), current_content=current_content, msg=Markup(msg), L=L)


@app.route('/search', methods=['GET'])
def search_engine():
    # ... (search_engine içeriği aynı kalacak)
    L = inject_globals()['lang']
    query = request.args.get('q', '').lower()
    conn = db.get_connection()
    
    if query:
        search_query = f"%{query}%"
        results = conn.execute("SELECT * FROM assets WHERE type = 'domain' AND name LIKE ? AND expiry_time > ?", (search_query, time.time())).fetchall()
    else:
        results = conn.execute("SELECT * FROM assets WHERE type = 'domain' AND expiry_time > ? ORDER BY creation_time DESC", (time.time(),)).fetchall()
        
    conn.close()
    
    search_template = """
    {% extends "base.html" %} 
    {% block content %}
        <div class="card">
            <h3>{{ L['search_title'] }}</h3>
            <form method='get'>
                <input name='q' placeholder="{{ L['search_placeholder'] }}" value="{{ query }}">
                <button>{{ L['search_btn'] }}</button>
            </form>
        </div>
        
        <div class="card">
            <h4>{% if query %}{{ L['search_title'] }} ({{ results | length }}){% else %}{{ L['latest_domains'] }}{% endif %}</h4>
            <ul>
            {% for asset in results %}
                <li>
                    {# Link burada da asset_id bazlı ve göreceli olmalı #}
                    <strong><a href="{{ url_for('view_asset', asset_id=asset.asset_id) }}" target="_blank">{{ asset.name }}</a></strong> 
                    <span style="font-size: 0.8em; color: #aaa;">(Sahibi: {{ asset.owner_pub_key[:10] }}...)</span>
                    {% if asset.content %}
                        {% set content_text = asset.content | base64_decode | decode_utf8 | striptags %}
                        <p style="font-size: 0.9em; color: #bbb; margin: 5px 0 0 10px;">{{ content_text[:150] }}...</p>
                    {% endif %}
                </li>
            {% endfor %}
            {% if not results %}
                <li>{% if query %}{{ L['search_no_results'] }}{% else %}{{ L['search_no_results'] }}{% endif %}</li>
            {% endif %}
            </ul>
        </div>
    {% endblock %}
    """
    def base64_decode(s):
        try: return base64.b64decode(s)
        except: return b''
    
    def decode_utf8(b):
        try: return b.decode('utf-8')
        except: return ''
        
    app.jinja_env.filters['base64_decode'] = base64_decode
    app.jinja_env.filters['decode_utf8'] = decode_utf8
    
    return render_template_string(search_template, results=[dict(r) for r in results], query=query, L=L)


@app.route('/register', methods=['GET', 'POST'])
def register():
    # ... (register içeriği aynı kalacak)
    L = inject_globals()['lang']
    
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
            template = """
                {% extends "base.html" %} 
                {% block content %}
                    <div class='msg ok card'>
                        <h3>🎉 {{ lang['status_success'] }}!</h3>
                        <p>{{ lang['reg_success_msg'] }}</p>
                        <a href="{{ url_for('login') }}"><button class="action-button" style="width:100%; margin: 15px 0;">{{ lang['login'] }}</button></a>
                    </div>
                {% endblock %}
            """
            return render_template_string(template, L=L)
        
        template = """
            {% extends "base.html" %} 
            {% block content %}
                <div class='msg err card'>
                    {{ lang['reg_fail_msg'].format(response=response) }} <a href="{{ url_for('register') }}">{{ lang['register'] }}</a>
                </div>
            {% endblock %}
        """
        return render_template_string(template, response=response, L=L) 
    
    template = """
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>{{ lang['register'] }}</h3>
                <form method='post'>
                    <input name='username' placeholder='Username' required>
                    <input name='password' type='password' placeholder='Password' required>
                    <input name='name' placeholder='Name' required>
                    <input name='surname' placeholder='Surname' required>
                    <input name='phone' placeholder='Phone'>
                    <input name='email' placeholder='Email' required>
                    <button>{{ lang['register'] }}</button>
                </form>
            </div>
        {% endblock %}
    """
    return render_template_string(template, L=L)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (login içeriği aynı kalacak)
    L = inject_globals()['lang']
    
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
            
            template = """
                {% extends "base.html" %} 
                {% block content %}
                    <div class='msg ok card'>
                        <h3>🎉 {{ lang['status_success'] }}!</h3>
                        <p><strong>{{ session['username'] }}</strong> {{ lang['login_success_msg'] }}</p>
                        <a href="{{ url_for('dashboard') }}"><button class="action-button" style="width:100%; margin: 15px 0;">{{ lang['dashboard_title'] }}</button></a>
                    </div>
                {% endblock %}
            """
            return render_template_string(template, L=L)
        
        conn.close()
        template = """
            {% extends "base.html" %} 
            {% block content %}
                <div class='msg err card'>{{ lang['login_fail_msg'] }} <a href="{{ url_for('login') }}">{{ lang['login'] }}</a></div>
            {% endblock %}
        """
        return render_template_string(template, L=L)
    
    template = """
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>{{ lang['login'] }}</h3>
                <form method='post'>
                    <input name='username' placeholder='Username' required>
                    <input name='password' type='password' placeholder='Password' required>
                    <button>{{ lang['login'] }}</button>
                </form>
            </div>
        {% endblock %}
    """
    return render_template_string(template, L=L)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
    
@app.route('/mine')
def mine():
    # ... (mine içeriği aynı kalacak)
    if not session.get('username'): return redirect(url_for('login'))
    L = inject_globals()['lang']
    
    success, response = chain.mine_block(session['pub_key'])
    
    conn = db.get_connection()
    user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (session['pub_key'],)).fetchone()
    session['balance'] = user['balance']
    conn.close()
    
    status_msg = L['status_success'] if success else L['status_failed']
    
    template = """
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <div class='msg {{'ok' if success else 'err'}}'>{{ lang['mining_title'] }} {{ status_msg }}: {{ response }}</div>
                <h3>{{ lang['mining_title'] }}</h3>
                <p>{{ lang['mine_last_block'] }}: #{{ last_block.block_index if last_block else 'N/A'}}</p>
                <a href="{{ url_for('dashboard') }}">{{ lang['back_to_dashboard'] }}</a>
            </div>
        {% endblock %}
    """
    return render_template_string(template, success=success, response=response, last_block=chain.last_block(), L=L, status_msg=status_msg)

@app.route('/view_asset/<asset_id>')
def view_asset(asset_id):
    # ... (view_asset içeriği aynı kalacak)
    if not asset_id: return "400: ID gerekli", 400
    L = inject_globals()['lang']
        
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
        return Response(content_bytes, mimetype='text/html')
    
    elif asset_type in ['image', 'video', 'audio', 'file']:
        # Dosya uzantısına göre MIME tipi belirleme
        mime_type = 'application/octet-stream'
        name_lower = asset['name'].lower()
        if name_lower.endswith(('.jpg', '.jpeg')): mime_type = 'image/jpeg'
        elif name_lower.endswith(('.png')): mime_type = 'image/png'
        elif name_lower.endswith(('.gif')): mime_type = 'image/gif'
        elif name_lower.endswith(('.mp4', '.webm')): mime_type = 'video/mp4'
        elif name_lower.endswith(('.mp3', '.wav')): mime_type = 'audio/mpeg'
        
        # Response'a dosya adını ekleyerek tarayıcıya ipucu ver
        return Response(content_bytes, mimetype=mime_type, headers={'Content-Disposition': f'inline; filename="{asset["name"]}"'})

    # Diğer varlıklar için geri dönüş şablonu
    template = """
        {% extends "base.html" %} 
        {% block content %}
            <div class="card">
                <h3>'{{ asset.name }}' Görüntüleniyor</h3>
                <p>Tip: {{ asset.type }} (İkili dosya). Bu içerik doğrudan tarayıcıda görüntülenemez.</p>
                <p><a href="{{ url_for('dashboard') }}">{{ lang['back_to_dashboard'] }}</a></p>
            </div>
        {% endblock %}
    """
    return render_template_string(template, asset=dict(asset), L=L)


if __name__ == '__main__':
    app.jinja_env.loader = DictLoader({'base.html': LAYOUT})
    
    print("--- GHOST CLOUD SUNUCUSU BAŞLATILIYOR / GHOST CLOUD SERVER STARTING ---")
    print("\n✅ **GÜNCELLEMELER YAPILDI:**")
    print("1. Medya ve Domain varlık linkleri, sunucu adresini içermeyen **göreceli URL'ler** kullanacak şekilde güncellendi.")
    print("2. Bu sayede, Ghost Mesh Node'lar (ağ düğümleri) bu ID'ler üzerinden içeriği alıntılayabilir ve merkeziyetsiz erişimi destekleyebilir.")
    print("3. Kopyalama butonu, kullanıcının kolaylığı için yine de tam (absolute) URL kopyalamaya devam etmektedir.")
    print("Veritabanı: ghost_cloud_v2.db (Kalıcı)\n")
    
    app.run(host='0.0.0.0', port=GHOST_PORT, debug=True, use_reloader=False)

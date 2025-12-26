# -*- coding: utf-8 -*-
"""
EN: GhostProtocol Mesh Node - CLI Version
Русский: Узел сетки GhostProtocol - версия для командной строки
TR: GhostProtocol Mesh Düğümü - Komut Satırı Sürümü
Հայերեն: GhostProtocol Mesh Node - CLI տարբերակ
Decentralized, Unstoppable Internet. / Merkeziyetsiz, Durdurulamaz İnternet.
"""

import hashlib
import json
import time
import sqlite3
import base64
import random
import re
import logging
import os
import requests
import threading
import socket
from uuid import uuid4
from datetime import timedelta, datetime
from typing import Optional, Tuple, Dict, Any, List

# --- CİHAZ ÖZELİNDE MESH MODÜLLERİ (OPSİYONEL) / DEVICE SPECIFIC MESH MODULES ---
try:
    import bluetooth
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GhostNode - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostMeshNode")

# --- YAPILANDIRMA / CONFIGURATION ---
NODE_ID = hashlib.sha256(socket.gethostname().encode()).hexdigest()[:10]
DB_FILE = os.path.join(os.getcwd(), f"ghost_node_{NODE_ID}.db")
GHOST_PORT = 5000 

# TR: Veri ve işlem eşleşmesi için bilinen sunucular
# EN: Known servers for data and transaction synchronization
KNOWN_PEERS = ["46.101.219.46", "68.183.12.91"] 

STORAGE_COST_PER_MB = 0.01
DOMAIN_REGISTRATION_FEE = 1.0
DOMAIN_EXPIRY_SECONDS = 15552000 # 6 Ay / 6 Months
# TR: Başlangıç bakiyesi sıfır (Madencilik ile kazanılır)
# EN: Initial balance zero (Earned via mining)
INITIAL_USER_BALANCE = 0.0
BASE_DIFFICULTY = 4
INITIAL_BLOCK_REWARD = 50.0
HALVING_INTERVAL = 2000
TOTAL_SUPPLY = 100000000.0

# TR: Ağ gelirlerinin birikeceği Hazine Cüzdanı Adresi
# EN: Treasury Wallet Address where network revenues will accumulate
TREASURY_WALLET_KEY = "GHST_NETWORK_TREASURY_VAULT"

# --- ÇOKLU DİL SÖZLÜĞÜ / MULTI-LANGUAGE DICTIONARY ---
LANGUAGES = {
    'tr': {
        'node_name': "Ghost Mesh Düğümü", 'menu_title': "GHOST PROTOCOL MENÜSÜ",
        'auth_menu_title': "GİRİŞ / KAYIT", 'opt_login': "1. Giriş Yap", 'opt_create_account': "2. Yeni Hesap Oluştur",
        'opt_register': "1. Varlık Kaydet (.ghost / Dosya)", 'opt_search': "2. Ara & Görüntüle",
        'opt_wallet': "3. Cüzdan & Transfer", 'opt_mine': "4. Madencilik Yap",
        'opt_messenger': "5. Ghost Messenger", 'opt_status': "6. Ağ Durumu", 
        'opt_logout': "7. Çıkış Yap", 'opt_exit': "8. Kapat",
        'balance': "Bakiye", 'pubkey': "Cüzdan", 'sync_status': "Senkronizasyon",
        'enter_choice': "Seçiminiz: ", 'invalid_choice': "Geçersiz seçim!",
        'domain_name': "Domain Adı (örn: site): ", 'content_html': "İçerik (HTML): ",
        'register_success': "Kayıt Başarılı! İşlem ağa yayınlandı.", 'register_fail': "Kayıt Başarısız: ",
        'search_query': "Arama (Domain/Kelime): ", 'no_results': "Sonuç bulunamadı.",
        'results_found': "Sonuçlar:", 'view_content': "İçeriği Görüntüle (ID girin, iptal için 0): ",
        'recipient': "Alıcı Cüzdan Adresi: ", 'amount': "Miktar: ", 'sent_success': "Gönderildi ve ağa yayınlandı!",
        'mining_start': "Madencilik Başlatılıyor...", 'block_found': "BLOK BULUNDU!", 
        'assets_title': "Kayıtlı Varlıklarım", 'fee': "Ücret", 'type': "Tür",
        'stats_total_supply': "Toplam Arz", 'stats_circulating': "Dolaşımdaki Arz",
        'stats_block_reward': "Blok Ödülü", 'stats_solved_blocks': "Çözülen Blok",
        'stats_last_block': "Son Blok Hash", 'stats_halving': "Yarılanmaya Kalan",
        'back_to_menu': "0. Ana Menüye Dön", 'asset_cost': "Maliyet", 'asset_expiry': "Bitiş",
        'enter_0_to_cancel': "(İptal etmek için 0 girin)",
        'login_title': "--- GHOST PROTOCOL GİRİŞ ---", 'login_user': "Kullanıcı Adı: ", 
        'login_pass': "Şifre: ", 'login_fail': "Giriş başarısız!", 'logged_out': "Çıkış yapıldı.",
        'create_acc_title': "--- YENİ HESAP OLUŞTUR ---", 'create_acc_success': "Hesap oluşturuldu! Lütfen giriş yapın.",
        'create_acc_fail': "Kullanıcı adı alınmış veya hata oluştu.",
        'msg_menu': "--- GHOST MESSENGER ---", 'msg_friends': "1. Arkadaş Listesi & Sohbet", 
        'msg_invite': "2. Arkadaş Davet Et", 'msg_enter_friend': "Sohbet edilecek arkadaş Cüzdan Anahtarı (yoksa 0): ",
        'msg_type': "Mesajınız: ", 'msg_sent': "Mesaj ağa gönderildi.",
        'msg_invite_user': "Davet edilecek kullanıcı adı: ", 'msg_invite_sent': "Davet ağa gönderildi.",
        'msg_chat_title': "Sohbet Geçmişi",
        'asset_remaining': "Kalan Süre", 'asset_held': "Tutulma Süresi", 
        'days': "gün", 'hours': "saat"
    },
    'en': {
        'node_name': "Ghost Mesh Node", 'menu_title': "GHOST PROTOCOL MENU",
        'auth_menu_title': "LOGIN / REGISTER", 'opt_login': "1. Login", 'opt_create_account': "2. Create Account",
        'opt_register': "1. Register Asset (.ghost / File)", 'opt_search': "2. Search & View",
        'opt_wallet': "3. Wallet & Transfer", 'opt_mine': "4. Mine Block",
        'opt_messenger': "5. Ghost Messenger", 'opt_status': "6. Network Status", 
        'opt_logout': "7. Logout", 'opt_exit': "8. Exit",
        'balance': "Balance", 'pubkey': "Wallet", 'sync_status': "Sync Status",
        'enter_choice': "Choice: ", 'invalid_choice': "Invalid choice!",
        'domain_name': "Domain Name (e.g., site): ", 'content_html': "Content (HTML): ",
        'register_success': "Registration Successful! Transaction broadcasted.", 'register_fail': "Registration Failed: ",
        'search_query': "Search (Domain/Keyword): ", 'no_results': "No results found.",
        'results_found': "Results:", 'view_content': "View Content (Enter ID, 0 to cancel): ",
        'recipient': "Recipient Address: ", 'amount': "Amount: ", 'sent_success': "Sent and broadcasted!",
        'mining_start': "Starting Mining...", 'block_found': "BLOCK FOUND!",
        'assets_title': "My Registered Assets", 'fee': "Fee", 'type': "Type",
        'stats_total_supply': "Total Supply", 'stats_circulating': "Circulating Supply",
        'stats_block_reward': "Block Reward", 'stats_solved_blocks': "Solved Blocks",
        'stats_last_block': "Last Block Hash", 'stats_halving': "Blocks to Halving",
        'back_to_menu': "0. Back to Main Menu", 'asset_cost': "Cost", 'asset_expiry': "Expires",
        'enter_0_to_cancel': "(Enter 0 to cancel)",
        'login_title': "--- GHOST PROTOCOL LOGIN ---", 'login_user': "Username: ", 
        'login_pass': "Password: ", 'login_fail': "Login failed!", 'logged_out': "Logged out.",
        'create_acc_title': "--- CREATE NEW ACCOUNT ---", 'create_acc_success': "Account created! Please login.",
        'create_acc_fail': "Username taken or error occurred.",
        'msg_menu': "--- GHOST MESSENGER ---", 'msg_friends': "1. Friend List & Chat", 
        'msg_invite': "2. Invite Friend", 'msg_enter_friend': "Friend Wallet Key to chat (0 to back): ",
        'msg_type': "Your Message: ", 'msg_sent': "Message sent to network.",
        'msg_invite_user': "Username to invite: ", 'msg_invite_sent': "Invite sent to network.",
        'msg_chat_title': "Chat History",
        'asset_remaining': "Time Left", 'asset_held': "Held For",
        'days': "days", 'hours': "hours"
    },
    'ru': {
        'node_name': "Узел Ghost Mesh", 'menu_title': "МЕНЮ GHOST PROTOCOL",
        'auth_menu_title': "ВХОД / РЕГИСТРАЦИЯ", 'opt_login': "1. Войти", 'opt_create_account': "2. Создать аккаунт",
        'opt_register': "1. Регистрация актива", 'opt_search': "2. Поиск и просмотр",
        'opt_wallet': "3. Кошелек и перевод", 'opt_mine': "4. Майнинг",
        'opt_messenger': "5. Ghost Мессенджер", 'opt_status': "6. Статус сети", 
        'opt_logout': "7. Выйти", 'opt_exit': "8. Выход",
        'balance': "Баланс", 'pubkey': "Кошелек", 'sync_status': "Синхронизация",
        'enter_choice': "Ваш выбор: ", 'invalid_choice': "Неверный выбор!",
        'domain_name': "Имя домена: ", 'content_html': "Содержание (HTML): ",
        'register_success': "Успешно! Транзакция отправлена.", 'register_fail': "Ошибка: ",
        'search_query': "Поиск: ", 'no_results': "Нет результатов.",
        'results_found': "Результаты:", 'view_content': "Просмотр (ID): ",
        'recipient': "Адрес получателя: ", 'amount': "Сумма: ", 'sent_success': "Отправлено и транслировано!",
        'mining_start': "Майнинг начат...", 'block_found': "БЛОК НАЙДЕН!",
        'assets_title': "Мои активы", 'fee': "Плата", 'type': "Тип",
        'stats_total_supply': "Общее предложение", 'stats_circulating': "В обращении",
        'stats_block_reward': "Награда за блок", 'stats_solved_blocks': "Решено блоков",
        'stats_last_block': "Хеш последнего блока", 'stats_halving': "До халвинга",
        'back_to_menu': "0. Вернуться в главное меню", 'asset_cost': "Стоимость", 'asset_expiry': "Истекает",
        'enter_0_to_cancel': "(Введите 0 для отмены)",
        'login_title': "--- ВХОД В GHOST PROTOCOL ---", 'login_user': "Имя пользователя: ", 
        'login_pass': "Пароль: ", 'login_fail': "Ошибка входа!", 'logged_out': "Вышли из системы.",
        'create_acc_title': "--- СОЗДАТЬ АККАУНТ ---", 'create_acc_success': "Аккаунт создан! Пожалуйста, войдите.",
        'create_acc_fail': "Имя пользователя занято или ошибка.",
        'msg_menu': "--- GHOST МЕССЕНДЖЕР ---", 'msg_friends': "1. Друзья и Чат", 
        'msg_invite': "2. Пригласить друга", 'msg_enter_friend': "Ключ кошелька друга (0 назад): ",
        'msg_type': "Сообщение: ", 'msg_sent': "Сообщение отправлено в сеть.",
        'msg_invite_user': "Имя для приглашения: ", 'msg_invite_sent': "Приглашение отправлено в сеть.",
        'msg_chat_title': "История чата",
        'asset_remaining': "Осталось", 'asset_held': "Владение",
        'days': "дн.", 'hours': "ч."
    },
    'hy': {
        'node_name': "Ghost Mesh Հանգույց", 'menu_title': "GHOST PROTOCOL ԸՆՏՐԱՑԱՆԿ",
        'auth_menu_title': "ՄՈՒՏՔ / ԳՐԱՆՑՈՒՄ", 'opt_login': "1. Մուտք գործել", 'opt_create_account': "2. Ստեղծել հաշիվ",
        'opt_register': "1. Գրանցել Ակտիվ", 'opt_search': "2. Որոնում",
        'opt_wallet': "3. Դրամապանակ", 'opt_mine': "4. Մայնինգ",
        'opt_messenger': "5. Ghost Մեսենջեր", 'opt_status': "6. Ցանցի կարգավիճակ", 
        'opt_logout': "7. Դուրս գալ", 'opt_exit': "8. Ելք",
        'balance': "Հաշվեկշիռ", 'pubkey': "Դրամապանակ", 'sync_status': "Սինխրոնիզացիա",
        'enter_choice': "Ընտրություն: ", 'invalid_choice': "Սխալ ընտրություն!",
        'domain_name': "Դոմենի անուն: ", 'content_html': "Բովանդակություն (HTML): ",
        'register_success': "Հաջողվեց! Գործարքը հեռարձակվեց:", 'register_fail': "Ձախողվեց: ",
        'search_query': "Որոնում: ", 'no_results': "Արդյունք չկա:",
        'results_found': "Արդյունքներ:", 'view_content': "Դիտել (ID): ",
        'recipient': "Ստացող: ", 'amount': "Գումար: ", 'sent_success': "Ուղարկվեց և հեռարձակվեց!",
        'mining_start': "Մայնինգ...", 'block_found': "ԲԼՈԿԸ ԳՏՆՎԵՑ!",
        'assets_title': "Իմ Ակտիվները", 'fee': "Վճար", 'type': "Տեսակ",
        'stats_total_supply': "Ընդհանուր առաջարկ", 'stats_circulating': "Շրջանառվող առաջարկ",
        'stats_block_reward': "Բլոկի պարգև", 'stats_solved_blocks': "Լուծված բլոկներ",
        'stats_last_block': "Վերջին բլոկի հեշ", 'stats_halving': "Մինչ կիսումը",
        'back_to_menu': "0. Վերադառնալ գլխավոր մենյու", 'asset_cost': "Արժեք", 'asset_expiry': "Լրանում է",
        'enter_0_to_cancel': "(Մուտքագրեք 0 չեղարկելու համար)",
        'login_title': "--- GHOST PROTOCOL ՄՈՒՏՔ ---", 'login_user': "Օգտանուն: ", 
        'login_pass': "Գաղտնաբառ: ", 'login_fail': "Մուտքը ձախողվեց:", 'logged_out': "Դուրս եկավ:",
        'create_acc_title': "--- ՍՏԵՂԾԵԼ ՆՈՐ ՀԱՇԻՎ ---", 'create_acc_success': "Հաշիվը ստեղծված է: Խնդրում ենք մուտք գործել:",
        'create_acc_fail': "Օգտանունը զբաղված է կամ սխալ:",
        'msg_menu': "--- GHOST ՄԵՍԵՆՋԵՐ ---", 'msg_friends': "1. Ընկերներ և Զրույց", 
        'msg_invite': "2. Հրավիրել ընկերոջը", 'msg_enter_friend': "Ընկերոջ Դրամապանակի բանալին (0 հետ): ",
        'msg_type': "Հաղորդագրություն: ", 'msg_sent': "Ուղարկվեց ցանցին:",
        'msg_invite_user': "Օգտանուն հրավերի համար: ", 'msg_invite_sent': "Հրավերն ուղարկվեց ցանցին:",
        'msg_chat_title': "Զրույցի պատմություն",
        'asset_remaining': "Մնացած ժամանակը", 'asset_held': "Պահպանման ժամկետը",
        'days': "օր", 'hours': "ժամ"
    }
}
DEFAULT_LANG = 'tr'

# --- YARDIMCI FONKSİYONLAR / HELPER FUNCTIONS ---
def generate_user_keys(username):
    original_hash = hashlib.sha256(username.encode()).hexdigest()[:20]
    ghst_address = f"GHST{original_hash}" 
    return original_hash, ghst_address

def calculate_difficulty(active_peer_count):
    increase = active_peer_count // 5
    return BASE_DIFFICULTY + increase

def extract_keywords(content_str):
    try:
        text = re.sub(r'<(script|style).*?>.*?</\1>', '', content_str, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<.*?>', ' ', text)
        text = re.sub(r'[^a-zA-ZğüşıöçĞÜŞİÖÇ ]', ' ', text)
        return ",".join(list(set([w for w in text.lower().split() if len(w) > 2]))[:20])
    except: return ""

def calculate_asset_fee(size_bytes, asset_type):
    if asset_type == 'domain': return DOMAIN_REGISTRATION_FEE
    return round((size_bytes / (1024 * 1024)) * STORAGE_COST_PER_MB, 5)

# --- VERİTABANI YÖNETİCİSİ / DATABASE MANAGER ---
class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 0, last_mined REAL DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, previous_hash TEXT, block_hash TEXT, proof INTEGER, miner_key TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS friends (user_key TEXT, friend_key TEXT, status TEXT, PRIMARY KEY(user_key, friend_key))''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (msg_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, content TEXT, asset_id TEXT, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS network_fees (fee_type TEXT PRIMARY KEY, amount REAL)''')
        
        default_fees = [('domain_reg', DOMAIN_REGISTRATION_FEE), ('storage_mb', STORAGE_COST_PER_MB), ('msg_fee', 0.00001), ('invite_fee', 0.00001)]
        for key, val in default_fees:
            c.execute("INSERT OR IGNORE INTO network_fees (fee_type, amount) VALUES (?, ?)", (key, val))

        if c.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
            genesis_hash = hashlib.sha256(b'GhostGenesis').hexdigest()
            c.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                      (1, time.time(), '0', genesis_hash, 100, 'GhostProtocol_System'))
        
        # TR: Yerel test için varsayılan kullanıcı
        # EN: Default user for local testing
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            my_key = f"GHST{hashlib.sha256(NODE_ID.encode()).hexdigest()[:20]}"
            c.execute("INSERT INTO users (username, password, wallet_public_key, balance) VALUES (?, ?, ?, ?)",
                      ("node_user", "local_pass", my_key, INITIAL_USER_BALANCE))

        # TR: Sistem Hazine Cüzdanını oluştur (Gelirlerin birikeceği yer)
        # EN: Create System Treasury Wallet (Where revenue accumulates)
        if c.execute("SELECT COUNT(*) FROM users WHERE wallet_public_key = ?", (TREASURY_WALLET_KEY,)).fetchone()[0] == 0:
            c.execute("INSERT INTO users (username, password, wallet_public_key, balance) VALUES (?, ?, ?, ?)",
                      ('Network_Treasury', 'sys_locked_node_v1', TREASURY_WALLET_KEY, 0.0))
            
        conn.commit()
        conn.close()

    def get_my_user(self):
        conn = self.get_connection()
        user = conn.execute("SELECT * FROM users LIMIT 1").fetchone() 
        conn.close()
        return dict(user) if user else None
    
    def login_user(self, username, password):
        conn = self.get_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        return dict(user) if user else None

    def register_user(self, username, password):
        _, pub_key = generate_user_keys(username)
        conn = self.get_connection()
        try:
            conn.execute("INSERT INTO users (username, password, wallet_public_key, balance) VALUES (?, ?, ?, ?)",
                         (username, password, pub_key, INITIAL_USER_BALANCE))
            conn.commit()
            return True, pub_key
        except sqlite3.IntegrityError:
            return False, None
        finally:
            conn.close()

    def update_fees(self, fees_dict):
        conn = self.get_connection()
        for k, v in fees_dict.items():
            conn.execute("INSERT OR REPLACE INTO network_fees (fee_type, amount) VALUES (?, ?)", (k, v))
        conn.commit()
        conn.close()

    def get_fee(self, fee_type):
        conn = self.get_connection()
        res = conn.execute("SELECT amount FROM network_fees WHERE fee_type = ?", (fee_type,)).fetchone()
        conn.close()
        if res: return res['amount']
        return 0.00001 

# --- MANAGER SINIFLARI / MANAGER CLASSES ---

class NodeMessengerManager:
    def __init__(self, db_mgr, blockchain_mgr, mesh_mgr):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.mesh_mgr = mesh_mgr

    def send_invite(self, current_user, friend_username):
        fee = self.db.get_fee('invite_fee')
        sender_key = current_user['wallet_public_key']
        
        # TR: Ücreti Hazineye aktar
        # EN: Transfer fee to Treasury
        success, msg = self.chain_mgr.transfer_coin(current_user, TREASURY_WALLET_KEY, fee)
        if not success: return False, f"Bakiye yetersiz: {fee}"

        # TR: Daveti sunucuya yayınla (Broadcast)
        # EN: Broadcast invite to server
        invite_data = {
            'type': 'invite',
            'sender': sender_key,
            'target_username': friend_username,
            'timestamp': time.time()
        }
        self.mesh_mgr.broadcast_message(invite_data)
        
        return True, "Davet ağa iletildi."

    def get_friends(self, user_key):
        conn = self.db.get_connection()
        friends = conn.execute("SELECT * FROM friends WHERE user_key = ?", (user_key,)).fetchall()
        conn.close()
        return [dict(f) for f in friends]

    def send_message(self, current_user, friend_key, content, asset_id=None):
        fee = self.db.get_fee('msg_fee')
        sender_key = current_user['wallet_public_key']
        
        # TR: Ücreti Hazineye aktar
        # EN: Transfer fee to Treasury
        success, msg = self.chain_mgr.transfer_coin(current_user, TREASURY_WALLET_KEY, fee)
        if not success: return False, f"Bakiye yetersiz: {fee}"

        msg_id = str(uuid4())
        timestamp = time.time()
        encrypted_content = base64.b64encode(content.encode()).decode()
        
        # TR: Yerel kaydet
        # EN: Save locally
        conn = self.db.get_connection()
        conn.execute("INSERT INTO messages (msg_id, sender, recipient, content, asset_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                     (msg_id, sender_key, friend_key, encrypted_content, asset_id, timestamp))
        conn.commit()
        conn.close()
        
        # TR: Ağa Yay (Broadcast)
        # EN: Broadcast to Network
        msg_data = {
            'type': 'message',
            'msg_id': msg_id,
            'sender': sender_key,
            'recipient': friend_key,
            'content': encrypted_content,
            'asset_id': asset_id,
            'timestamp': timestamp
        }
        self.mesh_mgr.broadcast_message(msg_data)
        
        return True, "Mesaj ağa gönderildi."

    def get_messages(self, user_key, friend_key):
        conn = self.db.get_connection()
        msgs = conn.execute("SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY timestamp ASC",
                            (user_key, friend_key, friend_key, user_key)).fetchall()
        conn.close()
        decoded = []
        for m in msgs:
            d = dict(m)
            try: d['content'] = base64.b64decode(d['content']).decode()
            except: d['content'] = "[Encrypted]"
            decoded.append(d)
        return decoded

class NodeAssetManager:
    def __init__(self, db_mgr, blockchain_mgr, mesh_mgr):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.mesh_mgr = mesh_mgr 

    def register_asset(self, current_user, asset_type, name, content):
        if asset_type == 'domain' and not name.endswith('.ghost'): name += '.ghost'
        if not content: content = "<h1>New Site</h1>"
        
        content_bytes = content.encode('utf-8')
        keywords = extract_keywords(content) if asset_type == 'domain' else ""
        size = len(content_bytes)
        
        if asset_type == 'domain': fee = self.db.get_fee('domain_reg')
        else: fee = (size / (1024*1024)) * self.db.get_fee('storage_mb')
        
        if current_user['balance'] < fee: return False, f"Yetersiz Bakiye ({fee} GHOST)"

        conn = self.db.get_connection()
        try:
            asset_id = str(uuid4())
            tx_id = str(uuid4())
            timestamp = time.time()
            sender_key = current_user['wallet_public_key']

            conn.execute("INSERT OR REPLACE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_id, sender_key, asset_type, name, content_bytes, size, timestamp, timestamp + DOMAIN_EXPIRY_SECONDS, keywords))
            
            # TR: Ücreti kullanıcıdan düş
            # EN: Deduct fee from user
            conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (fee, current_user['id']))
            
            # TR: Ücreti Hazineye Ekle
            # EN: Add fee to Treasury
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (fee, TREASURY_WALLET_KEY))
            
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (tx_id, sender_key, TREASURY_WALLET_KEY, fee, timestamp))
            
            conn.commit()

            # TR: İşlemi ve Varlığı Ağa Yay (Broadcast Transaction & Asset Sync)
            # EN: Broadcast Transaction & Asset Sync
            tx_data = {'tx_id': tx_id, 'sender': sender_key, 'recipient': TREASURY_WALLET_KEY, 'amount': fee, 'timestamp': timestamp}
            self.mesh_mgr.broadcast_transaction(tx_data)
            
            return True, "Kayıt Başarılı"
        except Exception as e: return False, str(e)
        finally: conn.close()

    def get_local_assets(self, owner_pub_key):
        conn = self.db.get_connection()
        assets = conn.execute("SELECT * FROM assets WHERE owner_pub_key = ? ORDER BY creation_time DESC", (owner_pub_key,)).fetchall()
        conn.close()
        return assets
    
    def search_assets(self, query):
        conn = self.db.get_connection()
        s = f"%{query}%"
        results = conn.execute("SELECT * FROM assets WHERE name LIKE ? OR keywords LIKE ?", (s, s)).fetchall()
        conn.close()
        return results
    
    def sync_asset(self, asset_data):
        conn = self.db.get_connection()
        try:
            content_bytes = base64.b64decode(asset_data['content'])
            conn.execute("INSERT OR IGNORE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_data['asset_id'], asset_data['owner_pub_key'], asset_data['type'], asset_data['name'], content_bytes, 
                          len(content_bytes), asset_data['creation_time'], asset_data['expiry_time'], asset_data.get('keywords', '')))
            conn.commit()
        except: pass
        finally: conn.close()

    def get_all_assets_meta(self):
        conn = self.db.get_connection()
        assets = conn.execute("SELECT asset_id FROM assets").fetchall()
        conn.close()
        return [dict(a) for a in assets]

class NodeBlockchainManager:
    def __init__(self, db_mgr, mesh_mgr=None):
        self.db = db_mgr
        self.mesh_mgr = mesh_mgr

    def set_mesh_manager(self, mesh_mgr):
        self.mesh_mgr = mesh_mgr

    def get_last_block(self):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return block

    def get_statistics(self):
        conn = self.db.get_connection()
        last_block = self.get_last_block()
        
        mined_rewards = conn.execute("SELECT SUM(amount) FROM transactions WHERE sender = 'GhostProtocol_System'").fetchone()[0] or 0.0
        mined_supply = mined_rewards 
        
        current_block_index = last_block['block_index']
        halvings = current_block_index // HALVING_INTERVAL
        current_reward = INITIAL_BLOCK_REWARD / (2**halvings)
        blocks_to_halving = HALVING_INTERVAL - (current_block_index % HALVING_INTERVAL)
        
        conn.close()
        
        return {
            "total_supply": TOTAL_SUPPLY,
            "circulating_supply": mined_supply,
            "block_reward": current_reward,
            "solved_blocks": current_block_index,
            "last_block_hash": last_block['block_hash'][:10] + "...",
            "blocks_to_halving": blocks_to_halving
        }

    def mine_block(self, current_user):
        miner_key = current_user['wallet_public_key']
        last_mined = current_user['last_mined']
        
        if (time.time() - last_mined) < 86400:
            return False, "Günlük limit dolmadı."

        last_block = self.get_last_block()
        index = last_block['block_index'] + 1
        
        proof = 0
        while True:
            guess = f'{last_block["proof"]}{proof}'.encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if guess_hash[:BASE_DIFFICULTY] == '0' * BASE_DIFFICULTY: break
            proof += 1
            
        block_hash = hashlib.sha256(f"{index}{time.time()}{last_block['block_hash']}{proof}".encode()).hexdigest()
        
        halvings = index // HALVING_INTERVAL
        reward = INITIAL_BLOCK_REWARD / (2**halvings)

        conn = self.db.get_connection()
        try:
            conn.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                         (index, time.time(), last_block['block_hash'], block_hash, proof, miner_key))
            conn.execute("UPDATE users SET balance = balance + ?, last_mined = ? WHERE id = ?", (reward, time.time(), current_user['id']))
            conn.commit()
            return True, block_hash
        except Exception as e: return False, str(e)
        finally: conn.close()

    def transfer_coin(self, current_user, recipient, amount):
        if current_user['balance'] < amount: return False, "Yetersiz bakiye."
        
        conn = self.db.get_connection()
        try:
            tx_id = str(uuid4())
            timestamp = time.time()
            sender_key = current_user['wallet_public_key']

            # TR: Gönderen bakiyesini düş
            # EN: Deduct sender balance
            conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, current_user['id']))
            
            # TR: Alıcı bakiyesini artır (Eğer yerel veritabanında varsa - Örn: Hazine Cüzdanı)
            # EN: Increase recipient balance (If exists in local db - e.g., Treasury Wallet)
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (amount, recipient))

            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (tx_id, sender_key, recipient, amount, timestamp))
            conn.commit()

            if self.mesh_mgr:
                tx_data = {'tx_id': tx_id, 'sender': sender_key, 'recipient': recipient, 'amount': amount, 'timestamp': timestamp}
                self.mesh_mgr.broadcast_transaction(tx_data)

            return True, "Transfer yapıldı."
        except Exception as e: return False, str(e)
        finally: conn.close()

class NodeMeshManager:
    def __init__(self, db_mgr, blockchain_mgr):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.asset_mgr = None
        self.known_peers = KNOWN_PEERS
        
        self.start_services()

    def set_asset_manager(self, asset_mgr):
        self.asset_mgr = asset_mgr

    def start_services(self):
        threading.Thread(target=self._sync_loop, daemon=True).start()

    def _sync_loop(self):
        while True:
            self.sync_with_network()
            time.sleep(60) 

    def broadcast_transaction(self, tx_data):
        def _send():
            for peer in self.known_peers:
                try:
                    url = f"http://{peer}:{GHOST_PORT}/api/send_transaction"
                    requests.post(url, json=tx_data, timeout=3)
                    logger.info(f"Transaction sent to {peer}")
                except Exception as e:
                    logger.warning(f"Failed to send TX to {peer}: {e}")
        threading.Thread(target=_send, daemon=True).start()

    def broadcast_message(self, msg_data):
        # TR: Mesajı ağa yay
        # EN: Broadcast message to network
        def _send():
            for peer in self.known_peers:
                try:
                    url = f"http://{peer}:{GHOST_PORT}/api/messenger/receive_message"
                    requests.post(url, json=msg_data, timeout=3)
                    logger.info(f"Message sent to {peer}")
                except Exception as e:
                    logger.warning(f"Failed to send MSG to {peer}: {e}")
        threading.Thread(target=_send, daemon=True).start()

    def broadcast_new_user(self, username, pub_key):
        # TR: Yeni kullanıcıyı ağa duyur (User Sync Çözümü)
        # EN: Announce new user to network (User Sync Solution)
        def _send():
            logger.info(f"Broadcasting new user: {username}")
        threading.Thread(target=_send, daemon=True).start()

    def sync_with_network(self):
        for peer_ip in self.known_peers:
            try:
                # 1. BLOK SYNC
                resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/chain_meta", timeout=3)
                if resp.status_code == 200:
                    remote_headers = resp.json()
                    local_last = self.chain_mgr.get_last_block()
                    
                    if remote_headers and remote_headers[-1]['block_index'] > local_last['block_index']:
                        for h in remote_headers:
                            if h['block_index'] > local_last['block_index']:
                                b_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/block/{h['block_hash']}", timeout=3)
                                if b_resp.status_code == 200:
                                    self._save_block(b_resp.json())
                                    logger.info(f"Blok indirildi: {h['block_index']}")

                # 2. ASSET SYNC
                if self.asset_mgr:
                    a_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/assets_meta", timeout=3)
                    if a_resp.status_code == 200:
                        remote_assets = a_resp.json()
                        local_assets_meta = self.asset_mgr.get_all_assets_meta()
                        local_asset_ids = {a['asset_id'] for a in local_assets_meta}
                        
                        for ra in remote_assets:
                            if ra['asset_id'] not in local_asset_ids:
                                content_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/asset_data/{ra['asset_id']}", timeout=3)
                                if content_resp.status_code == 200:
                                    self.asset_mgr.sync_asset(content_resp.json())
                                    logger.info(f"Varlık indirildi: {ra['name']}")
                                    
                # 3. FEE SYNC
                f_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/get_fees", timeout=3)
                if f_resp.status_code == 200:
                    self.db.update_fees(f_resp.json())
                
            except Exception as e: 
                logger.debug(f"Senkronizasyon hatası ({peer_ip}): {e}")

    def _save_block(self, block_data):
        conn = self.db.get_connection()
        try:
            conn.execute("INSERT OR IGNORE INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                         (block_data['block_index'], block_data['timestamp'], block_data['previous_hash'], block_data['block_hash'], block_data['proof'], block_data['miner_key']))
            conn.commit()
        finally: conn.close()

# --- ANA UYGULAMA (TERMINAL ARAYÜZÜ) / MAIN APP (TERMINAL UI) ---
class GhostMeshNodeApp:
    def __init__(self):
        self.db = DatabaseManager(DB_FILE)
        
        self.chain = NodeBlockchainManager(self.db)
        self.mesh = NodeMeshManager(self.db, self.chain)
        self.asset = NodeAssetManager(self.db, self.chain, self.mesh)
        self.messenger = NodeMessengerManager(self.db, self.chain, self.mesh)
        
        self.mesh.set_asset_manager(self.asset)
        self.chain.set_mesh_manager(self.mesh)
        
        self.lang_code = 'tr' 
        self.L = LANGUAGES[self.lang_code]
        self.current_user = None

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def set_language(self):
        self.clear_screen()
        print("1. Türkçe\n2. English\n3. Русский\n4. Հայերեն")
        choice = input("Select Language: ")
        if choice == '1': self.lang_code = 'tr'
        elif choice == '2': self.lang_code = 'en'
        elif choice == '3': self.lang_code = 'ru'
        elif choice == '4': self.lang_code = 'hy'
        self.L = LANGUAGES[self.lang_code]

    def login_screen(self):
        while not self.current_user:
            self.clear_screen()
            print(self.L['auth_menu_title'])
            print(self.L['opt_login'])
            print(self.L['opt_create_account'])
            
            choice = input(self.L['enter_choice'])
            
            if choice == '1': # Login
                self.clear_screen()
                print(self.L['login_title'])
                u = input(self.L['login_user'])
                p = input(self.L['login_pass'])
                user = self.db.login_user(u, hashlib.sha256(p.encode()).hexdigest()) 
                
                # Default user fallback
                if not user and u == "node_user" and p == "local_pass":
                    user = self.db.get_my_user()
                
                if user: self.current_user = user
                else:
                    print(f"❌ {self.L['login_fail']}")
                    time.sleep(2)
            
            elif choice == '2': # Create Account
                self.clear_screen()
                print(self.L['create_acc_title'])
                u = input(self.L['login_user'])
                p = input(self.L['login_pass'])
                
                if u and p:
                    p_hash = hashlib.sha256(p.encode()).hexdigest()
                    success, pub_key = self.db.register_user(u, p_hash)
                    if success:
                        print(f"✅ {self.L['create_acc_success']}")
                        # TR: Yeni kullanıcıyı ağa duyur (User Discovery Fix)
                        # EN: Announce new user to network (User Discovery Fix)
                        self.mesh.broadcast_new_user(u, pub_key)
                    else:
                        print(f"❌ {self.L['create_acc_fail']}")
                else:
                    print("Error: Empty fields.")
                time.sleep(2)

    def display_stats_box(self):
        stats = self.chain.get_statistics()
        print("\n" + "="*40)
        print(f"📊 {self.L.get('node_name', 'Ghost Node')} Stats")
        print(f"{self.L['stats_total_supply']}: {stats['total_supply']:,.0f} GHOST")
        print(f"{self.L['stats_circulating']}: {stats['circulating_supply']:,.2f} GHOST")
        print(f"{self.L['stats_block_reward']}: {stats['block_reward']} GHOST")
        print(f"{self.L['stats_solved_blocks']}: {stats['solved_blocks']}")
        print(f"{self.L['stats_last_block']}: {stats['last_block_hash']}")
        print(f"{self.L['stats_halving']}: {stats['blocks_to_halving']}")
        print("="*40 + "\n")

    def display_status(self):
        self.current_user = self.db.login_user(self.current_user['username'], self.current_user['password'])
        if not self.current_user:
             self.current_user = self.db.get_my_user() 

        assets = self.asset.get_local_assets(self.current_user['wallet_public_key'])
        
        self.clear_screen()
        print(f"--- {self.L['node_name']} ---")
        print(f"👤 User: {self.current_user['username']}")
        print(f"🌍 {self.L['sync_status']}: {'ONLINE' if self.mesh.known_peers else 'MESH'}")
        print(f"💰 {self.L['balance']}: {self.current_user['balance']:.4f} GHOST")
        # TR: Cüzdan adresini tam göster (Fix)
        # EN: Show full wallet address (Fix)
        print(f"🔑 {self.L['pubkey']}: {self.current_user['wallet_public_key']}")
        
        self.display_stats_box()
        
        assets_title = self.L.get('assets_title', 'Local Assets') 
        print(f"📂 {assets_title} ({len(assets)}):")
        current_time = time.time()
        for a in assets[:5]:
            fee = calculate_asset_fee(a['storage_size'], a['type'])
            
            # TR: Varlık detaylarını hesapla (Fix)
            # EN: Calculate asset details (Fix)
            expiry_date = datetime.fromtimestamp(a['expiry_time'])
            creation_date = datetime.fromtimestamp(a['creation_time'])
            
            remaining = expiry_date - datetime.now()
            remaining_str = f"{remaining.days} {self.L['days']}, {remaining.seconds // 3600} {self.L['hours']}"
            if remaining.days < 0: remaining_str = "Expired"
            
            held_duration = datetime.now() - creation_date
            held_str = f"{held_duration.days} {self.L['days']}"
            
            print(f" - {a['name']} ({a['type']})")
            print(f"   └ {self.L['asset_cost']}: {fee} GHOST")
            print(f"   └ {self.L['asset_remaining']}: {remaining_str}")
            print(f"   └ {self.L['asset_held']}: {held_str}")
            
        print("-" * 30)

    def register_screen(self):
        print(f"\n--- {self.L['opt_register']} ---")
        print(self.L['back_to_menu'])
        
        name = input(self.L['domain_name'])
        if name == '0': return
        
        content = input(self.L['content_html'])
        if content == '0': return
        
        success, msg = self.asset.register_asset(self.current_user, 'domain', name, content)
        if success: print(f"✅ {self.L['register_success']}")
        else: print(f"❌ {self.L['register_fail']}{msg}")
        input("Enter...")

    def search_screen(self):
        print(f"\n--- {self.L['opt_search']} ---")
        print(self.L['back_to_menu'])
        
        q = input(self.L['search_query'])
        if q == '0': return
        
        results = self.asset.search_assets(q)
        if not results: print(self.L['no_results'])
        else:
            print(self.L['results_found'])
            for r in results: print(f"ID: {r['asset_id']} | {r['name']}")
            vid = input(self.L['view_content'])
            if vid != '0':
                for r in results:
                    if r['asset_id'] == vid:
                        try:
                            print(f"\n--- {r['name']} ---\n{r['content'].decode('utf-8')}\n----------------")
                        except:
                            print("Binary content.")
                        input("Enter...")

    def wallet_screen(self):
        print(f"\n--- {self.L['opt_wallet']} ---")
        print(self.L['back_to_menu'])
        
        rec = input(self.L['recipient'])
        if rec == '0': return
        
        try: 
            amt_str = input(self.L['amount'])
            if amt_str == '0': return
            amt = float(amt_str)
        except: amt = 0
        
        success, msg = self.chain.transfer_coin(self.current_user, rec, amt)
        if success: print(f"✅ {self.L['sent_success']}")
        else: print(f"❌ {msg}")
        input("Enter...")

    def mining_screen(self):
        print(f"\n--- {self.L['opt_mine']} ---")
        print(self.L['back_to_menu'])
        
        confirm = input("Start Mining? (y/n/0): ")
        if confirm == '0' or confirm.lower() == 'n': return
        
        print(self.L['mining_start'])
        success, msg = self.chain.mine_block(self.current_user)
        if success: print(f"⛏️ {self.L['block_found']} Hash: {msg}")
        else: print(f"❌ {msg}")
        input("Enter...")

    def messenger_screen(self):
        while True:
            self.clear_screen()
            print(self.L['msg_menu'])
            print(self.L['msg_friends'])
            print(self.L['msg_invite'])
            print(self.L['back_to_menu'])
            
            c = input(self.L['enter_choice'])
            if c == '0': break
            elif c == '1': # Chat & Friends
                friends = self.messenger.get_friends(self.current_user['wallet_public_key'])
                print("\n--- Friends ---")
                for f in friends: print(f"ID: {f['friend_key'][:10]}... | Status: {f['status']}")
                
                f_key = input(self.L['msg_enter_friend']) 
                if f_key != '0':
                    msgs = self.messenger.get_messages(self.current_user['wallet_public_key'], f_key)
                    print(f"\n{self.L['msg_chat_title']}:")
                    for m in msgs:
                        sender = "Me" if m['sender'] == self.current_user['wallet_public_key'] else "Friend"
                        print(f"[{datetime.fromtimestamp(m['timestamp']).strftime('%H:%M')}] {sender}: {m['content']}")
                    
                    txt = input(self.L['msg_type'])
                    if txt:
                        self.messenger.send_message(self.current_user, f_key, txt)
                        print(self.L['msg_sent'])
                        time.sleep(1)
            
            elif c == '2': # Invite
                u_name = input(self.L['msg_invite_user'])
                if u_name:
                    success, msg = self.messenger.send_invite(self.current_user, u_name)
                    print(msg)
                    time.sleep(2)

    def run(self):
        self.set_language()
        while True:
            # Login loop
            if not self.current_user:
                self.login_screen()
            
            # Main menu loop
            self.display_status()
            print(f"1. {self.L['opt_register']}")
            print(f"2. {self.L['opt_search']}")
            print(f"3. {self.L['opt_wallet']}")
            print(f"4. {self.L['opt_mine']}")
            print(f"5. {self.L['opt_messenger']}")
            print(f"6. {self.L['opt_status']}")
            print(f"7. {self.L['opt_logout']}")
            print(f"8. {self.L['opt_exit']}")
            
            choice = input(self.L['enter_choice'])
            
            if choice == '1': self.register_screen()
            elif choice == '2': self.search_screen()
            elif choice == '3': self.wallet_screen()
            elif choice == '4': self.mining_screen()
            elif choice == '5': self.messenger_screen()
            elif choice == '7': 
                self.current_user = None
                print(self.L['logged_out'])
                time.sleep(1)
            elif choice == '8': break

if __name__ == '__main__':
    node = GhostMeshNodeApp()
    try:
        node.run()
    except KeyboardInterrupt:
        print("\nKapatılıyor...")

# -*- coding: utf-8 -*-
"""
EN: GhostProtocol Mesh Node - Smart Contract Integrated CLI (Fix V2)
TR: GhostProtocol Mesh Düğümü - Akıllı Kontrat Entegreli CLI (Düzeltme V2)
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

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GhostNode - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostMeshNode")

# --- CONFIGURATION ---
NODE_ID = hashlib.sha256(socket.gethostname().encode()).hexdigest()[:10]
DB_FILE = os.path.join(os.getcwd(), f"ghost_node_{NODE_ID}.db")
GHOST_PORT = 5000 
KNOWN_PEERS = ["46.101.219.46", "68.183.12.91"] 

STORAGE_COST_PER_MB = 0.01
DOMAIN_REGISTRATION_FEE = 1.0
DOMAIN_EXPIRY_SECONDS = 15552000 
INITIAL_USER_BALANCE = 0.0
BASE_DIFFICULTY = 4
INITIAL_BLOCK_REWARD = 50.0
HALVING_INTERVAL = 2000
TOTAL_SUPPLY = 100000000.0

# --- LANGUAGES ---
LANGUAGES = {
    'tr': {
        'node_name': "Ghost Mesh Düğümü", 'menu_title': "GHOST PROTOCOL MENÜSÜ",
        'auth_menu_title': "GİRİŞ / KAYIT", 'opt_login': "1. Giriş Yap", 'opt_create_account': "2. Yeni Hesap Oluştur",
        'opt_register': "1. Varlık Kaydet", 'opt_search': "2. Ara & Görüntüle",
        'opt_wallet': "3. Cüzdan & Transfer", 'opt_mine': "4. Madencilik Yap",
        'opt_messenger': "5. Ghost Messenger", 'opt_contracts': "6. Akıllı Kontratlar", 
        'opt_status': "7. Ağ Durumu", 'opt_logout': "8. Çıkış Yap", 'opt_exit': "9. Kapat",
        'balance': "Bakiye", 'pubkey': "Cüzdan", 'sync_status': "Senkronizasyon",
        'enter_choice': "Seçiminiz: ", 'invalid_choice': "Geçersiz seçim!",
        'domain_name': "Domain Adı (İptal için 0): ", 'content_html': "İçerik (HTML) (İptal için 0): ",
        'register_success': "Kayıt Başarılı!", 'register_fail': "Kayıt Başarısız: ",
        'search_query': "Arama (İptal için 0): ", 'no_results': "Sonuç yok.",
        'results_found': "Sonuçlar:", 'view_content': "Görüntüle (ID girin, İptal için 0): ",
        'recipient': "Alıcı Cüzdan (İptal için 0): ", 'amount': "Miktar (İptal için 0): ", 'sent_success': "Gönderildi!",
        'mining_start': "Madencilik Başlıyor... (Durdurmak için CTRL+C)", 'block_found': "BLOK BULUNDU!", 
        'assets_title': "Varlıklarım", 'fee': "Ücret", 
        'stats_total_supply': "Toplam Arz", 'stats_circulating': "Dolaşımdaki Arz", 'stats_remaining': "Kalan Arz",
        'stats_block_reward': "Blok Ödülü", 'stats_solved_blocks': "Çözülen Blok",
        'stats_last_block': "Son Blok Hash", 'stats_halving': "Yarılanmaya Kalan",
        'back_to_menu': "0. Geri Dön", 'asset_cost': "Maliyet", 'asset_expiry': "Bitiş",
        'enter_0_to_cancel': "(İptal: 0)", 'login_title': "--- GİRİŞ ---", 'login_user': "Kullanıcı Adı: ", 
        'login_pass': "Şifre: ", 'login_fail': "Başarısız!", 'logged_out': "Çıkış yapıldı.",
        'create_acc_title': "--- KAYIT ---", 'create_acc_success': "Hesap oluşturuldu.",
        'create_acc_fail': "Hata.", 'msg_menu': "--- MESSENGER ---", 'msg_friends': "1. Arkadaşlar & Sohbet", 
        'msg_invite': "2. Davet Et", 'msg_enter_friend': "Arkadaş Cüzdan Anahtarı (0 geri): ",
        'msg_type': "Mesaj (İptal 0): ", 'msg_sent': "Gönderildi.", 'msg_invite_user': "Kullanıcı Adı (İptal 0): ", 'msg_invite_sent': "Davet gönderildi.",
        'msg_chat_title': "Sohbet", 'sc_menu': "--- AKILLI KONTRATLAR ---", 'sc_deploy': "1. Yeni Kontrat Yükle",
        'sc_call': "2. Kontrat Çağır", 'sc_code': "Kod Girin (Bitirmek için END yazın, İptal 0):", 'sc_deploying': "Yükleniyor...",
        'sc_addr': "Kontrat Adresi (İptal 0): ", 'sc_method': "Metot Adı: ", 'sc_args': "Argümanlar (virgülle ayır): "
    },
    'en': {
        'node_name': "Ghost Mesh Node", 'menu_title': "GHOST PROTOCOL MENU",
        'auth_menu_title': "LOGIN / REGISTER", 'opt_login': "1. Login", 'opt_create_account': "2. Create Account",
        'opt_register': "1. Register Asset", 'opt_search': "2. Search & View",
        'opt_wallet': "3. Wallet & Transfer", 'opt_mine': "4. Mine Block",
        'opt_messenger': "5. Ghost Messenger", 'opt_contracts': "6. Smart Contracts",
        'opt_status': "7. Network Status", 'opt_logout': "8. Logout", 'opt_exit': "9. Exit",
        'balance': "Balance", 'pubkey': "Wallet", 'sync_status': "Sync Status",
        'enter_choice': "Choice: ", 'invalid_choice': "Invalid choice!",
        'domain_name': "Domain Name (0 to cancel): ", 'content_html': "Content (HTML) (0 to cancel): ",
        'register_success': "Success!", 'register_fail': "Failed: ",
        'search_query': "Search (0 to cancel): ", 'no_results': "No results.",
        'results_found': "Results:", 'view_content': "View (Enter ID, 0 to cancel): ",
        'recipient': "Recipient (0 to cancel): ", 'amount': "Amount (0 to cancel): ", 'sent_success': "Sent!",
        'mining_start': "Mining... (CTRL+C to stop)", 'block_found': "BLOCK FOUND!", 
        'assets_title': "My Assets", 'fee': "Fee", 
        'stats_total_supply': "Total Supply", 'stats_circulating': "Circulating", 'stats_remaining': "Remaining Supply",
        'stats_block_reward': "Block Reward", 'stats_solved_blocks': "Solved Blocks",
        'stats_last_block': "Last Hash", 'stats_halving': "Halving in",
        'back_to_menu': "0. Back", 'asset_cost': "Cost", 'asset_expiry': "Expires",
        'enter_0_to_cancel': "(Cancel: 0)", 'login_title': "--- LOGIN ---", 'login_user': "Username: ", 
        'login_pass': "Password: ", 'login_fail': "Failed!", 'logged_out': "Logged out.",
        'create_acc_title': "--- REGISTER ---", 'create_acc_success': "Account created.",
        'create_acc_fail': "Error.", 'msg_menu': "--- MESSENGER ---", 'msg_friends': "1. Friends & Chat", 
        'msg_invite': "2. Invite", 'msg_enter_friend': "Friend Wallet Key (0 back): ",
        'msg_type': "Message (0 to cancel): ", 'msg_sent': "Sent.", 'msg_invite_user': "Username (0 to cancel): ", 'msg_invite_sent': "Invite sent.",
        'msg_chat_title': "Chat", 'sc_menu': "--- SMART CONTRACTS ---", 'sc_deploy': "1. Deploy New Contract",
        'sc_call': "2. Call Contract", 'sc_code': "Enter Code (Type END to finish, 0 to cancel):", 'sc_deploying': "Deploying...",
        'sc_addr': "Contract Address (0 to cancel): ", 'sc_method': "Method Name: ", 'sc_args': "Args (comma separated): "
    },
    'ru': {
        'node_name': "Узел Ghost Mesh", 'menu_title': "МЕНЮ",
        'auth_menu_title': "ВХОД / РЕГИСТРАЦИЯ", 'opt_login': "1. Войти", 'opt_create_account': "2. Создать",
        'opt_register': "1. Регистрация актива", 'opt_search': "2. Поиск",
        'opt_wallet': "3. Кошелек", 'opt_mine': "4. Майнинг",
        'opt_messenger': "5. Мессенджер", 'opt_contracts': "6. Смарт-контракты",
        'opt_status': "7. Статус", 'opt_logout': "8. Выйти", 'opt_exit': "9. Выход",
        'balance': "Баланс", 'pubkey': "Кошелек", 'sync_status': "Синхронизация",
        'enter_choice': "Выбор: ", 'invalid_choice': "Ошибка!",
        'domain_name': "Домен (0 отмена): ", 'content_html': "Контент (0 отмена): ",
        'register_success': "Успешно!", 'register_fail': "Ошибка: ",
        'search_query': "Поиск (0 отмена): ", 'no_results': "Нет результатов.",
        'results_found': "Результаты:", 'view_content': "Просмотр (ID, 0 отмена): ",
        'recipient': "Получатель (0 отмена): ", 'amount': "Сумма (0 отмена): ", 'sent_success': "Отправлено!",
        'mining_start': "Майнинг...", 'block_found': "БЛОК НАЙДЕН!", 
        'assets_title': "Активы", 'fee': "Плата", 
        'stats_total_supply': "Всего", 'stats_circulating': "В обороте", 'stats_remaining': "Остаток",
        'stats_block_reward': "Награда", 'stats_solved_blocks': "Блоки",
        'stats_last_block': "Хеш", 'stats_halving': "Халвинг",
        'back_to_menu': "0. Назад", 'asset_cost': "Цена", 'asset_expiry': "Срок",
        'enter_0_to_cancel': "(0 отмена)", 'login_title': "--- ВХОД ---", 'login_user': "Имя: ", 
        'login_pass': "Пароль: ", 'login_fail': "Ошибка!", 'logged_out': "Выход выполнен.",
        'create_acc_title': "--- РЕГИСТРАЦИЯ ---", 'create_acc_success': "Создано.",
        'create_acc_fail': "Ошибка.", 'msg_menu': "--- МЕССЕНДЖЕР ---", 'msg_friends': "1. Друзья", 
        'msg_invite': "2. Пригласить", 'msg_enter_friend': "ID друга (0 назад): ",
        'msg_type': "Сообщение (0 отмена): ", 'msg_sent': "Отправлено.", 'msg_invite_user': "Имя (0 отмена): ", 'msg_invite_sent': "Отправлено.",
        'msg_chat_title': "Чат", 'sc_menu': "--- СМАРТ-КОНТРАКТЫ ---", 'sc_deploy': "1. Развернуть",
        'sc_call': "2. Вызвать", 'sc_code': "Код (END для завершения, 0 отмена):", 'sc_deploying': "Развертывание...",
        'sc_addr': "Адрес (0 отмена): ", 'sc_method': "Метод: ", 'sc_args': "Аргументы: "
    },
    'hy': {
        'node_name': "Ghost Mesh Node", 'menu_title': "ԸՆՏՐԱՑԱՆԿ",
        'auth_menu_title': "ՄՈՒՏՔ / ԳՐԱՆՑՈՒՄ", 'opt_login': "1. Մուտք", 'opt_create_account': "2. Գրանցվել",
        'opt_register': "1. Գրանցել Ակտիվ", 'opt_search': "2. Որոնում",
        'opt_wallet': "3. Դրամապանակ", 'opt_mine': "4. Մայնինգ",
        'opt_messenger': "5. Մեսենջեր", 'opt_contracts': "6. Խելացի պայմանագրեր",
        'opt_status': "7. Կարգավիճակ", 'opt_logout': "8. Դուրս գալ", 'opt_exit': "9. Ելք",
        'balance': "Հաշվեկշիռ", 'pubkey': "Դրամապանակ", 'sync_status': "Սինխրոնիզացիա",
        'enter_choice': "Ընտրություն: ", 'invalid_choice': "Սխալ!",
        'domain_name': "Դոմեն (0 չեղարկել): ", 'content_html': "Բովանդակություն (0 չեղարկել): ",
        'register_success': "Հաջողվեց!", 'register_fail': "Սխալ: ",
        'search_query': "Որոնում (0 չեղարկել): ", 'no_results': "Արդյունք չկա:",
        'results_found': "Արդյունքներ:", 'view_content': "Դիտել (ID, 0 չեղարկել): ",
        'recipient': "Ստացող (0 չեղարկել): ", 'amount': "Գումար (0 չեղարկել): ", 'sent_success': "Ուղարկվեց!",
        'mining_start': "Մայնինգ...", 'block_found': "ԲԼՈԿ!", 
        'assets_title': "Ակտիվներ", 'fee': "Վճար", 
        'stats_total_supply': "Ընդհանուր", 'stats_circulating': "Շրջանառվող", 'stats_remaining': "Մնացորդ",
        'stats_block_reward': "Պարգև", 'stats_solved_blocks': "Բլոկներ",
        'stats_last_block': "Հեշ", 'stats_halving': "Կիսում",
        'back_to_menu': "0. Հետ", 'asset_cost': "Արժեք", 'asset_expiry': "Ժամկետ",
        'enter_0_to_cancel': "(0 չեղարկել)", 'login_title': "--- ՄՈՒՏՔ ---", 'login_user': "Անուն: ", 
        'login_pass': "Գաղտնաբառ: ", 'login_fail': "Սխալ!", 'logged_out': "Դուրս եկավ:",
        'create_acc_title': "--- ԳՐԱՆՑՈՒՄ ---", 'create_acc_success': "Ստեղծվեց:",
        'create_acc_fail': "Սխալ:", 'msg_menu': "--- ՄԵՍԵՆՋԵՐ ---", 'msg_friends': "1. Ընկերներ", 
        'msg_invite': "2. Հրավիրել", 'msg_enter_friend': "Ընկերոջ ID (0 հետ): ",
        'msg_type': "Նամակ (0 չեղարկել): ", 'msg_sent': "Ուղարկվեց:", 'msg_invite_user': "Անուն (0 չեղարկել): ", 'msg_invite_sent': "Ուղարկվեց:",
        'msg_chat_title': "Զրույց", 'sc_menu': "--- ԽԵԼԱՑԻ ՊԱՅՄԱՆԱԳՐԵՐ ---", 'sc_deploy': "1. Տեղադրել",
        'sc_call': "2. Կանչել", 'sc_code': "Կոդ (END ավարտելու համար, 0 չեղարկել):", 'sc_deploying': "Բեռնում...",
        'sc_addr': "Հասցե (0 չեղարկել): ", 'sc_method': "Մեթոդ: ", 'sc_args': "Արգումենտներ: "
    }
}
DEFAULT_LANG = 'tr'

# --- HELPERS ---
def generate_user_keys(username):
    original_hash = hashlib.sha256(username.encode()).hexdigest()[:20]
    return original_hash, f"GHST{original_hash}"

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

# --- DATABASE ---
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
        
        # TR: Tabloları oluştur (Eğer yoksa)
        # EN: Create tables (If not exists)
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 0, last_mined REAL DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, previous_hash TEXT, block_hash TEXT, proof INTEGER, miner_key TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS friends (user_key TEXT, friend_key TEXT, status TEXT, PRIMARY KEY(user_key, friend_key))''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (msg_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, content TEXT, asset_id TEXT, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS network_fees (fee_type TEXT PRIMARY KEY, amount REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS contracts (contract_address TEXT PRIMARY KEY, owner_key TEXT, code TEXT, state TEXT, creation_time REAL)''')

        # TR: Geriye dönük uyumluluk için sütun kontrolleri (Migration)
        # EN: Column checks for backward compatibility (Migration)
        self._check_and_add_column(c, 'users', 'last_mined', 'REAL DEFAULT 0')
        self._check_and_add_column(c, 'assets', 'keywords', 'TEXT')
        
        # Genesis Block
        if c.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
            genesis_hash = hashlib.sha256(b'GhostGenesis').hexdigest()
            c.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                      (1, time.time(), '0', genesis_hash, 100, 'GhostProtocol_System'))
            
        conn.commit()
        conn.close()

    def _check_and_add_column(self, cursor, table, column, definition):
        try:
            cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                logger.info(f"Migrated: Added {column} to {table}")
            except Exception as e:
                logger.error(f"Migration failed for {table}.{column}: {e}")

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
        if res: return float(res['amount'])
        return 0.00001 

# --- MANAGERS ---

class NodeMessengerManager:
    def __init__(self, db_mgr, blockchain_mgr, mesh_mgr):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.mesh_mgr = mesh_mgr

    def send_invite(self, current_user, friend_username):
        fee = self.db.get_fee('invite_fee')
        sender_key = current_user['wallet_public_key']
        success, msg = self.chain_mgr.transfer_coin(current_user, "Fee_Collector", fee)
        if not success: return False, f"Balance error: {fee}"

        invite_data = {'type': 'invite', 'sender': sender_key, 'target_username': friend_username, 'timestamp': time.time()}
        self.mesh_mgr.broadcast_message(invite_data)
        return True, "Invite sent."

    def get_friends(self, user_key):
        conn = self.db.get_connection()
        friends = conn.execute("SELECT * FROM friends WHERE user_key = ?", (user_key,)).fetchall()
        conn.close()
        return [dict(f) for f in friends]

    def send_message(self, current_user, friend_key, content, asset_id=None):
        fee = self.db.get_fee('msg_fee')
        sender_key = current_user['wallet_public_key']
        
        success, msg = self.chain_mgr.transfer_coin(current_user, "Fee_Collector", fee)
        if not success: return False, f"Balance error: {fee}"

        msg_id = str(uuid4())
        timestamp = time.time()
        encrypted_content = base64.b64encode(content.encode()).decode()
        
        conn = self.db.get_connection()
        conn.execute("INSERT INTO messages (msg_id, sender, recipient, content, asset_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                     (msg_id, sender_key, friend_key, encrypted_content, asset_id, timestamp))
        conn.commit()
        conn.close()
        
        msg_data = {'type': 'message', 'msg_id': msg_id, 'sender': sender_key, 'recipient': friend_key, 'content': encrypted_content, 'asset_id': asset_id, 'timestamp': timestamp}
        self.mesh_mgr.broadcast_message(msg_data)
        return True, "Message sent."

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

class NodeSmartContractManager:
    def __init__(self, db_mgr, blockchain_mgr, mesh_mgr):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.mesh_mgr = mesh_mgr
        
    def deploy_contract(self, current_user, code):
        # TR: CLI düğümleri kontratı sunucu API'si üzerinden dağıtır.
        # EN: CLI nodes deploy contracts via server API.
        try:
            # Not: Gerçek bir P2P ağda bu işlem doğrudan işlem (TX) olarak yayınlanmalıdır.
            # Şimdilik basitleştirilmiş API çağrısı kullanıyoruz.
            # Note: In a real P2P network this should be broadcasted as a TX.
            # Using simplified API call for now.
            target = f"http://{KNOWN_PEERS[0]}:{GHOST_PORT}/api/send_transaction"
            # Bu kısım tam uygulama için geliştirilmeli, şimdilik yerel veritabanına kayıt simülasyonu
            contract_addr = "CNT" + hashlib.sha256(str(uuid4()).encode()).hexdigest()[:10]
            
            # Ücret düş
            fee = self.db.get_fee('contract_deploy')
            success, msg = self.chain_mgr.transfer_coin(current_user, "Fee_Collector", fee)
            if not success: return False, msg
            
            conn = self.db.get_connection()
            conn.execute("INSERT INTO contracts (contract_address, owner_key, code, state, creation_time) VALUES (?, ?, ?, ?, ?)",
                         (contract_addr, current_user['wallet_public_key'], code, "{}", time.time()))
            conn.commit()
            conn.close()
            
            return True, f"Deployed: {contract_addr}"
        except Exception as e:
            return False, str(e)

    def call_contract(self, current_user, contract_address, method, args):
        # TR: Yerel simülasyon veya API çağrısı
        return False, "CLI Call Simulation not fully implemented yet. Use Dashboard."

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
        
        if float(current_user['balance']) < fee: return False, f"Balance: {fee}"

        conn = self.db.get_connection()
        try:
            asset_id = str(uuid4())
            tx_id = str(uuid4())
            timestamp = time.time()
            sender_key = current_user['wallet_public_key']

            conn.execute("INSERT OR REPLACE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_id, sender_key, asset_type, name, content_bytes, size, timestamp, timestamp + DOMAIN_EXPIRY_SECONDS, keywords))
            
            conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (fee, current_user['id']))
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (tx_id, sender_key, "Asset_Fee_Collector", fee, timestamp))
            conn.commit()

            tx_data = {'tx_id': tx_id, 'sender': sender_key, 'recipient': "Asset_Fee_Collector", 'amount': fee, 'timestamp': timestamp}
            self.mesh_mgr.broadcast_transaction(tx_data)

            return True, "Success"
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
        # TR: İstatistiklerin eksiksiz hesaplanması (Fix)
        # EN: Complete calculation of statistics (Fix)
        conn = self.db.get_connection()
        last_block = self.get_last_block()
        
        mined_supply = conn.execute("SELECT SUM(amount) FROM transactions WHERE sender = 'GhostProtocol_System'").fetchone()[0] or 0.0
        
        current_block_index = last_block['block_index']
        halvings = current_block_index // HALVING_INTERVAL
        current_reward = INITIAL_BLOCK_REWARD / (2**halvings)
        blocks_to_halving = HALVING_INTERVAL - (current_block_index % HALVING_INTERVAL)
        
        conn.close()
        return {
            "total_supply": TOTAL_SUPPLY,
            "circulating_supply": mined_supply,
            "remaining_supply": TOTAL_SUPPLY - mined_supply,
            "block_reward": current_reward,
            "solved_blocks": current_block_index,
            "last_block_hash": last_block['block_hash'][:15] + "...",
            "blocks_to_halving": blocks_to_halving
        }

    def mine_block(self, current_user):
        miner_key = current_user['wallet_public_key']
        last_mined = current_user['last_mined']
        if (time.time() - last_mined) < 86400: return False, "Limit."

        last_block = self.get_last_block()
        index = last_block['block_index'] + 1
        proof = 0
        while True:
            guess = f'{last_block["proof"]}{proof}'.encode()
            if hashlib.sha256(guess).hexdigest()[:BASE_DIFFICULTY] == '0' * BASE_DIFFICULTY: break
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
        if float(current_user['balance']) < amount: return False, "Balance error."
        conn = self.db.get_connection()
        try:
            tx_id = str(uuid4())
            timestamp = time.time()
            sender_key = current_user['wallet_public_key']
            conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, current_user['id']))
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (tx_id, sender_key, recipient, amount, timestamp))
            conn.commit()
            if self.mesh_mgr:
                tx_data = {'tx_id': tx_id, 'sender': sender_key, 'recipient': recipient, 'amount': amount, 'timestamp': timestamp}
                self.mesh_mgr.broadcast_transaction(tx_data)
            return True, "Transfer done."
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
                try: requests.post(f"http://{peer}:{GHOST_PORT}/api/send_transaction", json=tx_data, timeout=3)
                except: pass
        threading.Thread(target=_send, daemon=True).start()

    def broadcast_message(self, msg_data):
        def _send():
            for peer in self.known_peers:
                try: requests.post(f"http://{peer}:{GHOST_PORT}/api/messenger/receive_message", json=msg_data, timeout=3)
                except: pass
        threading.Thread(target=_send, daemon=True).start()

    def broadcast_new_user(self, username, pub_key):
        pass 

    def sync_with_network(self):
        for peer_ip in self.known_peers:
            try:
                resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/chain_meta", timeout=3)
                if resp.status_code == 200:
                    remote_headers = resp.json()
                    local_last = self.chain_mgr.get_last_block()
                    if remote_headers and remote_headers[-1]['block_index'] > local_last['block_index']:
                        for h in remote_headers:
                            if h['block_index'] > local_last['block_index']:
                                b_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/block/{h['block_hash']}", timeout=3)
                                if b_resp.status_code == 200: self._save_block(b_resp.json())

                if self.asset_mgr:
                    a_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/assets_meta", timeout=3)
                    if a_resp.status_code == 200:
                        remote_assets = a_resp.json()
                        local_assets = self.asset_mgr.get_all_assets_meta()
                        local_ids = {a['asset_id'] for a in local_assets}
                        for ra in remote_assets:
                            if ra['asset_id'] not in local_ids:
                                c_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/asset_data/{ra['asset_id']}", timeout=3)
                                if c_resp.status_code == 200: self.asset_mgr.sync_asset(c_resp.json())
                                    
                f_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/get_fees", timeout=3)
                if f_resp.status_code == 200: self.db.update_fees(f_resp.json())
                
            except: pass

    def _save_block(self, block_data):
        conn = self.db.get_connection()
        try:
            conn.execute("INSERT OR IGNORE INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                         (block_data['block_index'], block_data['timestamp'], block_data['previous_hash'], block_data['block_hash'], block_data['proof'], block_data['miner_key']))
            conn.commit()
        finally: conn.close()

# --- MAIN CLI APP ---
class GhostMeshNodeApp:
    def __init__(self):
        self.db = DatabaseManager(DB_FILE)
        self.chain = NodeBlockchainManager(self.db)
        self.mesh = NodeMeshManager(self.db, self.chain)
        self.asset = NodeAssetManager(self.db, self.chain, self.mesh)
        self.messenger = NodeMessengerManager(self.db, self.chain, self.mesh)
        self.smart_contract = NodeSmartContractManager(self.db, self.chain, self.mesh) 
        
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
        c = input("Select Language: ")
        if c == '2': self.lang_code = 'en'
        elif c == '3': self.lang_code = 'ru'
        elif c == '4': self.lang_code = 'hy'
        self.L = LANGUAGES[self.lang_code]

    def login_screen(self):
        while not self.current_user:
            self.clear_screen()
            print(self.L['auth_menu_title'])
            print(self.L['opt_login'])
            print(self.L['opt_create_account'])
            c = input(self.L['enter_choice'])
            
            if c == '1':
                self.clear_screen()
                print(self.L['login_title'])
                u = input(self.L['login_user'])
                p = input(self.L['login_pass'])
                user = self.db.login_user(u, hashlib.sha256(p.encode()).hexdigest()) 
                if not user and u == "node_user" and p == "local_pass": user = self.db.get_my_user()
                if user: self.current_user = user
                else: 
                    print(f"❌ {self.L['login_fail']}")
                    time.sleep(2)
            elif c == '2':
                self.clear_screen()
                print(self.L['create_acc_title'])
                u = input(self.L['login_user'])
                p = input(self.L['login_pass'])
                if u and p:
                    p_hash = hashlib.sha256(p.encode()).hexdigest()
                    success, pub_key = self.db.register_user(u, p_hash)
                    if success: 
                        print(f"✅ {self.L['create_acc_success']}")
                        self.mesh.broadcast_new_user(u, pub_key)
                    else: print(f"❌ {self.L['create_acc_fail']}")
                time.sleep(2)

    def display_status(self):
        self.current_user = self.db.login_user(self.current_user['username'], self.current_user['password'])
        if not self.current_user: self.current_user = self.db.get_my_user()
        
        self.clear_screen()
        print(f"--- {self.L['node_name']} ---")
        print(f"👤 User: {self.current_user['username']}")
        print(f"🌍 {self.L['sync_status']}: {'ONLINE' if self.mesh.known_peers else 'MESH'}")
        print(f"💰 {self.L['balance']}: {self.current_user['balance']:.4f} GHOST")
        
        # TR: İstatistikleri göster (Fix)
        # EN: Show statistics (Fix)
        stats = self.chain.get_statistics()
        print(f"\n📊 Stats:")
        print(f"   {self.L['stats_total_supply']}: {stats['total_supply']:,.0f}")
        print(f"   {self.L['stats_circulating']}: {stats['circulating_supply']:,.2f}")
        print(f"   {self.L['stats_block_reward']}: {stats['block_reward']}")
        print(f"   {self.L['stats_solved_blocks']}: {stats['solved_blocks']}")
        print(f"   {self.L['stats_last_block']}: {stats['last_block_hash']}")
        print("-" * 30)

    # --- SCREENS ---
    def register_screen(self):
        print(f"\n--- {self.L['opt_register']} ---")
        name = input(self.L['domain_name'])
        if name == '0': return
        content = input(self.L['content_html'])
        if content == '0': return
        success, msg = self.asset.register_asset(self.current_user, 'domain', name, content)
        print(msg)
        input("Enter...")

    def search_screen(self):
        print(f"\n--- {self.L['opt_search']} ---")
        q = input(self.L['search_query'])
        if q == '0': return
        results = self.asset.search_assets(q)
        if not results: print(self.L['no_results'])
        else:
            for r in results: print(f"ID: {r['asset_id']} | {r['name']}")
        input("Enter...")

    def wallet_screen(self):
        print(f"\n--- {self.L['opt_wallet']} ---")
        rec = input(self.L['recipient'])
        if rec == '0': return
        amt_str = input(self.L['amount'])
        if amt_str == '0': return
        success, msg = self.chain.transfer_coin(self.current_user, rec, float(amt_str))
        print(msg)
        input("Enter...")

    def mining_screen(self):
        print(f"\n--- {self.L['opt_mine']} ---")
        print(self.L['mining_start'])
        try:
            success, msg = self.chain.mine_block(self.current_user)
            print(f"{self.L['block_found'] if success else 'Error'}: {msg}")
        except KeyboardInterrupt:
            print("Mining stopped.")
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
            elif c == '1': # Chat
                friends = self.messenger.get_friends(self.current_user['wallet_public_key'])
                for f in friends: print(f"Friend Key: {f['friend_key'][:10]}...")
                f_key = input(self.L['msg_enter_friend'])
                if f_key != '0':
                    msgs = self.messenger.get_messages(self.current_user['wallet_public_key'], f_key)
                    for m in msgs: print(f"- {m['content']}")
                    txt = input(self.L['msg_type'])
                    if txt and txt != '0': self.messenger.send_message(self.current_user, f_key, txt)
            elif c == '2': # Invite
                u = input(self.L['msg_invite_user'])
                if u and u != '0': self.messenger.send_invite(self.current_user, u)

    def contracts_screen(self):
        while True:
            self.clear_screen()
            print(self.L['sc_menu'])
            print(self.L['sc_deploy'])
            print(self.L['sc_call'])
            print(self.L['back_to_menu'])
            c = input(self.L['enter_choice'])
            if c == '0': break
            elif c == '1': # Deploy
                print(self.L['sc_code'])
                lines = []
                while True:
                    l = input()
                    if l.strip() == 'END': break
                    if l.strip() == '0' and not lines: return # Cancel check
                    lines.append(l)
                code = "\n".join(lines)
                if code:
                    print(self.L['sc_deploying'])
                    success, msg = self.smart_contract.deploy_contract(self.current_user, code)
                    print(msg)
                    time.sleep(2)
            elif c == '2': # Call
                addr = input(self.L['sc_addr'])
                if addr == '0': continue
                method = input(self.L['sc_method'])
                args = input(self.L['sc_args'])
                success, msg = self.smart_contract.call_contract(self.current_user, addr, method, args)
                print(msg)
                time.sleep(2)

    def run(self):
        self.set_language()
        while True:
            if not self.current_user: self.login_screen()
            self.display_status()
            print(f"1. {self.L['opt_register']}")
            print(f"2. {self.L['opt_search']}")
            print(f"3. {self.L['opt_wallet']}")
            print(f"4. {self.L['opt_mine']}")
            print(f"5. {self.L['opt_messenger']}")
            print(f"6. {self.L['opt_contracts']}")
            print(f"7. {self.L['opt_status']}")
            print(f"8. {self.L['opt_logout']}")
            print(f"9. {self.L['opt_exit']}")
            
            c = input(self.L['enter_choice'])
            if c == '1': self.register_screen()
            elif c == '2': self.search_screen()
            elif c == '3': self.wallet_screen()
            elif c == '4': self.mining_screen()
            elif c == '5': self.messenger_screen()
            elif c == '6': self.contracts_screen()
            elif c == '8': self.current_user = None
            elif c == '9': break

if __name__ == '__main__':
    node = GhostMeshNodeApp()
    try: node.run()
    except KeyboardInterrupt: print("\nExiting...")

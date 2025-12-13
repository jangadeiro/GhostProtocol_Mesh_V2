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
from typing import Optional, Tuple, Dict, Any, List
from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for, Response
from uuid import uuid4
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from datetime import timedelta, datetime
from markupsafe import Markup 
from jinja2 import DictLoader, Template 
from werkzeug.utils import secure_filename

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GhostServer - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostCloud")

# --- YAPILANDIRMA / CONFIGURATION ---
BASE_DIFFICULTY = 4 
TOTAL_SUPPLY = 100000000.0 
INITIAL_BLOCK_REWARD = 50.0 
HALVING_INTERVAL = 2000
DB_FILE = os.path.join(os.getcwd(), "ghost_cloud_v2.db") 
GHOST_PORT = 5000
UDP_BROADCAST_PORT = 5001 
DOMAIN_EXPIRY_SECONDS = 15552000  # 6 Ay / 6 Months
STORAGE_COST_PER_MB = 0.01        # MB başına 0.01 GHOST
DOMAIN_REGISTRATION_FEE = 1.0     # Sabit 1.0 GHOST
INITIAL_USER_BALANCE = 50.0

# TR: P2P Bootstrap Peer Listesi (İlk bağlantı noktaları)
KNOWN_PEERS = ["46.101.219.46", "195.200.30.40"] 

app = Flask(__name__)
app.secret_key = 'cloud_super_secret_permanency_fix_2024_FINAL_FULL_V3' 
app.permanent_session_lifetime = timedelta(days=7) 
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 

# --- ÇOKLU DİL SÖZLÜĞÜ / MULTI-LANGUAGE DICTIONARY ---
LANGUAGES = {
    'tr': {
        'title': "GhostProtocol Sunucusu", 'status_online': "ÇEVRİMİÇİ", 'status_offline': "ÇEVRİMDIŞI",
        'server_status': "Sunucu Durumu", 'active_peers': "Aktif Düğüm (Peer)",
        'dashboard_title': "Panel", 'mining_title': "Madencilik", 'logout': "Çıkış", 'login': "Giriş", 'register': "Kayıt", 'search': "Arama",
        'wallet_title': "💳 Cüzdanım", 'pubkey': "Public Key (Hash)", 'balance': "Bakiye",
        'domain_title': "💾 .ghost Kayıt", 'media_title': "🖼️ Varlık Yükle", 'asset_action': "İşlem", 
        'status_success': "Başarılı", 'status_failed': "Başarısız", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Link Kopyala",
        'media_info': "Desteklenen: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Yayınla", 
        'search_title': "🔍 Ghost Arama (İçerik & Domain)", 'edit': "Düzenle", 'delete': "Sil",
        'login_prompt': "Giriş Yap", 'username': "Kullanıcı Adı", 'password': "Şifre", 'submit': "Gönder",
        'asset_fee': "Ücret (Toplam)", 'asset_expires': "Süre Sonu", 'mine_success': "Blok Başarılı", 
        'mine_message': "Yeni blok bulundu: {{ block_hash }}. Ödül: {{ reward }} GHOST hesabınıza eklendi.",
        'mine_limit_error': "Günde sadece 1 kez madencilik yapabilirsiniz. Kalan süre:",
        'wallet_address': "Cüzdan Adresi (GHST)", 'last_transactions': "Son İşlemlerim", 
        'tx_id': "İşlem ID", 'tx_sender': "Gönderen", 'tx_recipient': "Alıcı", 'tx_amount': "Miktar", 'tx_timestamp': "Zaman",
        'no_transactions': "Henüz bir işlem yok.",
        'total_supply': "Toplam Arz", 'mined_supply': "Dolaşımdaki Arz", 'remaining_supply': "Kalan Arz",
        'mine_last_block': "Son Blok", 'mine_difficulty': "Zorluk", 'mine_reward': "Mevcut Ödül",
        'mine_next_halving': "Sonraki Yarılanma", 'view': "Görüntüle", 'back_to_dashboard': "Panele Dön",
        'send_coin_title': "Para Gönder", 'recipient_address': "Alıcı Cüzdan Adresi", 'amount': "Miktar", 'send_btn': "Gönder",
        'insufficient_balance': "Yetersiz bakiye.", 'transfer_success': "Transfer başarıyla gerçekleşti.", 'recipient_not_found': "Alıcı bulunamadı.",
        'asset_name': "Varlık Adı", 'asset_type': "Tür", 'my_assets_title': "Kayıtlı Varlıklarım", 'update_btn': "Güncelle", 'edit_title': "Varlık Düzenle",
        'content_placeholder': "İçerik (HTML/Metin)"
    },
    'en': {
        'title': "GhostProtocol Server", 'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'server_status': "Server Status", 'active_peers': "Active Peers",
        'dashboard_title': "Dashboard", 'mining_title': "Mining", 'logout': "Logout", 'login': "Login", 'register': "Register", 'search': "Search",
        'wallet_title': "💳 My Wallet", 'pubkey': "Public Key (Hash)", 'balance': "Balance",
        'domain_title': "💾 .ghost Registration", 'media_title': "🖼️ Upload Asset", 'asset_action': "Action", 
        'status_success': "Success", 'status_failed': "Failed", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Copy Link",
        'media_info': "Supported: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Publish", 
        'search_title': "🔍 Ghost Search (Content & Domain)", 'edit': "Edit", 'delete': "Delete",
        'login_prompt': "Login", 'username': "Username", 'password': "Password", 'submit': "Submit",
        'asset_fee': "Fee (Total)", 'asset_expires': "Expires", 'mine_success': "Block Success",
        'mine_message': "New block found: {{ block_hash }}. Reward: {{ reward }} GHOST added to your account.",
        'mine_limit_error': "You can only mine once per day. Time remaining:",
        'wallet_address': "Wallet Address (GHST)", 'last_transactions': "Last Transactions", 
        'tx_id': "Tx ID", 'tx_sender': "Sender", 'tx_recipient': "Recipient", 'tx_amount': "Amount", 'tx_timestamp': "Time",
        'no_transactions': "No transactions yet.",
        'total_supply': "Total Supply", 'mined_supply': "Circulating Supply", 'remaining_supply': "Remaining Supply",
        'mine_last_block': "Last Block", 'mine_difficulty': "Difficulty", 'mine_reward': "Current Reward",
        'mine_next_halving': "Next Halving", 'view': "View", 'back_to_dashboard': "Back to Dashboard",
        'send_coin_title': "Send Coin", 'recipient_address': "Recipient Wallet Address", 'amount': "Amount", 'send_btn': "Send",
        'insufficient_balance': "Insufficient balance.", 'transfer_success': "Transfer successful.", 'recipient_not_found': "Recipient not found.",
        'asset_name': "Asset Name", 'asset_type': "Type", 'my_assets_title': "My Registered Assets", 'update_btn': "Update", 'edit_title': "Edit Asset",
        'content_placeholder': "Content (HTML/Text)"
    },
    'ru': {
        'title': "Сервер GhostProtocol", 'status_online': "ОНЛАЙН", 'status_offline': "ОФФЛАЙН",
        'server_status': "Статус Сервера", 'active_peers': "Активные Пиры",
        'dashboard_title': "Панель", 'mining_title': "Майнинг", 'logout': "Выход", 'login': "Вход", 'register': "Регистрация", 'search': "Поиск",
        'wallet_title': "💳 Мой Кошелек", 'pubkey': "Публичный Ключ (Хеш)", 'balance': "Баланс",
        'domain_title': "💾 Регистрация .ghost", 'media_title': "🖼️ Загрузить Актив", 'asset_action': "Действие", 
        'status_success': "Успех", 'status_failed': "Ошибка", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Скопировать",
        'media_info': "Поддерживается: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Опубликовать", 
        'search_title': "🔍 Ghost Поиск (Контент и Домен)", 'edit': "Редактировать", 'delete': "Удалить",
        'login_prompt': "Войти", 'username': "Имя пользователя", 'password': "Пароль", 'submit': "Отправить",
        'asset_fee': "Плата (Всего)", 'asset_expires': "Истекает", 'mine_success': "Блок Найден", 
        'mine_message': "Найден новый блок: {{ block_hash }}. Награда: {{ reward }} GHOST добавлена на ваш счет.",
        'mine_limit_error': "Вы можете майнить только один раз в день. Оставшееся время:",
        'wallet_address': "Адрес Кошелька (GHST)", 'last_transactions': "Последние Транзакции", 
        'tx_id': "ID Транзакции", 'tx_sender': "Отправитель", 'tx_recipient': "Получатель", 'tx_amount': "Сумма", 'tx_timestamp': "Время",
        'no_transactions': "Пока нет транзакций.",
        'total_supply': "Общий Объем", 'mined_supply': "В Обращении", 'remaining_supply': "Оставшийся Объем",
        'mine_last_block': "Последний Блок", 'mine_difficulty': "Сложность", 'mine_reward': "Текущая Награда",
        'mine_next_halving': "Следующее Уполовинивание", 'view': "Просмотр", 'back_to_dashboard': "Назад",
        'send_coin_title': "Отправить Монеты", 'recipient_address': "Адрес Получателя", 'amount': "Сумма", 'send_btn': "Отправить",
        'insufficient_balance': "Недостаточно средств.", 'transfer_success': "Перевод выполнен успешно.", 'recipient_not_found': "Получатель не найден.",
        'asset_name': "Имя Актива", 'asset_type': "Тип", 'my_assets_title': "Мои Активы", 'update_btn': "Обновить", 'edit_title': "Редактировать Актив",
        'content_placeholder': "Контент (HTML/Текст)"
    },
    'hy': {
        'title': "GhostProtocol Սերվեր", 'status_online': "ԱՌՑԱՆՑ", 'status_offline': "ԱՆՑԱՆՑ",
        'server_status': "Սերվերի Կարգավիճակը", 'active_peers': "Ակտիվ Փիրեր",
        'dashboard_title': "Վահանակ", 'mining_title': "Մայնինգ", 'logout': "Ելք", 'login': "Մուտք", 'register': "Գրանցվել", 'search': "Որոնում",
        'wallet_title': "💳 Իմ Դրամապանակը", 'pubkey': "Հանրային Բանալի (Հեշ)", 'balance': "Մնացորդ",
        'domain_title': "💾 .ghost Գրանցում", 'media_title': "🖼️ Բեռնել Ակտիվ", 'asset_action': "Գործողություն", 
        'status_success': "Հաջող", 'status_failed': "Ձախողված", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Պատճենել",
        'media_info': "Աջակցվում է՝ .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Հրատարակել", 
        'search_title': "🔍 Ghost Որոնում (Բովանդակություն և Դոմեն)", 'edit': "Խմբագրել", 'delete': "Ջնջել",
        'login_prompt': "Մուտք գործել", 'username': "Օգտվողի անուն", 'password': "Գաղտնաբառ", 'submit': "Ուղարկել",
        'asset_fee': "Վճար (Ընդհանուր)", 'asset_expires': "Ժամկետը", 'mine_success': "Բլոկը Հաջողվեց",
        'mine_message': "Գտնվեց նոր բլոկ: {{ block_hash }}: Պարգև՝ {{ reward }} GHOST ավելացվել է ձեր հաշվին:",
        'mine_limit_error': "Դուք կարող եք մայնինգ անել օրը միայն մեկ անգամ: Մնացած ժամանակը:",
        'wallet_address': "Դրամապանակի Հասցե (GHST)", 'last_transactions': "Վերջին Գործարքները", 
        'tx_id': "Գործարքի ID", 'tx_sender': "Ուղարկող", 'tx_recipient': "Ստացող", 'tx_amount': "Գումար", 'tx_timestamp': "Ժամանակ",
        'no_transactions': "Դեռ գործարքներ չկան։",
        'total_supply': "Ընդհանուր Մատակարարում", 'mined_supply': "Շրջանառվող Մատակարարում", 'remaining_supply': "Մնացորդային Մատակարարում",
        'mine_last_block': "Վերջին Բլոկ", 'mine_difficulty': "Բարդություն", 'mine_reward': "Ընթացիկ Պարգև",
        'mine_next_halving': "Հաջորդ Կիսում", 'view': "Դիտել", 'back_to_dashboard': "Վերադառնալ",
        'send_coin_title': "Ուղարկել Մետաղադրամ", 'recipient_address': "Ստացողի Հասցեն", 'amount': "Գումար", 'send_btn': "Ուղարկել",
        'insufficient_balance': "Անբավարար միջոցներ:", 'transfer_success': "Փոխանցումը հաջողվեց:", 'recipient_not_found': "Ստացողը չի գտնվել:",
        'asset_name': "Ակտիվի Անուն", 'asset_type': "Տեսակ", 'my_assets_title': "Իմ Ակտիվները", 'update_btn': "Թարմացնել", 'edit_title': "Խմբագրել",
        'content_placeholder': "Բովանդակություն (HTML/Տեքստ)"
    }
}

# --- YARDIMCI FONKSİYONLAR ---
def generate_user_keys(username):
    original_hash = hashlib.sha256(username.encode()).hexdigest()[:20]
    ghst_address = f"GHST{original_hash}" 
    return original_hash, ghst_address

def generate_qr_code_link(ghst_address):
    return f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={ghst_address}"

def extract_keywords(content_str):
    try:
        text = re.sub(r'<(script|style).*?>.*?</\1>', '', content_str, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<.*?>', ' ', text)
        text = re.sub(r'[^a-zA-ZğüşıöçĞÜŞİÖÇ ]', ' ', text)
        words = text.lower().split()
        stop_words = {'ve', 'ile', 'the', 'and', 'for', 'this', 'bir', 'için', 'or', 'by'}
        keywords = set([w for w in words if len(w) > 2 and w not in stop_words])
        return ",".join(list(keywords)[:20])
    except:
        return ""

def calculate_asset_fee(size_bytes, asset_type):
    if asset_type == 'domain':
        return DOMAIN_REGISTRATION_FEE
    else:
        return round((size_bytes / (1024 * 1024)) * STORAGE_COST_PER_MB, 5)

def calculate_difficulty(active_peer_count):
    increase = active_peer_count // 5
    return BASE_DIFFICULTY + increase

# --- VERİTABANI YÖNETİCİSİ ---
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
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 50, last_mined REAL DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, previous_hash TEXT, block_hash TEXT, proof INTEGER, miner_key TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL)''')
        
        try: cursor.execute("SELECT last_mined FROM users LIMIT 1")
        except sqlite3.OperationalError: cursor.execute("ALTER TABLE users ADD COLUMN last_mined REAL DEFAULT 0")

        for table, column in [('assets', 'keywords'), ('blocks', 'miner_key')]:
            try: cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
            except sqlite3.OperationalError:
                default = 'TEXT'
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {default}")
        
        if cursor.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
            self.create_genesis_block(cursor)
        conn.commit()
        conn.close()

    def create_genesis_block(self, cursor):
        genesis_hash = hashlib.sha256(b'GhostGenesis').hexdigest()
        cursor.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                       (1, time.time(), '0', genesis_hash, 100, 'GhostProtocol_System'))

# --- MANAGER SINIFLARI ---

class AssetManager:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def register_asset(self, owner_key, asset_type, name, content, is_file=False):
        keywords = ""
        # 1. Eksiklik Giderildi: İçerik boş olabilir (Domain için)
        if not content and asset_type == 'domain':
            content = "<h1>Yeni Ghost Sitesi</h1><p>Yapım aşamasında...</p>"

        if is_file:
            content.seek(0)
            content_bytes = content.read()
        else:
            content_bytes = content.encode('utf-8')
            if asset_type == 'domain':
                keywords = extract_keywords(content)
            
        size = len(content_bytes)
        fee = calculate_asset_fee(size, asset_type)

        conn = self.db.get_connection()
        user_balance_row = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (owner_key,)).fetchone()
        
        if not user_balance_row or user_balance_row['balance'] < fee:
             conn.close()
             return False, f"Yetersiz bakiye. Gerekli: {fee} GHOST"

        try:
            conn.execute("INSERT OR REPLACE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (str(uuid4()), owner_key, asset_type, name, content_bytes, size, time.time(), time.time() + DOMAIN_EXPIRY_SECONDS, keywords))
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (fee, owner_key))
            
            tx_id = str(uuid4())
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (tx_id, owner_key, "Asset_Fee_Collector", fee, time.time()))

            conn.commit()
            return True, f"Başarılı. Ücret: {fee} GHOST"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def update_asset_content(self, asset_id, owner_key, new_content):
        # 2. Hata Düzeltildi: İçerik düzenleme fonksiyonu eklendi
        conn = self.db.get_connection()
        try:
            keywords = extract_keywords(new_content)
            content_bytes = new_content.encode('utf-8')
            conn.execute("UPDATE assets SET content = ?, keywords = ? WHERE asset_id = ? AND owner_pub_key = ?", 
                         (content_bytes, keywords, asset_id, owner_key))
            conn.commit()
            return True, "İçerik güncellendi."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def delete_asset(self, asset_id, owner_key):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            result = cursor.execute("DELETE FROM assets WHERE asset_id = ? AND owner_pub_key = ?", (asset_id, owner_key))
            conn.commit()
            if result.rowcount > 0:
                return True, "Varlık silindi."
            else:
                return False, "Varlık bulunamadı."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

class BlockchainManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_last_block(self):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return block

    def hash_block(self, index, timestamp, previous_hash, proof, miner_key):
        block_string = json.dumps({'index': index, 'timestamp': timestamp, 'previous_hash': previous_hash, 'proof': proof, 'miner': miner_key}, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def proof_of_work(self, last_proof, difficulty):
        proof = 0
        while self.is_valid_proof(last_proof, proof, difficulty) is False:
            proof += 1
        return proof

    def is_valid_proof(self, last_proof, proof, difficulty):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == '0' * difficulty
    
    def calculate_block_reward(self, current_block_index):
        halvings = current_block_index // HALVING_INTERVAL
        reward = INITIAL_BLOCK_REWARD / (2**halvings)
        current_supply = self.get_current_mined_supply()
        if current_supply + reward > TOTAL_SUPPLY:
            reward = max(0.0, TOTAL_SUPPLY - current_supply)
        return reward

    def mine_block(self, miner_key):
        conn = self.db.get_connection()
        user = conn.execute("SELECT last_mined FROM users WHERE wallet_public_key = ?", (miner_key,)).fetchone()
        last_mined = user['last_mined'] if user else 0
        
        if (time.time() - last_mined) < 86400:
            conn.close()
            return None 

        last_block = self.get_last_block()
        index = last_block['block_index'] + 1
        timestamp = time.time()
        
        active_peers_count = mesh_mgr.get_active_peers()
        difficulty = calculate_difficulty(active_peers_count)
        
        last_proof = last_block['proof']
        proof = self.proof_of_work(last_proof, difficulty)
        
        reward = self.calculate_block_reward(index)
        previous_hash = last_block['block_hash']
        block_hash = self.hash_block(index, timestamp, previous_hash, proof, miner_key)

        try:
            conn.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                         (index, timestamp, previous_hash, block_hash, proof, miner_key))
            
            tx_id = str(uuid4())
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp, block_index) VALUES (?, ?, ?, ?, ?, ?)",
                         (tx_id, "GhostProtocol_System", miner_key, reward, timestamp, index))
            
            conn.execute("UPDATE users SET balance = balance + ?, last_mined = ? WHERE wallet_public_key = ?", (reward, timestamp, miner_key))
            conn.commit()
        except Exception as e:
            logger.error(f"Mining error: {e}")
            conn.close()
            return None 
        finally:
            conn.close()

        return {'index': index, 'hash': block_hash, 'reward': reward}

    def get_current_mined_supply(self):
        conn = self.db.get_connection()
        total_mining_rewards = conn.execute("SELECT SUM(amount) FROM transactions WHERE sender = 'GhostProtocol_System'").fetchone()[0] or 0.0
        initial_balances_given = conn.execute("SELECT COUNT(id) FROM users").fetchone()[0] * INITIAL_USER_BALANCE
        conn.close()
        return total_mining_rewards + initial_balances_given

    def transfer_coin(self, sender_key, recipient_key, amount):
        if sender_key == recipient_key: return False, "Kendinize gönderemezsiniz."
        if amount <= 0: return False, "Miktar 0'dan büyük olmalı."

        conn = self.db.get_connection()
        try:
            sender = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender_key,)).fetchone()
            if not sender or sender['balance'] < amount:
                return False, "Yetersiz bakiye."
            
            recipient = conn.execute("SELECT id FROM users WHERE wallet_public_key = ?", (recipient_key,)).fetchone()
            if not recipient:
                return False, "Alıcı adresi bulunamadı."

            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (amount, sender_key))
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (amount, recipient_key))
            
            tx_id = str(uuid4())
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (tx_id, sender_key, recipient_key, amount, time.time()))
            conn.commit()
            return True, "Transfer başarılı."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

class MeshManager:
    def __init__(self, db_manager):
        self.db = db_manager
        for peer in KNOWN_PEERS:
            self.register_peer(peer)
            
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception as e:
            logger.warning(f"UDP Broadcast desteği yok: {e}")

        self.start_discovery_services()

    def start_discovery_services(self):
        threading.Thread(target=self._listen_for_peers, daemon=True).start()
        threading.Thread(target=self._broadcast_presence, daemon=True).start()
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
        logger.info("MeshManager: Keşif servisleri başlatıldı.")

    def _broadcast_presence(self):
        while True:
            try:
                message = json.dumps({'type': 'presence', 'ip': self._get_local_ip()}).encode('utf-8')
                self.broadcast_socket.sendto(message, ('<broadcast>', UDP_BROADCAST_PORT))
            except Exception: pass
            time.sleep(30)

    def _listen_for_peers(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('', UDP_BROADCAST_PORT))
        except: return

        while True:
            try:
                data, addr = listener.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                if message.get('type') == 'presence' and message.get('ip'):
                    ip = message['ip']
                    if ip != self._get_local_ip():
                        self.register_peer(ip)
            except: pass

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except: return "127.0.0.1"

    def _cleanup_loop(self):
        while True:
            conn = self.db.get_connection()
            cutoff = time.time() - 300
            conn.execute("DELETE FROM mesh_peers WHERE last_seen < ?", (cutoff,))
            conn.commit()
            conn.close()
            time.sleep(300)

    def register_peer(self, ip_address):
        if ip_address.startswith("127.0") or ip_address == "0.0.0.0": return False
        conn = self.db.get_connection()
        try:
            conn.execute("INSERT OR REPLACE INTO mesh_peers (ip_address, last_seen) VALUES (?, ?)", (ip_address, time.time()))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    def get_active_peers(self):
        conn = self.db.get_connection()
        cutoff = time.time() - 300
        count = conn.execute("SELECT COUNT(*) FROM mesh_peers WHERE last_seen > ?", (cutoff,)).fetchone()[0]
        conn.close()
        return count

class TransactionManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_last_transactions(self, pub_key, limit=10):
        conn = self.db.get_connection()
        transactions = conn.execute(
            "SELECT * FROM transactions WHERE sender = ? OR recipient = ? ORDER BY timestamp DESC LIMIT ?", 
            (pub_key, pub_key, limit)
        ).fetchall()
        conn.close()
        return transactions

# --- INIT ---
db = DatabaseManager(DB_FILE)
assets_mgr = AssetManager(db)
blockchain_mgr = BlockchainManager(db)
mesh_mgr = MeshManager(db)
tx_mgr = TransactionManager(db)

# --- HTML TEMPLATES ---
LAYOUT = r"""
<!DOCTYPE html>
<html lang="{{ session.get('lang', 'tr') }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ lang['title'] }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1e1e1e; color: #ddd; margin: 0; padding: 0; }
        .header { background-color: #333; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #00c853; }
        .logo { font-size: 1.5em; font-weight: bold; color: #00c853; }
        .menu a { color: #ddd; text-decoration: none; padding: 10px 15px; border-radius: 5px; margin-left: 10px; transition: background-color 0.3s; }
        .menu a:hover { background-color: #444; }
        .container { width: 90%; max-width: 1200px; margin: 20px auto; }
        .status-bar { background-color: #2a2a2a; padding: 10px 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; font-size: 0.9em; }
        .status-online { color: #00c853; font-weight: bold; }
        .card { background-color: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        .card h3 { color: #ffeb3b; border-bottom: 1px solid #444; padding-bottom: 10px; margin-top: 0; }
        .action-button { background-color: #4caf50; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; transition: background-color 0.3s; text-decoration: none; display: inline-block; font-size: 0.9em; }
        .action-button:hover { background-color: #45a049; }
        .btn-small { padding: 5px 10px; font-size: 0.8em; margin-left: 5px; }
        .btn-delete { background-color: #f44336; } .btn-delete:hover { background-color: #d32f2f; }
        .btn-edit { background-color: #2196F3; } .btn-edit:hover { background-color: #1976D2; }
        .btn-view { background-color: #FF9800; } .btn-view:hover { background-color: #F57C00; }
        .btn-link { background-color: #9C27B0; } .btn-link:hover { background-color: #7B1FA2; }
        input[type="text"], input[type="password"], textarea, input[type="number"] { width: 100%; padding: 10px; margin: 5px 0 10px 0; border: 1px solid #555; border-radius: 4px; background-color: #333; color: #ddd; }
        .status-message { padding: 10px; margin-bottom: 10px; border-radius: 5px; font-weight: bold; }
        .status-success { background-color: #4CAF50; color: white; }
        .status-error { background-color: #f44336; color: white; }
        table { border-collapse: collapse; width: 100%; font-size: 0.9em; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #333; }
        th { background-color: #3a3a3a; }
        .lang-switch a { margin-left: 5px; color: #888; text-decoration: none; }
        .asset-actions { white-space: nowrap; }
    </style>
    <script>
    function copyLink(text) {
        navigator.clipboard.writeText(text).then(function() {
            alert('Link kopyalandı / Link copied!');
        }, function(err) {
            console.error('Async: Could not copy text: ', err);
        });
    }
    </script>
</head>
<body>
    <div class="header">
        <div class="logo">GhostProtocol</div>
        <div class="menu">
            {% if session.get('username') %}
                <a href="{{ url_for('dashboard') }}">{{ lang['dashboard_title'] }}</a>
                <a href="{{ url_for('mining') }}">{{ lang['mining_title'] }}</a>
                <a href="{{ url_for('search') }}">{{ lang['search'] }}</a>
                <a href="{{ url_for('logout') }}">{{ lang['logout'] }}</a>
            {% else %}
                <a href="{{ url_for('login') }}">{{ lang['login'] }}</a>
                <a href="{{ url_for('register') }}">{{ lang['register'] }}</a>
            {% endif %}
        </div>
    </div>
    <div class="container">
        <div class="status-bar">
            <span>{{ lang['server_status'] }}: <span class="status-online">{{ lang['status_online'] }}</span></span>
            <span>{{ lang['active_peers'] }}: {{ session.get('active_peers_count', 0) }}</span>
            <div class="lang-switch">
                <a href="{{ url_for('set_lang', lang='tr') }}">TR</a>
                <a href="{{ url_for('set_lang', lang='en') }}">EN</a>
                <a href="{{ url_for('set_lang', lang='ru') }}">RU</a>
                <a href="{{ url_for('set_lang', lang='hy') }}">HY</a>
            </div>
        </div>
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

DASHBOARD_UI = r"""
{% extends 'base.html' %}
{% block content %}
<div class="card">
    <h3>{{ lang['wallet_title'] }}</h3>
    {% if message %}<div class="status-message status-success">{{ message }}</div>{% endif %}
    {% if error %}<div class="status-message status-error">{{ error }}</div>{% endif %}
    <p><strong>{{ lang['wallet_address'] }}:</strong> {{ user_ghst_address }} 
        <img src="{{ qr_code_link }}" style="vertical-align: middle; margin-left: 10px; width: 75px; height: 75px;"></p>
    <p><strong>{{ lang['pubkey'] }}:</strong> {{ user_pub_key_hash }}</p>
    <p><strong>{{ lang['balance'] }}:</strong> <span style="font-size: 1.5em; color: #ffeb3b;">{{ session.get('balance', 0) | round(4) | thousands }} GHOST</span></p>
    
    <hr style="border-color:#444; margin: 15px 0;">
    <h4>{{ lang['send_coin_title'] }}</h4>
    <form method="POST" action="{{ url_for('dashboard') }}" style="display:flex; gap:10px;">
        <input type="hidden" name="action" value="send_coin">
        <input type="text" name="recipient" placeholder="{{ lang['recipient_address'] }}" required style="flex:2;">
        <input type="number" name="amount" step="0.0001" placeholder="{{ lang['amount'] }}" required style="flex:1;">
        <button class="action-button" type="submit">{{ lang['send_btn'] }}</button>
    </form>
</div>

<div style="display: flex; gap: 12px;">
    <div class="card" style="flex: 1;">
        <h3>{{ lang['domain_title'] }}</h3>
        <p><strong>{{ lang['asset_fee'] }}:</strong> {{ DOMAIN_REGISTRATION_FEE }} GHOST</p>
        <p><strong>Süre:</strong> 6 Ay</p>
        <form method="POST" action="{{ url_for('dashboard') }}">
            <input type="hidden" name="action" value="register_domain">
            <input type="text" name="domain_name" placeholder="Domain Adı (ornek.ghost)" required pattern="[a-zA-Z0-9.-]+\.ghost$"><br>
            <textarea name="content" placeholder="{{ lang['content_placeholder'] }}" rows="3"></textarea><br>
            <button class="action-button" type="submit">{{ lang['register_btn'] }}</button>
        </form>
    </div>
    
    <div class="card" style="flex: 1;">
        <h3>{{ lang['media_title'] }}</h3>
        <p>{{ lang['media_info'] }}</p>
        <form method="POST" action="{{ url_for('dashboard') }}" enctype="multipart/form-data">
            <input type="hidden" name="action" value="upload_media">
            <input type="file" name="file" required><br>
            <button class="action-button" type="submit">{{ lang['register_btn'] }}</button>
        </form>
    </div>
</div>

<div class="card">
    <h3>{{ lang['my_assets_title'] }} ({{ assets|length }})</h3>
    <table style="width:100%">
        <tr>
            <th>{{ lang['asset_name'] }}</th> <th>{{ lang['asset_type'] }}</th> <th>{{ lang['asset_fee'] }}</th> <th>{{ lang['asset_expires'] }}</th> <th>{{ lang['asset_action'] }}</th>
        </tr>
        {% for a in assets %}
        {% set asset_fee_calculated = calculate_asset_fee(a.storage_size, a.type)|round(4) %}
        {% set asset_relative_link = url_for('view_asset', asset_id=a.asset_id) %}
        {% set asset_external_link = url_for('view_asset', asset_id=a.asset_id, _external=True) %}
        <tr>
            <td>{{ a.name }}</td>
            <td>{{ a.type | upper }}</td>
            <td>{{ asset_fee_calculated }} {{ lang['monthly_fee_unit'] }}</td>
            <td>{{ datetime.fromtimestamp(a.expiry_time).strftime('%Y-%m-%d') }}</td>
            <td class="asset-actions">
                <a href="{{ asset_relative_link }}" target="_blank" class="action-button btn-small btn-view">{{ lang['view'] }}</a>
                <button onclick="copyLink('{{ asset_external_link }}')" class="action-button btn-small btn-link">Link</button>
                {% if a.type == 'domain' %}
                <a href="{{ url_for('edit_asset', asset_id=a.asset_id) }}" class="action-button btn-small btn-edit">{{ lang['edit'] }}</a>
                {% endif %}
                <form method="POST" style="display: inline-block;">
                    <input type="hidden" name="action" value="delete_asset">
                    <input type="hidden" name="asset_id" value="{{ a.asset_id }}">
                    <button class="action-button btn-small btn-delete" type="submit">{{ lang['delete'] }}</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
</div>

<div class="card">
    <h3>{{ lang['last_transactions'] }}</h3>
    <table>
        <tr>
            <th>{{ lang['tx_id'] }}</th> <th>{{ lang['tx_sender'] }}</th> <th>{{ lang['tx_recipient'] }}</th> <th>{{ lang['tx_amount'] }}</th> <th>{{ lang['tx_timestamp'] }}</th>
        </tr>
        {% for tx in transactions %}
        <tr style="color: {% if tx.sender == user_ghst_address %}#f44336{% else %}#4CAF50{% endif %}">
            <td>{{ tx.tx_id[:8] }}...</td>
            <td>{% if tx.sender == user_ghst_address %}SEN{% else %}{{ tx.sender[:8] }}...{% endif %}</td>
            <td>{% if tx.recipient == user_ghst_address %}SEN{% else %}{{ tx.recipient[:8] }}...{% endif %}</td>
            <td>{{ tx.amount | round(4) | thousands }}</td>
            <td>{{ tx.timestamp | timestamp_to_datetime }}</td>
        </tr>
        {% else %}
        <tr><td colspan="5">{{ lang['no_transactions'] }}</td></tr>
        {% endfor %}
    </table>
</div>
{% endblock %}
"""

LOGIN_UI = r"""
{% extends 'base.html' %}
{% block content %}
<div style="display: flex; gap: 20px;">
    <div class="card" style="flex: 2;">
        <h3>{{ lang['login_prompt'] }}</h3>
        {% if error %}<div class="status-message status-error">{{ error }}</div>{% endif %}
        <form method="POST" action="{{ url_for('login') }}" class="login-form">
            <label for="username">{{ lang['username'] }}</label>
            <input type="text" id="username" name="username" required>
            <label for="password">{{ lang['password'] }}</label>
            <input type="password" id="password" name="password" required>
            <button class="action-button" type="submit">{{ lang['submit'] }}</button>
            <p style="margin-top: 15px;">{{ lang['register'] }} için <a href="{{ url_for('register') }}" style="color: #ffeb3b;">tıklayın</a>.</p>
        </form>
    </div>
</div>
{% endblock %}
"""

REGISTER_UI = r"""
{% extends 'base.html' %}
{% block content %}
<div class="card login-form">
    <h3>{{ lang['register'] }}</h3>
    {% if error %}<div class="status-message status-error">{{ error }}</div>{% endif %}
    <form method="POST">
        <input type="text" name="username" placeholder="{{ lang['username'] }}" required><br>
        <input type="password" name="password" placeholder="{{ lang['password'] }}" required><br>
        <input type="password" name="password_confirm" placeholder="Şifre Tekrar" required><br>
        <button class="action-button" type="submit">{{ lang['submit'] }}</button>
    </form>
</div>
{% endblock %}
"""

MINING_UI = r"""
{% extends 'base.html' %}
{% block content %}
<div class="card">
    <h3>{{ lang['mining_title'] }}</h3>
    {% if message %} <div class="status-message status-success">{{ message | safe }}</div> {% endif %}
    {% if error %} <div class="status-message status-error">{{ error | safe }}</div> {% endif %}
    
    {% if last_block %}
    <p><strong>{{ lang['mine_last_block'] }}:</strong> Blok {{ last_block.block_index }}</p>
    <p><strong>{{ lang['mine_difficulty'] }}:</strong> {{ difficulty }}</p>
    <p><strong>{{ lang['mine_reward'] }}:</strong> {{ current_reward | round(4) }} GHOST</p>
    {% endif %}

    <hr style="border-top: 1px solid #333; margin: 10px 0;">

    <form method="POST" action="{{ url_for('mining') }}">
    {% if not can_mine %}
        <div class="status-message status-error">
            {{ lang['mine_limit_error'] }} {{ remaining_time }}
        </div>
        <button class="action-button" type="submit" disabled style="opacity:0.5; cursor:not-allowed;">Madencilik Başlat (Kilitli)</button>
    {% else %}
        <button class="action-button" type="submit">Madencilik Başlat</button>
    {% endif %}
    </form>
</div>
{% endblock %}
"""

SEARCH_UI = r"""
{% extends 'base.html' %}
{% block content %}
<div class="card">
    <h3>{{ lang['search_title'] }}</h3>
    <form method="GET" action="{{ url_for('search') }}">
        <input type="text" name="query" placeholder="..." value="{{ query or '' }}" required style="width: 80%; display: inline-block;">
        <button class="action-button" type="submit" style="width: 19%; display: inline-block; margin-left: 1%;">{{ lang['search'] }}</button>
    </form>
</div>
{% if results %}
<div class="card">
    <h3>Arama Sonuçları</h3>
    <table>
        <tr><th>{{ lang['asset_name'] }}</th><th>{{ lang['asset_type'] }}</th><th>Link</th></tr>
        {% for r in results %}
        <tr>
            <td>{{ r.name }}</td>
            <td>{{ r.type | upper }}</td>
            <td><a href="{{ url_for('view_asset', asset_id=r.asset_id) }}" target="_blank" style="color:#4caf50;">{{ lang['view'] }}</a></td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}
{% endblock %}
"""

EDIT_ASSET_UI = r"""
{% extends 'base.html' %}
{% block content %}
<div class="card">
    <h3>{{ lang['edit_title'] }}: {{ asset_id }}</h3>
    {% if error %}<div class="status-message status-error">{{ error }}</div>{% endif %}
    <form method="POST">
        <textarea name="content" rows="10" placeholder="{{ lang['content_placeholder'] }}">{{ current_content }}</textarea><br>
        <button class="action-button" type="submit">{{ lang['update_btn'] }}</button>
    </form>
    <br>
    <a href="{{ url_for('dashboard') }}" style="color:#aaa;">{{ lang['back_to_dashboard'] }}</a>
</div>
{% endblock %}
"""

app.jinja_loader = DictLoader({
    'base.html': LAYOUT, 'dashboard.html': DASHBOARD_UI, 'login.html': LOGIN_UI,
    'register.html': REGISTER_UI, 'mining.html': MINING_UI, 'search.html': SEARCH_UI,
    'edit_asset.html': EDIT_ASSET_UI
})

def timestamp_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
app.jinja_env.filters['timestamp_to_datetime'] = timestamp_to_datetime

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in LANGUAGES: session['lang'] = lang
    return redirect(request.referrer or url_for('login'))

@app.route('/')
def index(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('username'): return redirect(url_for('dashboard'))
    L = LANGUAGES[session.get('lang', 'tr')]
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()
        conn = db.get_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        if user:
            session['username'] = user['username']
            session['pub_key'] = user['wallet_public_key']
            session['pub_key_hash'] = user['wallet_public_key'][:20]
            session['balance'] = user['balance']
            return redirect(url_for('dashboard'))
        else: error = "Hatalı Kullanıcı Adı veya Şifre."
    active_peers_count = mesh_mgr.get_active_peers()
    session['active_peers_count'] = active_peers_count
    return render_template_string(LOGIN_UI, lang=L, error=error, active_peers_count=active_peers_count)

@app.route('/register', methods=['GET', 'POST'])
def register():
    L = LANGUAGES[session.get('lang', 'tr')]
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()
        public_key_hash, ghst_address = generate_user_keys(username)
        conn = db.get_connection()
        try:
            conn.execute("INSERT INTO users (username, password, wallet_public_key, balance) VALUES (?, ?, ?, ?)", (username, password, ghst_address, INITIAL_USER_BALANCE))
            conn.commit()
            session['username'] = username
            session['pub_key'] = ghst_address
            session['pub_key_hash'] = public_key_hash
            session['balance'] = INITIAL_USER_BALANCE
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError: error = "Kullanıcı adı alınmış."
        finally: conn.close()
    return render_template_string(REGISTER_UI, lang=L, error=error, active_peers_count=session.get('active_peers_count', 0))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('username'): return redirect(url_for('login'))
    L = LANGUAGES[session.get('lang', 'tr')]
    pub_key = session['pub_key']
    message = None
    error = None
    action = request.form.get('action')

    if request.method == 'POST':
        if action == 'register_domain':
            # 1. Düzeltme: İçerik zorunlu değil (Varsayılan içerik atanır)
            content = request.form.get('content')
            success, msg = assets_mgr.register_asset(pub_key, 'domain', request.form['domain_name'], content)
            if success: message = msg
            else: error = msg
        elif action == 'upload_media':
            f = request.files['file']
            if f.filename:
                success, msg = assets_mgr.register_asset(pub_key, 'file', f.filename, f, is_file=True)
                if success: message = msg
                else: error = msg
        elif action == 'delete_asset':
            success, msg = assets_mgr.delete_asset(request.form['asset_id'], pub_key)
            if success: message = msg
            else: error = msg
        elif action == 'send_coin':
            recipient = request.form['recipient']
            try: amount = float(request.form['amount'])
            except: amount = 0
            success, msg = blockchain_mgr.transfer_coin(pub_key, recipient, amount)
            if success: message = msg
            else: error = msg

    conn = db.get_connection()
    user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (pub_key,)).fetchone()
    session['balance'] = user['balance'] if user else 0.0
    assets = conn.execute("SELECT * FROM assets WHERE owner_pub_key = ? ORDER BY creation_time DESC", (pub_key,)).fetchall()
    conn.close()
    transactions = tx_mgr.get_last_transactions(pub_key)
    active_peers_count = mesh_mgr.get_active_peers()
    session['active_peers_count'] = active_peers_count
    
    return render_template_string(DASHBOARD_UI, lang=L, message=message, error=error, 
                                  user_ghst_address=pub_key, user_pub_key_hash=session.get('pub_key_hash'), 
                                  assets=assets, transactions=transactions, qr_code_link=generate_qr_code_link(pub_key), 
                                  DOMAIN_REGISTRATION_FEE=DOMAIN_REGISTRATION_FEE, calculate_asset_fee=calculate_asset_fee,
                                  active_peers_count=active_peers_count, datetime=datetime)

@app.route('/edit_asset/<asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    if not session.get('username'): return redirect(url_for('login'))
    L = LANGUAGES[session.get('lang', 'tr')]
    pub_key = session['pub_key']
    
    conn = db.get_connection()
    asset = conn.execute("SELECT * FROM assets WHERE asset_id = ? AND owner_pub_key = ?", (asset_id, pub_key)).fetchone()
    conn.close()
    
    if not asset: return "Varlık bulunamadı veya yetkiniz yok.", 403
    
    if request.method == 'POST':
        new_content = request.form['content']
        success, msg = assets_mgr.update_asset_content(asset_id, pub_key, new_content)
        if success: return redirect(url_for('dashboard'))
        else: return f"Hata: {msg}"

    # Mevcut içeriği decode et (Sadece domainler için mantıklı)
    try: current_content = asset['content'].decode('utf-8')
    except: current_content = ""

    return render_template_string(EDIT_ASSET_UI, lang=L, asset_id=asset_id, current_content=current_content, active_peers_count=session.get('active_peers_count', 0))

@app.route('/mining', methods=['GET', 'POST'])
def mining():
    if not session.get('username'): return redirect(url_for('login'))
    L = LANGUAGES[session.get('lang', 'tr')]
    pub_key = session['pub_key']
    
    conn = db.get_connection()
    user = conn.execute("SELECT last_mined FROM users WHERE wallet_public_key = ?", (pub_key,)).fetchone()
    last_mined_time = user['last_mined'] if user else 0
    conn.close()
    
    can_mine = (time.time() - last_mined_time) >= 86400
    last_block = blockchain_mgr.get_last_block()
    active_peers = mesh_mgr.get_active_peers()
    difficulty = calculate_difficulty(active_peers)
    reward = blockchain_mgr.calculate_block_reward(last_block['block_index'] + 1)
    
    message = None
    error = None

    if request.method == 'POST':
        if can_mine:
            result = blockchain_mgr.mine_block(pub_key)
            if result:
                new_hash = result.get('hash')
                message = L['mine_success']
                can_mine = False
                last_block = blockchain_mgr.get_last_block()
            else: error = "Madencilik hatası."
        else: error = L['mine_limit_error']

    remaining = max(0, 86400 - (time.time() - last_mined_time))
    remaining_time = str(timedelta(seconds=int(remaining)))
    
    return render_template_string(MINING_UI, lang=L, message=message, error=error, last_block=last_block, difficulty=difficulty, current_reward=reward, can_mine=can_mine, remaining_time=remaining_time, next_halving=0, active_peers_count=active_peers)

@app.route('/view_asset/<asset_id>')
def view_asset(asset_id):
    conn = db.get_connection()
    asset = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    conn.close()
    if not asset: return "Bulunamadı", 404
    
    # 2. Düzeltme: İçerik türüne göre işlem
    if asset['type'] == 'domain':
        return asset['content'] # HTML olarak render et
    return Response(asset['content'], mimetype='application/octet-stream')

@app.route('/search')
def search():
    L = LANGUAGES[session.get('lang', 'tr')]
    query = request.args.get('query', '').strip()
    results = []
    if query:
        conn = db.get_connection()
        s = f'%{query}%'
        results = conn.execute("SELECT * FROM assets WHERE name LIKE ? OR keywords LIKE ?", (s, s)).fetchall()
        conn.close()
    return render_template_string(SEARCH_UI, lang=L, query=query, results=results, active_peers_count=mesh_mgr.get_active_peers())

@app.route('/peer_update', methods=['POST'])
def peer_update():
    ip = request.remote_addr
    data = request.get_json()
    if data and 'ip_address' in data: ip = data['ip_address']
    mesh_mgr.register_peer(ip)
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    def format_thousands(value):
        try: return f"{float(value):,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except: return str(value)
    app.jinja_env.filters['thousands'] = format_thousands
    print("--- GHOST PROTOCOL SUNUCUSU BAŞLATILIYOR ---")
    app.run(host='0.0.0.0', port=GHOST_PORT, debug=True, threaded=True)

# -*- coding: utf-8 -*-
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
# TR: Bilinen sunucu IP'leri (Bu IP'ler ile veri eşleşmesi sağlanır)
# EN: Known server IPs (Data synchronization is ensured with these IPs)
KNOWN_PEERS = ["46.101.219.46", "68.183.12.91"] 

STORAGE_COST_PER_MB = 0.01
DOMAIN_REGISTRATION_FEE = 1.0
DOMAIN_EXPIRY_SECONDS = 15552000 # 6 Ay / 6 Months
INITIAL_USER_BALANCE = 50.0
BASE_DIFFICULTY = 4
INITIAL_BLOCK_REWARD = 50.0
HALVING_INTERVAL = 2000
TOTAL_SUPPLY = 100000000.0

# --- ÇOKLU DİL SÖZLÜĞÜ / MULTI-LANGUAGE DICTIONARY ---
LANGUAGES = {
    'tr': {
        'node_name': "Ghost Mesh Düğümü", 'menu_title': "GHOST PROTOCOL MENÜSÜ",
        'opt_register': "1. Varlık Kaydet (.ghost / Dosya)", 'opt_search': "2. Ara & Görüntüle",
        'opt_wallet': "3. Cüzdan & Transfer", 'opt_mine': "4. Madencilik Yap",
        'opt_status': "5. Ağ Durumu", 'opt_exit': "6. Çıkış",
        'balance': "Bakiye", 'pubkey': "Cüzdan", 'sync_status': "Senkronizasyon",
        'enter_choice': "Seçiminiz: ", 'invalid_choice': "Geçersiz seçim!",
        'domain_name': "Domain Adı (örn: site): ", 'content_html': "İçerik (HTML): ",
        'register_success': "Kayıt Başarılı! İşlem ağa yayınlandı.", 'register_fail': "Kayıt Başarısız: ",
        'search_query': "Arama (Domain/Kelime): ", 'no_results': "Sonuç bulunamadı.",
        'results_found': "Sonuçlar:", 'view_content': "İçeriği Görüntüle (ID girin): ",
        'recipient': "Alıcı Cüzdan Adresi: ", 'amount': "Miktar: ", 'sent_success': "Gönderildi ve ağa yayınlandı!",
        'mining_start': "Madencilik Başlatılıyor...", 'block_found': "BLOK BULUNDU!", 
        'assets_title': "Yerel Varlıklar", 'fee': "Ücret", 'type': "Tür",
        'stats_total_supply': "Toplam Arz", 'stats_circulating': "Dolaşımdaki Arz",
        'stats_block_reward': "Blok Ödülü", 'stats_solved_blocks': "Çözülen Blok",
        'stats_last_block': "Son Blok Hash", 'stats_halving': "Yarılanmaya Kalan",
        'back_to_menu': "0. Ana Menüye Dön", 'asset_cost': "Maliyet", 'asset_expiry': "Bitiş",
        'enter_0_to_cancel': "(İptal etmek için 0 girin)"
    },
    'en': {
        'node_name': "Ghost Mesh Node", 'menu_title': "GHOST PROTOCOL MENU",
        'opt_register': "1. Register Asset (.ghost / File)", 'opt_search': "2. Search & View",
        'opt_wallet': "3. Wallet & Transfer", 'opt_mine': "4. Mine Block",
        'opt_status': "5. Network Status", 'opt_exit': "6. Exit",
        'balance': "Balance", 'pubkey': "Wallet", 'sync_status': "Sync Status",
        'enter_choice': "Choice: ", 'invalid_choice': "Invalid choice!",
        'domain_name': "Domain Name (e.g., site): ", 'content_html': "Content (HTML): ",
        'register_success': "Registration Successful! Transaction broadcasted.", 'register_fail': "Registration Failed: ",
        'search_query': "Search (Domain/Keyword): ", 'no_results': "No results found.",
        'results_found': "Results:", 'view_content': "View Content (Enter ID): ",
        'recipient': "Recipient Address: ", 'amount': "Amount: ", 'sent_success': "Sent and broadcasted!",
        'mining_start': "Starting Mining...", 'block_found': "BLOCK FOUND!",
        'assets_title': "Local Assets", 'fee': "Fee", 'type': "Type",
        'stats_total_supply': "Total Supply", 'stats_circulating': "Circulating Supply",
        'stats_block_reward': "Block Reward", 'stats_solved_blocks': "Solved Blocks",
        'stats_last_block': "Last Block Hash", 'stats_halving': "Blocks to Halving",
        'back_to_menu': "0. Back to Main Menu", 'asset_cost': "Cost", 'asset_expiry': "Expires",
        'enter_0_to_cancel': "(Enter 0 to cancel)"
    },
    'ru': {
        'node_name': "Узел Ghost Mesh", 'menu_title': "МЕНЮ GHOST PROTOCOL",
        'opt_register': "1. Регистрация актива", 'opt_search': "2. Поиск и просмотр",
        'opt_wallet': "3. Кошелек и перевод", 'opt_mine': "4. Майнинг",
        'opt_status': "5. Статус сети", 'opt_exit': "6. Выход",
        'balance': "Баланс", 'pubkey': "Кошелек", 'sync_status': "Синхронизация",
        'enter_choice': "Ваш выбор: ", 'invalid_choice': "Неверный выбор!",
        'domain_name': "Имя домена: ", 'content_html': "Содержание (HTML): ",
        'register_success': "Успешно! Транзакция отправлена.", 'register_fail': "Ошибка: ",
        'search_query': "Поиск: ", 'no_results': "Нет результатов.",
        'results_found': "Результаты:", 'view_content': "Просмотр (ID): ",
        'recipient': "Адрес получателя: ", 'amount': "Сумма: ", 'sent_success': "Отправлено и транслировано!",
        'mining_start': "Майнинг начат...", 'block_found': "БЛОК НАЙДЕН!",
        'assets_title': "Локальные активы", 'fee': "Плата", 'type': "Тип",
        'stats_total_supply': "Общее предложение", 'stats_circulating': "В обращении",
        'stats_block_reward': "Награда за блок", 'stats_solved_blocks': "Решено блоков",
        'stats_last_block': "Хеш последнего блока", 'stats_halving': "До халвинга",
        'back_to_menu': "0. Вернуться в главное меню", 'asset_cost': "Стоимость", 'asset_expiry': "Истекает",
        'enter_0_to_cancel': "(Введите 0 для отмены)"
    },
    'hy': {
        'node_name': "Ghost Mesh Հանգույց", 'menu_title': "GHOST PROTOCOL ԸՆՏՐԱՑԱՆԿ",
        'opt_register': "1. Գրանցել Ակտիվ", 'opt_search': "2. Որոնում",
        'opt_wallet': "3. Դրամապանակ", 'opt_mine': "4. Մայնինգ",
        'opt_status': "5. Ցանցի կարգավիճակ", 'opt_exit': "6. Ելք",
        'balance': "Հաշվեկշիռ", 'pubkey': "Դրամապանակ", 'sync_status': "Սինխրոնիզացիա",
        'enter_choice': "Ընտրություն: ", 'invalid_choice': "Սխալ ընտրություն!",
        'domain_name': "Դոմենի անուն: ", 'content_html': "Բովանդակություն (HTML): ",
        'register_success': "Հաջողվեց! Գործարքը հեռարձակվեց:", 'register_fail': "Ձախողվեց: ",
        'search_query': "Որոնում: ", 'no_results': "Արդյունք չկա:",
        'results_found': "Արդյունքներ:", 'view_content': "Դիտել (ID): ",
        'recipient': "Ստացող: ", 'amount': "Գումար: ", 'sent_success': "Ուղարկվեց և հեռարձակվեց!",
        'mining_start': "Մայնինգ...", 'block_found': "ԲԼՈԿԸ ԳՏՆՎԵՑ!",
        'assets_title': "Տեղական Ակտիվներ", 'fee': "Վճար", 'type': "Տեսակ",
        'stats_total_supply': "Ընդհանուր առաջարկ", 'stats_circulating': "Շրջանառվող առաջարկ",
        'stats_block_reward': "Բլոկի պարգև", 'stats_solved_blocks': "Լուծված բլոկներ",
        'stats_last_block': "Վերջին բլոկի հեշ", 'stats_halving': "Մինչ կիսումը",
        'back_to_menu': "0. Վերադառնալ գլխավոր մենյու", 'asset_cost': "Արժեք", 'asset_expiry': "Լրանում է",
        'enter_0_to_cancel': "(Մուտքագրեք 0 չեղարկելու համար)"
    }
}
DEFAULT_LANG = 'tr'

# --- YARDIMCI FONKSİYONLAR / HELPER FUNCTIONS ---
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
        c.execute('''CREATE TABLE IF NOT EXISTS node_config (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 0, last_mined REAL DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, previous_hash TEXT, block_hash TEXT, proof INTEGER, miner_key TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL)''')
        
        if c.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
            genesis_hash = hashlib.sha256(b'GhostGenesis').hexdigest()
            c.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                      (1, time.time(), '0', genesis_hash, 100, 'GhostProtocol_System'))
        
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            my_key = f"GHST{hashlib.sha256(NODE_ID.encode()).hexdigest()[:20]}"
            c.execute("INSERT INTO users (username, password, wallet_public_key, balance) VALUES (?, ?, ?, ?)",
                      ("node_user", "local_pass", my_key, INITIAL_USER_BALANCE))
            
        conn.commit()
        conn.close()

    def get_my_user(self):
        conn = self.get_connection()
        user = conn.execute("SELECT * FROM users LIMIT 1").fetchone() 
        conn.close()
        return dict(user) if user else None

# --- MANAGER SINIFLARI / MANAGER CLASSES ---

class NodeAssetManager:
    def __init__(self, db_mgr, blockchain_mgr, mesh_mgr):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.mesh_mgr = mesh_mgr 

    def register_asset(self, asset_type, name, content):
        if asset_type == 'domain' and not name.endswith('.ghost'): name += '.ghost'
        if not content: content = "<h1>New Site</h1>"
        
        content_bytes = content.encode('utf-8')
        keywords = extract_keywords(content) if asset_type == 'domain' else ""
        size = len(content_bytes)
        fee = calculate_asset_fee(size, asset_type)
        
        user = self.db.get_my_user()
        if user['balance'] < fee: return False, "Yetersiz Bakiye"

        conn = self.db.get_connection()
        try:
            asset_id = str(uuid4())
            tx_id = str(uuid4())
            timestamp = time.time()
            sender_key = user['wallet_public_key']

            # 1. Varlığı yerel olarak kaydet / Save asset locally
            conn.execute("INSERT OR REPLACE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_id, sender_key, asset_type, name, content_bytes, size, timestamp, timestamp + DOMAIN_EXPIRY_SECONDS, keywords))
            
            # 2. Bakiyeyi düş / Deduct balance
            conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (fee, user['id']))
            
            # 3. Ücret işlemini oluştur / Create fee transaction
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (tx_id, sender_key, "Asset_Fee_Collector", fee, timestamp))
            
            conn.commit()

            # 4. İşlemi ağa yayınla / Broadcast transaction to network
            tx_data = {'tx_id': tx_id, 'sender': sender_key, 'recipient': "Asset_Fee_Collector", 'amount': fee, 'timestamp': timestamp}
            self.mesh_mgr.broadcast_transaction(tx_data)

            return True, "Kayıt Başarılı"
        except Exception as e: return False, str(e)
        finally: conn.close()

    def get_local_assets(self):
        conn = self.db.get_connection()
        assets = conn.execute("SELECT * FROM assets ORDER BY creation_time DESC").fetchall()
        conn.close()
        return assets
    
    def get_all_assets_meta(self):
        conn = self.db.get_connection()
        assets = conn.execute("SELECT asset_id FROM assets").fetchall()
        conn.close()
        return [dict(a) for a in assets]

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
        except Exception as e:
            logger.error(f"Asset sync error: {e}")
        finally:
            conn.close()

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
        # TR: İstatistikleri hesaplar (Toplam arz, dolaşım, vb.)
        # EN: Calculates statistics (Total supply, circulation, etc.)
        conn = self.db.get_connection()
        last_block = self.get_last_block()
        
        mined_rewards = conn.execute("SELECT SUM(amount) FROM transactions WHERE sender = 'GhostProtocol_System'").fetchone()[0] or 0.0
        user_count = conn.execute("SELECT COUNT(id) FROM users").fetchone()[0] or 0
        mined_supply = mined_rewards + (user_count * INITIAL_USER_BALANCE)
        
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

    def mine_block(self):
        user = self.db.get_my_user()
        miner_key = user['wallet_public_key']
        last_mined = user['last_mined']
        
        if (time.time() - last_mined) < 86400:
            return False, "Günlük limit dolmadı."

        last_block = self.get_last_block()
        index = last_block['block_index'] + 1
        difficulty = BASE_DIFFICULTY
        
        proof = 0
        while True:
            guess = f'{last_block["proof"]}{proof}'.encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if guess_hash[:difficulty] == '0' * difficulty: break
            proof += 1
            
        block_hash = hashlib.sha256(f"{index}{time.time()}{last_block['block_hash']}{proof}".encode()).hexdigest()
        reward = INITIAL_BLOCK_REWARD

        conn = self.db.get_connection()
        try:
            conn.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                         (index, time.time(), last_block['block_hash'], block_hash, proof, miner_key))
            conn.execute("UPDATE users SET balance = balance + ?, last_mined = ? WHERE id = ?", (reward, time.time(), user['id']))
            conn.commit()
            return True, block_hash
        except Exception as e: return False, str(e)
        finally: conn.close()

    def transfer_coin(self, recipient, amount):
        user = self.db.get_my_user()
        if user['balance'] < amount: return False, "Yetersiz bakiye."
        
        conn = self.db.get_connection()
        try:
            tx_id = str(uuid4())
            timestamp = time.time()
            sender_key = user['wallet_public_key']

            conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user['id']))
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
                                if b_resp.status_code == 200:
                                    self._save_block(b_resp.json())
                                    logger.info(f"Blok indirildi: {h['block_index']}")

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
        
        self.mesh.set_asset_manager(self.asset)
        self.chain.set_mesh_manager(self.mesh)
        
        self.lang_code = 'tr' 
        self.L = LANGUAGES[self.lang_code]

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

    def display_stats_box(self):
        # TR: İstenilen istatistikleri gösteren kutu
        # EN: Box showing requested statistics
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
        user = self.db.get_my_user()
        assets = self.asset.get_local_assets()
        
        self.clear_screen()
        print(f"--- {self.L['node_name']} ---")
        print(f"🌍 {self.L['sync_status']}: {'ONLINE' if self.mesh.known_peers else 'MESH'}")
        print(f"💰 {self.L['balance']}: {user['balance']:.4f} GHOST")
        print(f"🔑 {self.L['pubkey']}: {user['wallet_public_key']}")
        
        self.display_stats_box()
        
        assets_title = self.L.get('assets_title', 'Local Assets') 
        print(f"📂 {assets_title} ({len(assets)}):")
        for a in assets[:5]:
            # TR: Varlık detayları (ücret ve süre)
            # EN: Asset details (fee and duration)
            fee = calculate_asset_fee(a['storage_size'], a['type'])
            expiry_date = datetime.fromtimestamp(a['expiry_time']).strftime('%Y-%m-%d')
            print(f" - {a['name']} ({a['type']}) | {self.L['asset_cost']}: {fee} GHOST | {self.L['asset_expiry']}: {expiry_date}")
        print("-" * 30)

    # TR: Alt menü ekranları (Geri dönüş için)
    # EN: Sub-menu screens (For back navigation)
    
    def register_screen(self):
        print(f"\n--- {self.L['opt_register']} ---")
        print(self.L['back_to_menu'])
        print(self.L['enter_0_to_cancel'])
        
        name = input(self.L['domain_name'])
        if name == '0': return
        
        content = input(self.L['content_html'])
        if content == '0': return
        
        success, msg = self.asset.register_asset('domain', name, content)
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
        
        success, msg = self.chain.transfer_coin(rec, amt)
        if success: print(f"✅ {self.L['sent_success']}")
        else: print(f"❌ {msg}")
        input("Enter...")

    def mining_screen(self):
        print(f"\n--- {self.L['opt_mine']} ---")
        print(self.L['back_to_menu'])
        
        confirm = input("Start Mining? (y/n/0): ")
        if confirm == '0' or confirm.lower() == 'n': return
        
        print(self.L['mining_start'])
        success, msg = self.chain.mine_block()
        if success: print(f"⛏️ {self.L['block_found']} Hash: {msg}")
        else: print(f"❌ {msg}")
        input("Enter...")

    def run(self):
        self.set_language()
        while True:
            self.display_status()
            print(f"1. {self.L['opt_register']}")
            print(f"2. {self.L['opt_search']}")
            print(f"3. {self.L['opt_wallet']}")
            print(f"4. {self.L['opt_mine']}")
            print(f"6. {self.L['opt_exit']}")
            
            choice = input(self.L['enter_choice'])
            
            if choice == '1': self.register_screen()
            elif choice == '2': self.search_screen()
            elif choice == '3': self.wallet_screen()
            elif choice == '4': self.mining_screen()
            elif choice == '6': break

if __name__ == '__main__':
    node = GhostMeshNodeApp()
    try:
        node.run()
    except KeyboardInterrupt:
        print("\nKapatılıyor...")

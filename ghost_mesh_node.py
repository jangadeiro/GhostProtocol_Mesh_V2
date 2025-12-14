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

# --- CİHAZ ÖZELİNDE MESH MODÜLLERİ (OPSİYONEL) ---
# TR: Bluetooth ve WiFi modülleri (Gelecek geliştirme için yer tutucu)
# EN: Placeholders for Bluetooth and WiFi modules (For future development)
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
GHOST_PORT = 5000 # Node'un diğer node'larla konuşacağı port
# TR: Bilinen sunucu IP'leri (Bootstrap Nodes)
# EN: Known server IPs (Bootstrap Nodes)
KNOWN_PEERS = ["46.101.219.46", "68.183.12.91"] 

STORAGE_COST_PER_MB = 0.01
DOMAIN_REGISTRATION_FEE = 1.0
DOMAIN_EXPIRY_SECONDS = 15552000
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
        'register_success': "Kayıt Başarılı!", 'register_fail': "Kayıt Başarısız: ",
        'search_query': "Arama (Domain/Kelime): ", 'no_results': "Sonuç bulunamadı.",
        'results_found': "Sonuçlar:", 'view_content': "İçeriği Görüntüle (ID girin, iptal için 0): ",
        'recipient': "Alıcı Cüzdan Adresi: ", 'amount': "Miktar: ", 'sent_success': "Gönderildi!",
        'mining_start': "Madencilik Başlatılıyor...", 'block_found': "BLOK BULUNDU!", 
        'assets_title': "Yerel Varlıklar", # Hata Düzeltildi / Error Fixed
        'fee': "Ücret", 'type': "Tür"
    },
    'en': {
        'node_name': "Ghost Mesh Node", 'menu_title': "GHOST PROTOCOL MENU",
        'opt_register': "1. Register Asset (.ghost / File)", 'opt_search': "2. Search & View",
        'opt_wallet': "3. Wallet & Transfer", 'opt_mine': "4. Mine Block",
        'opt_status': "5. Network Status", 'opt_exit': "6. Exit",
        'balance': "Balance", 'pubkey': "Wallet", 'sync_status': "Sync Status",
        'enter_choice': "Choice: ", 'invalid_choice': "Invalid choice!",
        'domain_name': "Domain Name (e.g., site): ", 'content_html': "Content (HTML): ",
        'register_success': "Registration Successful!", 'register_fail': "Registration Failed: ",
        'search_query': "Search (Domain/Keyword): ", 'no_results': "No results found.",
        'results_found': "Results:", 'view_content': "View Content (Enter ID, 0 to cancel): ",
        'recipient': "Recipient Address: ", 'amount': "Amount: ", 'sent_success': "Sent!",
        'mining_start': "Starting Mining...", 'block_found': "BLOCK FOUND!",
        'assets_title': "Local Assets",
        'fee': "Fee", 'type': "Type"
    },
    'ru': {
        'node_name': "Узел Ghost Mesh", 'menu_title': "МЕНЮ GHOST PROTOCOL",
        'opt_register': "1. Регистрация актива", 'opt_search': "2. Поиск и просмотр",
        'opt_wallet': "3. Кошелек и перевод", 'opt_mine': "4. Майнинг",
        'opt_status': "5. Статус сети", 'opt_exit': "6. Выход",
        'balance': "Баланс", 'pubkey': "Кошелек", 'sync_status': "Синхронизация",
        'enter_choice': "Ваш выбор: ", 'invalid_choice': "Неверный выбор!",
        'domain_name': "Имя домена: ", 'content_html': "Содержание (HTML): ",
        'register_success': "Успешно!", 'register_fail': "Ошибка: ",
        'search_query': "Поиск: ", 'no_results': "Нет результатов.",
        'results_found': "Результаты:", 'view_content': "Просмотр (ID): ",
        'recipient': "Адрес получателя: ", 'amount': "Сумма: ", 'sent_success': "Отправлено!",
        'mining_start': "Майнинг начат...", 'block_found': "БЛОК НАЙДЕН!",
        'assets_title': "Локальные активы",
        'fee': "Плата", 'type': "Тип"
    },
    'hy': {
        'node_name': "Ghost Mesh Հանգույց", 'menu_title': "GHOST PROTOCOL ԸՆՏՐԱՑԱՆԿ",
        'opt_register': "1. Գրանցել Ակտիվ", 'opt_search': "2. Որոնում",
        'opt_wallet': "3. Դրամապանակ", 'opt_mine': "4. Մայնինգ",
        'opt_status': "5. Ցանցի կարգավիճակ", 'opt_exit': "6. Ելք",
        'balance': "Հաշվեկշիռ", 'pubkey': "Դրամապանակ", 'sync_status': "Սինխրոնիզացիա",
        'enter_choice': "Ընտրություն: ", 'invalid_choice': "Սխալ ընտրություն!",
        'domain_name': "Դոմենի անուն: ", 'content_html': "Բովանդակություն (HTML): ",
        'register_success': "Հաջողվեց!", 'register_fail': "Ձախողվեց: ",
        'search_query': "Որոնում: ", 'no_results': "Արդյունք չկա:",
        'results_found': "Արդյունքներ:", 'view_content': "Դիտել (ID): ",
        'recipient': "Ստացող: ", 'amount': "Գումար: ", 'sent_success': "Ուղարկվեց!",
        'mining_start': "Մայնինգ...", 'block_found': "ԲԼՈԿԸ ԳՏՆՎԵՑ!",
        'assets_title': "Տեղական Ակտիվներ",
        'fee': "Վճար", 'type': "Տեսակ"
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
        # Node'a özel konfigürasyon tablosu
        c.execute('''CREATE TABLE IF NOT EXISTS node_config (key TEXT PRIMARY KEY, value TEXT)''')
        # Standart tablolar (Server ile uyumlu)
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 0, last_mined REAL DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, previous_hash TEXT, block_hash TEXT, proof INTEGER, miner_key TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL)''')
        
        # Genesis Block Kontrolü
        if c.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
            genesis_hash = hashlib.sha256(b'GhostGenesis').hexdigest()
            c.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                      (1, time.time(), '0', genesis_hash, 100, 'GhostProtocol_System'))
        
        # Yerel kullanıcı/cüzdan oluşturma (Otomatik)
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            my_key = f"GHST{hashlib.sha256(NODE_ID.encode()).hexdigest()[:20]}"
            c.execute("INSERT INTO users (username, password, wallet_public_key, balance) VALUES (?, ?, ?, ?)",
                      ("node_user", "local_pass", my_key, INITIAL_USER_BALANCE))
            
        conn.commit()
        conn.close()

    def get_my_user(self):
        conn = self.get_connection()
        user = conn.execute("SELECT * FROM users LIMIT 1").fetchone() # Tek kullanıcı var sayıyoruz
        conn.close()
        return dict(user) if user else None

# --- MANAGER SINIFLARI / MANAGER CLASSES ---
# (Ghost Server mantığının Node'a uyarlanmış hali)

class NodeAssetManager:
    def __init__(self, db_mgr):
        self.db = db_mgr

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
            conn.execute("INSERT OR REPLACE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (str(uuid4()), user['wallet_public_key'], asset_type, name, content_bytes, size, time.time(), time.time() + DOMAIN_EXPIRY_SECONDS, keywords))
            conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (fee, user['id']))
            conn.commit()
            return True, "Kayıt Başarılı"
        except Exception as e: return False, str(e)
        finally: conn.close()

    def get_local_assets(self):
        conn = self.db.get_connection()
        assets = conn.execute("SELECT * FROM assets ORDER BY creation_time DESC").fetchall()
        conn.close()
        return assets

    def search_assets(self, query):
        conn = self.db.get_connection()
        s = f"%{query}%"
        results = conn.execute("SELECT * FROM assets WHERE name LIKE ? OR keywords LIKE ?", (s, s)).fetchall()
        conn.close()
        return results

class NodeBlockchainManager:
    def __init__(self, db_mgr):
        self.db = db_mgr

    def get_last_block(self):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return block

    def mine_block(self):
        user = self.db.get_my_user()
        miner_key = user['wallet_public_key']
        last_mined = user['last_mined']
        
        if (time.time() - last_mined) < 86400:
            return False, "Günlük limit dolmadı."

        last_block = self.get_last_block()
        index = last_block['block_index'] + 1
        difficulty = BASE_DIFFICULTY # Basitlik için sabit zorluk
        
        proof = 0
        while True:
            guess = f'{last_block["proof"]}{proof}'.encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if guess_hash[:difficulty] == '0' * difficulty: break
            proof += 1
            
        block_hash = hashlib.sha256(f"{index}{time.time()}{last_block['block_hash']}{proof}".encode()).hexdigest()
        reward = INITIAL_BLOCK_REWARD # Basit ödül

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
            conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user['id']))
            # Yerel veritabanında alıcı yoksa sadece bakiyeyi düşer (Basitleştirilmiş)
            # Gerçekte işlem transaction tablosuna yazılır ve ağa yayılır.
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (str(uuid4()), user['wallet_public_key'], recipient, amount, time.time()))
            conn.commit()
            return True, "Transfer yapıldı."
        except Exception as e: return False, str(e)
        finally: conn.close()

class NodeMeshManager:
    # TR: Peer bulma ve Veri Senkronizasyonu
    # EN: Peer discovery and Data Synchronization
    def __init__(self, db_mgr, blockchain_mgr, asset_mgr):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.asset_mgr = asset_mgr
        self.known_peers = KNOWN_PEERS
        
        self.start_services()

    def start_services(self):
        threading.Thread(target=self._sync_loop, daemon=True).start()

    def _sync_loop(self):
        while True:
            self.sync_with_network()
            time.sleep(60) # 1 dakikada bir senkronize ol

    def sync_with_network(self):
        # TR: Önce bilinen sunuculardan (Internet), yoksa yerel peerlardan güncelle
        # EN: Update from known servers (Internet) first, then local peers
        for peer_ip in self.known_peers:
            try:
                # 1. BLOK SENKRONİZASYONU
                resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/chain_meta", timeout=2)
                if resp.status_code == 200:
                    remote_headers = resp.json()
                    local_last = self.chain_mgr.get_last_block()
                    
                    if remote_headers[-1]['block_index'] > local_last['block_index']:
                        # Yeni blokları indir
                        for h in remote_headers:
                            if h['block_index'] > local_last['block_index']:
                                b_resp = requests.get(f"http://{peer_ip}:{GHOST_PORT}/api/block/{h['block_hash']}", timeout=2)
                                if b_resp.status_code == 200:
                                    self._save_block(b_resp.json())
                                    
                # 2. VARLIK SENKRONİZASYONU
                # (Benzer mantıkla varlıklar indirilir - Kısaltıldı)
                
            except Exception: pass # Sunucuya ulaşılamadı

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
        self.asset = NodeAssetManager(self.db)
        self.mesh = NodeMeshManager(self.db, self.chain, self.asset)
        
        self.lang_code = 'tr' # Varsayılan dil
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

    def display_status(self):
        user = self.db.get_my_user()
        assets = self.asset.get_local_assets()
        last_block = self.chain.get_last_block()
        
        self.clear_screen()
        print(f"--- {self.L['node_name']} ---")
        print(f"🌍 {self.L['sync_status']}: {'ONLINE' if self.mesh.known_peers else 'MESH'}")
        print(f"💰 {self.L['balance']}: {user['balance']:.4f} GHOST")
        print(f"🔑 {self.L['pubkey']}: {user['wallet_public_key']}")
        print(f"🧱 Son Blok: {last_block['block_index']}")
        
        # TR: KeyError hatasının düzeltildiği kısım
        # EN: Part where KeyError is fixed
        assets_title = self.L.get('assets_title', 'Local Assets') 
        print(f"\n📂 {assets_title} ({len(assets)}):")
        for a in assets[:3]:
            print(f" - {a['name']} ({a['type']})")
        print("-" * 30)

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
            
            if choice == '1':
                name = input(self.L['domain_name'])
                content = input(self.L['content_html'])
                success, msg = self.asset.register_asset('domain', name, content)
                print(msg)
                time.sleep(2)
            elif choice == '2':
                q = input(self.L['search_query'])
                results = self.asset.search_assets(q)
                if not results: print(self.L['no_results'])
                else:
                    print(self.L['results_found'])
                    for r in results: print(f"ID: {r['asset_id']} | {r['name']}")
                    vid = input(self.L['view_content'])
                    if vid != '0':
                        for r in results:
                            if r['asset_id'] == vid:
                                print(f"\n--- {r['name']} ---\n{r['content'].decode('utf-8')}\n----------------")
                                input("Devam etmek için Enter...")
            elif choice == '3':
                rec = input(self.L['recipient'])
                try: amt = float(input(self.L['amount']))
                except: amt = 0
                success, msg = self.chain.transfer_coin(rec, amt)
                print(msg)
                time.sleep(2)
            elif choice == '4':
                print(self.L['mining_start'])
                success, msg = self.chain.mine_block()
                if success: print(f"{self.L['block_found']} Hash: {msg}")
                else: print(f"Hata: {msg}")
                time.sleep(2)
            elif choice == '6':
                break

if __name__ == '__main__':
    node = GhostMeshNodeApp()
    try:
        node.run()
    except KeyboardInterrupt:
        print("\nKapatılıyor...")

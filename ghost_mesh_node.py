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
from uuid import uuid4
from datetime import timedelta
import socket
from markupsafe import Markup 
from typing import Optional, Tuple, Dict, Any, List

# --- CİHAZ ÖZELİNDE MESH/AĞ MODÜLLERİ (Mobil/Gömülü Cihazlar İçin) ---
# TR: Bluetooth ve WiFi modülleri için yer tutucular. 
# EN: Placeholders for Bluetooth and WiFi modules.
# TR: Gerçek uygulamada bu kısımlar pybluez, Bleak veya yerel WiFi API'leri ile değiştirilecektir.
# EN: In a real application, these parts would be replaced with pybluez, Bleak, or local WiFi APIs.
try:
    import bluetooth # Örn. pybluez
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False
    
try:
    # WiFi modülü yerine IP/Socket modülü kullanacağız.
    # Bu, temel IP iletişimini simüle eder.
    WIFI_AVAILABLE = True 
except Exception:
    WIFI_AVAILABLE = False

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GhostNode - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostMeshNode")

# --- YAPILANDIRMA / CONFIGURATION (Sunucu ile Eşleşmeli) ---
NODE_ID = hashlib.sha256(socket.gethostname().encode()).hexdigest()[:10]
DB_FILE = os.path.join(os.getcwd(), f"ghost_node_{NODE_ID}.db") 
GHOST_SERVER_URL = "http://127.0.0.1:5000"  # TR: Merkezi Sunucu Adresi

# TR: Varlık Ücretleri (ghost_server.py ile Eşleşmeli)
# EN: Asset Fees (Must match ghost_server.py)
STORAGE_COST_PER_MB = 0.01       # TR: Veri barındırma ücreti: MB başı 0.01 GHOST
DOMAIN_REGISTRATION_FEE = 1.0    # TR: 6 Aylık Domain Tescil Ücreti: 1.0 GHOST
DOMAIN_EXPIRY_SECONDS = 15552000  # 6 Ay / 6 Months

# --- ÇOKLU DİL SÖZLÜĞÜ (Sunucu ile Eşleşmeli) ---
LANGUAGES = {
    'tr': {
        'node_name': "Ghost Node", 'search': "Arama", 'register': "Kaydet", 'wallet': "Cüzdan",
        'domain_title': f"💾 .ghost Kayıt (Ücret: {DOMAIN_REGISTRATION_FEE} GHOST / 6 Ay)",
        'media_title': f"🖼️ Varlık Yükle (Barındırma Ücreti: {STORAGE_COST_PER_MB} GHOST / MB)",
        'status_online': "ONLINE", 'status_offline': "OFFLINE", 'status_mesh_active': "Mesh Aktif",
        'asset_fee': "Ücret", 'asset_expires': "Süre Sonu", 'asset_type': "Tip",
        'no_pubkey': "Lütfen cüzdan genel anahtarınızı ayarlayın.",
        'balance': "Bakiye", 'not_enough_balance': "Yetersiz bakiye."
    },
    'en': {
        'node_name': "Ghost Node", 'search': "Search", 'register': "Register", 'wallet': "Wallet",
        'domain_title': f"💾 .ghost Registration (Fee: {DOMAIN_REGISTRATION_FEE} GHOST / 6 Months)",
        'media_title': f"🖼️ Upload Asset (Storage Fee: {STORAGE_COST_PER_MB} GHOST / MB)",
        'status_online': "ONLINE", 'status_offline': "OFFLINE", 'status_mesh_active': "Mesh Active",
        'asset_fee': "Fee", 'asset_expires': "Expires", 'asset_type': "Type",
        'no_pubkey': "Please set your wallet public key.",
        'balance': "Balance", 'not_enough_balance': "Insufficient balance."
    },
    # Diğer diller kısaltıldı
}
DEFAULT_LANG = 'tr'

# --- YARDIMCI FONKSİYONLAR (Sunucu ile Eşleşmeli) ---

def extract_keywords(content_str):
    """
    TR: HTML etiketlerini temizler ve metinden anahtar kelimeleri ayıklar.
    EN: Cleans HTML tags and extracts keywords from the text.
    """
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

def calculate_asset_fee(size_bytes: int, asset_type: str) -> float:
    """
    TR: Varlık tipine göre doğru ücreti (GHOST cinsinden) hesaplar.
    EN: Calculates the correct fee (in GHOST) based on asset type.
    """
    if asset_type == 'domain':
        # TR: Domain tescilinde boyuttan bağımsız sabit ücret.
        # EN: Fixed fee for domain registration, regardless of size.
        return DOMAIN_REGISTRATION_FEE
    else:
        # TR: Diğer varlıklar için boyuta bağlı depolama ücreti (MB başına 0.01 GHOST).
        # EN: Size-dependent storage fee for other assets (0.01 GHOST per MB).
        return round((size_bytes / (1024 * 1024)) * STORAGE_COST_PER_MB, 4)

# --- VERİTABANI YÖNETİCİSİ / DATABASE MANAGER ---
class DatabaseManager:
    # TR: SQLite veritabanı işlemlerini yönetir.
    # EN: Manages SQLite database operations.
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
        
        # TR: Kullanıcı bilgileri (Cüzdan/Bakiye)
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_config (key TEXT PRIMARY KEY, value TEXT)''')
        # TR: Düğümde kayıtlı varlıklar (Yerel Barındırma)
        cursor.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        
        # TR: Varsayılan Bakiye ve Anahtar Kontrolü
        cursor.execute("INSERT OR IGNORE INTO user_config (key, value) VALUES (?, ?)", ('balance', '50.0'))
        cursor.execute("INSERT OR IGNORE INTO user_config (key, value) VALUES (?, ?)", ('pub_key', NODE_ID + '_KEY'))
        
        conn.commit()
        conn.close()

    def get_config(self, key):
        conn = self.get_connection()
        result = conn.execute("SELECT value FROM user_config WHERE key = ?", (key,)).fetchone()
        conn.close()
        return result['value'] if result else None

    def set_config(self, key, value):
        conn = self.get_connection()
        conn.execute("INSERT OR REPLACE INTO user_config (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    
    def get_assets(self):
        conn = self.get_connection()
        assets = conn.execute("SELECT * FROM assets ORDER BY creation_time DESC").fetchall()
        conn.close()
        return assets

# --- MESH AĞI İLETİŞİM YÖNETİCİSİ / MESH NETWORK COMMS MANAGER ---
class MeshCommsManager:
    def __init__(self, db_manager: DatabaseManager, server_url: str):
        self.db = db_manager
        self.server_url = server_url
        self.node_ip = self._get_local_ip()

    def _get_local_ip(self) -> str:
        # TR: Yerel IP adresini bulmaya çalışır.
        # EN: Tries to find the local IP address.
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def send_to_server(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # TR: Merkezi sunucuya veri gönderir (IP/HTTP)
        # EN: Sends data to the central server (IP/HTTP)
        url = f"{self.server_url}{endpoint}"
        try:
            response = requests.post(url, json=data, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Server communication failed ({url}): {e}")
            return None

    def announce_presence(self):
        # TR: Merkezi sunucuya varlığını bildirir (Mesh Peer Update)
        # EN: Announces presence to the central server (Mesh Peer Update)
        data = {'ip_address': self.node_ip, 'node_id': NODE_ID}
        self.send_to_server('/peer_update', data)
        logger.info(f"Node presence announced to server ({self.node_ip}).")
        
    # --- MESH (BT/WiFi) YEREL KEŞİF YER TUTUCULARI ---

    def discover_local_peers(self):
        # TR: Bluetooth ve WiFi üzerinden çevredeki cihazları keşfetme mantığı.
        # EN: Logic to discover nearby devices via Bluetooth and WiFi.
        # Bu kısım, gerçek donanım API'leri olmadan sadece loglama yapar.
        if BLUETOOTH_AVAILABLE:
            logger.info("Bluetooth discovery initiated...")
            # bluetooth.discover_devices() gibi fonksiyonlar çağrılır.
        else:
            logger.warning("Bluetooth module not found. Skipping BT discovery.")
        
        if WIFI_AVAILABLE:
            logger.info("WiFi/IP scan initiated...")
            # Yerel ağdaki diğer Ghost Node IP'leri aranır.
        else:
            logger.warning("WiFi/IP module not available.")

# --- ASSET MANAGER (Yerel Cihaz İçin) ---
class NodeAssetManager:
    def __init__(self, db_manager: DatabaseManager, comms_manager: MeshCommsManager):
        self.db = db_manager
        self.comms = comms_manager

    def register_asset(self, asset_type: str, name: str, content: str | bytes, is_file: bool = False) -> Tuple[bool, str]:
        """
        TR: Varlığı yerel olarak kaydeder ve ücreti bakiyeden düşer.
        EN: Registers the asset locally and deducts the fee from the balance.
        """
        pub_key = self.db.get_config('pub_key')
        if not pub_key:
            return False, "Pubkey not set."

        if isinstance(content, str) and not is_file:
            content_bytes = content.encode('utf-8')
            keywords = extract_keywords(content) if asset_type == 'domain' else ""
        elif is_file:
            # Dosya okuma simülasyonu (content'in dosya nesnesi olduğu varsayılır)
            try:
                content.seek(0)
                content_bytes = content.read()
            except AttributeError:
                 return False, "Invalid file object."
            keywords = ""
        else:
            content_bytes = content
            keywords = ""

        size = len(content_bytes)
        fee = calculate_asset_fee(size, asset_type)
        
        current_balance_str = self.db.get_config('balance')
        current_balance = float(current_balance_str) if current_balance_str else 0.0

        if current_balance < fee:
            L = LANGUAGES.get(DEFAULT_LANG) # Hata mesajı için dil
            return False, f"{L['not_enough_balance']} ({fee:.4f} GHOST gerekli, bakiye: {current_balance:.4f} GHOST)"
        
        asset_id = str(uuid4())
        
        conn = self.db.get_connection()
        try:
            # 1. Yerel veritabanına kaydet
            conn.execute("INSERT INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_id, pub_key, asset_type, name, content_bytes, size, time.time(), time.time() + DOMAIN_EXPIRY_SECONDS, keywords))
            
            # 2. Bakiyeyi güncelle
            new_balance = current_balance - fee
            self.db.set_config('balance', new_balance)
            
            # 3. Merkezi Sunucuya Bildirim (Opsiyonel)
            # TR: Bu kısım, merkezi sunucuya yeni varlığın kaydedildiğini bildirir.
            # EN: This part notifies the central server that a new asset has been registered.
            self.comms.send_to_server('/api/register_asset_from_node', {
                'asset_id': asset_id,
                'owner_pub_key': pub_key,
                'type': asset_type,
                'name': name,
                'fee': fee,
                'node_id': NODE_ID
            })
            
            conn.commit()
            conn.close()
            return True, f"Varlık Başarıyla Kaydedildi. Ödenen Ücret: {fee:.4f} GHOST. Yeni Bakiye: {new_balance:.4f} GHOST"
        except Exception as e:
            logger.error(f"Yerel varlık kaydı başarısız: {e}")
            conn.close()
            return False, str(e)
            
# --- TEMEL NODE SİSTEMİ ---
class GhostMeshNode:
    def __init__(self, lang_code=DEFAULT_LANG):
        self.db = DatabaseManager(DB_FILE)
        self.comms = MeshCommsManager(self.db, GHOST_SERVER_URL)
        self.asset_mgr = NodeAssetManager(self.db, self.comms)
        self.lang = LANGUAGES.get(lang_code, LANGUAGES[DEFAULT_LANG])

    def run_simulation(self):
        # TR: Basit arayüz simülasyonu
        # EN: Simple interface simulation
        logger.info(f"--- GhostProtocol Mesh Node ({self.lang['node_name']}) başlatıldı ---")
        self.comms.announce_presence()
        self.comms.discover_local_peers()
        
        while True:
            self.display_status()
            choice = input(f"\n[{self.lang['node_name']}]: 1-{self.lang['register']}, 2-{self.lang['search']}, 3-{self.lang['wallet']}, 4-Exit: ")
            
            if choice == '1':
                self.handle_registration()
            elif choice == '2':
                self.handle_search()
            elif choice == '3':
                self.handle_wallet()
            elif choice == '4':
                logger.info("Node kapatılıyor...")
                break
            else:
                print("Geçersiz seçim.")

    def display_status(self):
        pub_key = self.db.get_config('pub_key')
        balance = self.db.get_config('balance')
        assets = self.db.get_assets()
        
        status = self.lang['status_online'] if self.comms.send_to_server('/api/status', {}) else self.lang['status_offline']
        mesh_status = self.lang['status_mesh_active'] if (BLUETOOTH_AVAILABLE or WIFI_AVAILABLE) else self.lang['status_offline']

        print("\n--- NODE STATUS ---")
        print(f"ID: {NODE_ID} | IP: {self.comms.node_ip}")
        print(f"Server Status: {status} | Mesh Status: {mesh_status}")
        print(f"Key: {pub_key} | {self.lang['balance']}: {float(balance):.4f} GHOST")
        print(f"Yerel Varlıklar ({len(assets)}):")
        
        # Yerel varlık listesi
        for a in assets[:5]:
            fee = calculate_asset_fee(a['storage_size'], a['type'])
            print(f" - [{a['type'].upper()}] {a['name']} ({fee:.4f} GHOST Fee)")

    def handle_registration(self):
        print("\n--- VARLIK KAYIT ---")
        asset_type_choice = input("Varlık Tipi (1-Domain, 2-Media): ")
        
        if asset_type_choice == '1':
            # Domain Kayıt
            name = input("Domain Adı (alanadi.ghost): ")
            content = input("HTML İçeriği: ")
            success, message = self.asset_mgr.register_asset('domain', name, content)
            print(f"Sonuç: {'BAŞARILI' if success else 'HATA'}: {message}")
            
        elif asset_type_choice == '2':
            # Medya/Dosya Kayıt (Basitleştirilmiş simülasyon)
            file_name = input("Dosya Adı (ornek.png): ")
            size_mb = float(input("Boyut (MB): "))
            
            # TR: Simülasyon için rastgele veri oluştur
            # EN: Create random data for simulation
            size_bytes = int(size_mb * 1024 * 1024)
            # Dummy content (Gerçekte dosya okunur)
            dummy_content = os.urandom(size_bytes)
            
            success, message = self.asset_mgr.register_asset('file', file_name, dummy_content)
            print(f"Sonuç: {'BAŞARILI' if success else 'HATA'}: {message}")
        else:
            print("Geçersiz Varlık Tipi.")
            
    def handle_search(self):
        # TR: Arama, yerel varlıklar ve merkezi sunucu üzerinden yapılır.
        # EN: Search is performed across local assets and the central server.
        query = input("\nAranacak Kelime veya Domain: ")
        
        # 1. Yerel Arama
        local_results = [a for a in self.db.get_assets() if query.lower() in a['name'].lower() or (a['keywords'] and query.lower() in a['keywords'].lower())]
        print(f"\n--- YEREL SONUÇLAR ({len(local_results)}) ---")
        for r in local_results:
             print(f" - {r['name']} ({r['type'].upper()}): ID {r['asset_id'][:8]}...")
             
        # 2. Merkezi Sunucu Arama (Basit API Çağrısı Simülasyonu)
        server_response = self.comms.send_to_server('/api/search', {'query': query})
        
        if server_response and 'results' in server_response:
             print(f"\n--- MERKEZİ SUNUCU SONUÇLARI ({len(server_response['results'])}) ---")
             for r in server_response['results']:
                 print(f" - {r['name']} (Type: {r['type']})")
        else:
             print("\n--- MERKEZİ SUNUCU SONUÇLARI: Sunucuya ulaşılamadı veya sonuç yok. ---")

    def handle_wallet(self):
        pub_key = self.db.get_config('pub_key')
        balance = self.db.get_config('balance')
        print(f"\n--- CÜZDAN BİLGİLERİ ---")
        print(f"Genel Anahtar: {pub_key}")
        print(f"Bakiye: {float(balance):.4f} GHOST")

# --- START ---
if __name__ == '__main__':
    # TR: Simülasyon için kullanıcıdan dil seçimi alınabilir.
    node = GhostMeshNode()
    
    try:
        # TR: Gömülü cihaz veya CLI ortamı simülasyonu
        node.run_simulation()
    except KeyboardInterrupt:
        logger.info("Node kapatılıyor...")
    except Exception as e:
        logger.error(f"Beklenmedik bir hata oluştu: {e}")

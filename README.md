👻 GhostProtocol
The Decentralized, Off-Grid Internet & Blockchain Layer (Merkeziyetsiz, Şebekeden Bağımsız İnternet ve Blok Zinciri Katmanı)

🇬🇧 English
Overview
GhostProtocol is a Proof-of-Work (PoW) blockchain designed to function even without an internet connection. It enables a decentralized web (.ghost domains) and acts as a mesh network for data transmission using Wi-Fi UDP Broadcast and Bluetooth RFCOMM.

Key Features
Off-Grid Mesh Network: Sync blocks and data via Bluetooth or Local Wi-Fi when the internet is down.

Decentralized Hosting: Host uncensorable websites (.ghost) directly on the chain.

Storage Rent Model: "Pay-to-Stay" economy for storing images, videos, and audio.

Identity Management: Optional KYC and profile verification system.

Scrypt Mining: ASIC-resistant mining algorithm.

Installation & Usage
1. Local Development (Manual)
Prerequisites: Python 3.9+, libbluetooth-dev (for Linux).

Bash

# Clone the repository
git clone https://github.com/jangadeiro/GhostProtocol_Mesh_V5.git
cd ghostprotocol

# Install dependencies
pip install -r requirements.txt

# Run the node
python ghost_mesh_node.py
Access the dashboard at: http://localhost:5000

2. Deployment with Docker (Recommended)
This is the easiest way to run a node on a server or local machine.

Bash

# Build and Run
docker-compose up -d --build
Server Deployment (Production)
To deploy GhostProtocol on a cloud server (AWS, DigitalOcean, etc.) :

Prepare Server: Install Docker and Docker Compose.

Upload Files: Copy ghost_mesh_node.py, Dockerfile, requirements.txt, and docker-compose.yml to the server.

Launch: Run docker-compose up -d.

Firewall: Ensure ports 5000 (TCP) and 9999 (UDP) are open.

🇹🇷 Türkçe Proje Özeti

GhostProtocol, internet bağlantısı olmasa dahi çalışabilmek üzere tasarlanmış, Proof-of-Work (PoW) tabanlı bir blok zinciridir. Merkeziyetsiz web sitelerine (.ghost alan adları) ev sahipliği yapar ve Wi-Fi UDP Yayını ile Bluetooth RFCOMM kullanarak verileri cihazdan cihaza taşıyan bir örgü ağı (mesh network) oluşturur.

Temel Özellikler
Off-Grid Mesh Ağı: İnternet kesildiğinde Bluetooth veya Yerel Wi-Fi üzerinden blok ve veri senkronizasyonu.

Merkeziyetsiz Barındırma: Sansürlenemez web sitelerini (.ghost) doğrudan zincir üzerinde barındırın.

Depolama Kira Modeli: Resim, video ve ses dosyaları için "Kaldıkça-Öde" (Pay-to-Stay) ekonomisi.

Kimlik Yönetimi: İsteğe bağlı KYC ve profil doğrulama sistemi.

Scrypt Madenciliği: ASIC dirençli madencilik algoritması.

Kurulum ve Kullanım
1. Yerel Geliştirme (Manuel)
Gereksinimler: Python 3.9+, libbluetooth-dev (Linux için).

Bash

# Depoyu klonlayın
git clone https://github.com/jangadeiro/GhostProtocol_Mesh_V5.git
cd ghostprotocol

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Node'u çalıştırın
python ghost_mesh_node.py
Panele erişim: http://localhost:5000

2. Docker ile Kurulum (Önerilen)
Sunucuda veya yerel makinede bir node çalıştırmanın en kolay yoludur.

Bash

# İnşa et ve Başlat
docker-compose up -d --build
Sunucuya Yükleme (Canlı Ortam)
GhostProtocol'ü bir bulut sunucuya (AWS, DigitalOcean vb.) kurmak için:

Sunucuyu Hazırlayın: Docker ve Docker Compose'u kurun.

Dosyaları Yükleyin: ghost_mesh_node.py, Dockerfile, requirements.txt ve docker-compose.yml dosyalarını sunucuya kopyalayın.

Başlatın: docker-compose up -d komutunu çalıştırın.

Güvenlik Duvarı: 5000 (TCP) ve 9999 (UDP) portlarının açık olduğundan emin olun.

Disclaimer / Yasal Uyarı
GhostProtocol is an experimental software. Use at your own risk. (GhostProtocol deneysel bir yazılımdır. Kullanım riski size aittir.)

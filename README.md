# 👻 GhostProtocol

**The Decentralized, Off-Grid Internet & Blockchain Layer**
*(Merkeziyetsiz, Şebekeden Bağımsız İnternet ve Blok Zinciri Katmanı)*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/Status-Beta-orange.svg)]()

---

## 🌍 Language Selection / Dil Seçimi

- [🇬🇧 **English**](#-english)
- [🇹🇷 **Türkçe**](#-turkish)

---

<a name="-english">
## 🇬🇧 English</a>

### Overview
GhostProtocol is a Proof-of-Work (PoW) blockchain designed to function as a survivalist communication network. It enables a decentralized web (`.ghost` domains) and acts as a hybrid mesh network. It operates seamlessly whether connected to the high-speed internet (Cloud Mode) or completely offline using local connections (Mesh Mode).

### 🌟 Key Features

#### 1. Hybrid Synchronization (Cloud + Mesh)
* **Online Mode:** When an internet connection is detected, Mesh Nodes automatically pull the latest blocks and assets from the central **Cloud Server**.
* **Offline Mode:** In the absence of internet, nodes communicate with nearby devices via **Wi-Fi/UDP Broadcast** and **Bluetooth** to exchange blocks and transactions.

#### 2. Smart Domain Management (`.ghost`)
* **Lease Cycle:** Registered domains are valid for **6 months**.
* **Auto-Release:** If not renewed, the domain expires and becomes available for others.
* **Content Persistence:** Even if a domain expires, the content (HTML/XML) remains on the chain as a generic asset but is no longer accessible via the domain name.

#### 3. Content Forking & Ownership
* **Forking:** Users can "Clone" any content (images, videos, sites) they see on the network. This creates a new, independent copy owned by the cloner.
* **Redundancy:** If the original uploader deletes their asset or stops paying rent, the cloned versions remain live as long as their new owners pay the storage fee.

#### 4. Fair Economy (Storage Rent)
* **Pay-to-Stay:** To prevent blockchain bloat, users pay a storage fee based on file size.
* **Cost:** `0.001 GHOST` per MB / Month.
* **Transparency:** Costs and remaining time are visible on the Dashboard.

### 🚀 Installation

**Prerequisites:** Python 3.9+

# 1. Clone the repository
git clone [https://github.com/jangadeiro/GhostProtocol_Mesh_V2.git](https://github.com/jangadeiro/GhostProtocol_Mesh_V2.git)
cd ghostprotocol

# 2. Install dependencies
pip install flask requests cryptography

💻 Usage
GhostProtocol consists of two main components. Choose the one that fits your role.

A. Run as a Mesh Node (Client/Field Device)
For laptops, Raspberry Pis, or personal computers. It connects to the Cloud when online and peers when offline.

Bash
python ghost_mesh_node.py
Access: http://localhost:5001

Features: Wallet, Mining, Content Browsing, Offline Sync.

B. Run as a Cloud Server (Mainnet Backbone)
For VPS (DigitalOcean, AWS, etc.). Acts as the primary data repository.

Bash
python ghost_server.py
Access: http://YOUR_SERVER_IP:5000

Features: High-availability block storage, centralized sync point.

<a name="-turkish">
🇹🇷 Türkçe</a>

Proje Özeti
GhostProtocol, internet bağlantısı olmasa dahi çalışabilmek üzere tasarlanmış, Proof-of-Work (PoW) tabanlı bir blok zinciridir. Merkeziyetsiz web sitelerine (.ghost alan adları) ev sahipliği yapar. İnternet varken bulut sunucularla, yokken ise yerel cihazlarla haberleşen hibrit bir yapıya sahiptir.

🌟 Temel Özellikler
1. Hibrit Senkronizasyon (Bulut + Mesh)
Çevrimiçi Mod: Cihaz internet bulduğunda, blok verilerini otomatik olarak Bulut Sunucu'dan çeker ve kendini günceller.

Çevrimdışı Mod: İnternet kesildiğinde, cihazlar Wi-Fi/UDP Yayını ve Bluetooth kullanarak yakın çevredeki diğer Ghost cihazlarıyla veri alışverişi yapar.

2. Akıllı Domain Yönetimi (.ghost)
Kiralama Döngüsü: Tescil edilen her domain 6 ay boyunca kullanıcıya aittir.

Otomatik Boşa Çıkma: Süre sonunda yenilenmezse domain boşa çıkar ve başkası alabilir.

İçerik Kalıcılığı: Domain süresi dolsa bile, yüklenen içerik (HTML/Video vb.) zincirden silinmez, sahibinin varlıklarında "Pasif" olarak kalır.

3. İçerik Çatallanması (Forking)
Klonlama: Kullanıcılar ağdaki herhangi bir içeriği (örneğin viral bir video) "Kopyalayabilir". Bu işlem, içeriğin bağımsız bir kopyasını oluşturur.

Bağımsızlık: Orijinal yükleyici içeriği silse veya ödemesini kesse bile, kopyalayan kullanıcılar kendi kopyaları için ödeme yaptığı sürece içerik ağda yaşamaya devam eder.

4. Adil Ekonomi (Depolama Kirası)
Kaldıkça-Öde: Blok zincirinin çöp verilerle dolmasını önlemek için boyut bazlı ücretlendirme yapılır.

Ücret: MB başına aylık 0.001 GHOST.

Şeffaflık: Aylık giderler ve kalan süre Dashboard üzerinden takip edilebilir.

🚀 Kurulum
Gereksinimler: Python 3.9+

Bash

# 1. Projeyi indirin
git clone [https://github.com/jangadeiro/GhostProtocol_Mesh_V2.git](https://github.com/jangadeiro/GhostProtocol_Mesh_V2.git)
cd ghostprotocol

# 2. Gerekli kütüphaneleri yükleyin
pip install flask requests cryptography
💻 Kullanım
Sistemi kullanmak için rolünüze uygun dosyayı çalıştırın.

A. Mesh Düğümü Olarak Çalıştır (Kullanıcı/Saha Cihazı)
Kişisel bilgisayarlar veya Raspberry Pi için. İnternet varken buluta, yokken çevreye bağlanır.

Bash

python ghost_mesh_node.py
Erişim: http://localhost:5001

Özellikler: Cüzdan, Madencilik, Site Gezintisi, Çevrimdışı Mod.

B. Bulut Sunucu Olarak Çalıştır (Ana Ağ Omurgası)
VPS (DigitalOcean, AWS vb.) sunucuları için. Veri merkezi görevi görür.

Bash

python ghost_server.py
Erişim: http://SUNUCU_IP_ADRESINIZ:5000

Özellikler: Yüksek erişilebilirlik, Ana blok deposu.

⚠️ Disclaimer / Yasal Uyarı
GhostProtocol is an experimental software designed for educational and research purposes. Use at your own risk. (GhostProtocol eğitim ve araştırma amaçlı tasarlanmış deneysel bir yazılımdır. Kullanım riski size aittir.)

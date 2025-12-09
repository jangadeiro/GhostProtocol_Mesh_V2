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

# 🇹🇷 Önemli Değişiklikler ve Güncellemeler (Key Changes and Updates)
Bu bölüm, GhostProtocol ağının merkeziyetsizliğini ve işlevselliğini önemli ölçüde artıran son güncellemeleri içerir.

🔥 Varlık Sunumu ve Merkeziyetsizlik İyileştirmeleri (Asset Serving & Decentralization Enhancements)
1. ghost_server.py Güncellemeleri
Merkeziyetsiz Linkleme: Görüntüleme linkleri artık sunucu adresini içermeyen göreceli URL'ler kullanır. Örneğin, <a href="/view_asset/<asset_id>"> formatı kullanılır. Bu, ağdaki Ghost Mesh Node (GMN) tarafından alıntılamayı destekler.

Kopyalama Linkleri: Kullanıcıların kopyaladığı linkler, kullanım kolaylığı için mutlak URL (http://ip:port/view_asset/<asset_id>) olarak kalmaya devam eder.

2. ghost_mesh_node.py Yeniden Yapılandırması
Rol Değişimi: Kod, sunucu (Backbone) rolünden çıkarılıp, saf bir Ağ Düğümü (Mesh Node) olarak yeniden yapılandırıldı.

Merkeziyetsiz Servis Eklendi: Yeni /view_asset/<asset_id> rotası eklendi. Bu sayede düğüm, merkezi sunucudan bağımsız olarak, zincirden eşlediği varlıkları (medya, domain içeriği) kendi yerel veritabanından doğrudan sunabilir. Bu, içerik dağıtımını tamamen merkeziyetsiz hale getirir.

Veritabanı Sadeleştirmesi: Düğümün yalnızca blokları ve varlıkları saklaması için veritabanı şeması sadeleştirildi. Kullanıcı, cüzdan ve işlem tabloları kaldırıldı.

Çoklu Dil Desteği: Kullanıcı arayüzüne Türkçe ve İngilizce dil destekleri eklendi.

3. Genel Etki
Bu değişiklikler, Ghost Mesh Node (GMN) kullanıcılarının, GhostProtocol'e içerik yükleyen kişilerin paylaştığı medyaları veya domainleri, merkezi bir sunucuya gitmeden, doğrudan zincir referansı (Asset ID) üzerinden alıntılayabilmesini sağlar.

# 🇬🇧 Key Changes and Updates
This section details the latest updates that significantly enhance the decentralization and functionality of the GhostProtocol network.

🔥 Asset Serving & Decentralization Enhancements
1. ghost_server.py Updates
Decentralized Linking: Viewing links now use relative URLs that do not include the server address. For example, the format <a href="/view_asset/<asset_id>"> is used. This supports referencing by the Ghost Mesh Node (GMN) across the network.

Copy Links: Links copied by users remain absolute URLs (http://ip:port/view_asset/<asset_id>) for ease of use.

2. ghost_mesh_node.py Refactoring
Role Change: The code was refactored from a Backbone Server role to act as a purely Network Node (Mesh Node).

Decentralized Service Added: A new /view_asset/<asset_id> route was implemented. This allows the node to serve assets (media, domain content) synchronized from the chain directly from its local database, independent of the central server. This fully decentralizes content distribution.

Database Simplification: The database schema was streamlined to only store blocks and assets. Tables for users, wallets, and transactions were removed.

Multi-Language Support: Turkish and English language support was added to the user interface.

3. Overall Impact
These changes enable Ghost Mesh Node (GMN) users to reference media or domains shared by GhostProtocol content creators directly via the chain reference (Asset ID), without needing to route through a centralized server.


# ⚠️ Disclaimer / Yasal Uyarı
GhostProtocol is an experimental software designed for educational and research purposes. Use at your own risk. (GhostProtocol eğitim ve araştırma amaçlı tasarlanmış deneysel bir yazılımdır. Kullanım riski size aittir.)

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
* **Cost:** `0.01 GHOST` per MB / Month.
* **Transparency:** Costs and remaining time are visible on the Dashboard.

### 🚀 Installation

**Prerequisites:** Python 3.9+

# 1. Clone the repository
`git clone [https://github.com/jangadeiro/GhostProtocol_Mesh_V2.git](https://github.com/jangadeiro/GhostProtocol_Mesh_V2.git) `

`cd ghostprotocol`

# 2. Install dependencies
`pip install flask requests cryptography`

💻 Usage
GhostProtocol consists of two main components. Choose the one that fits your role.

A. Run as a Mesh Node (Client/Field Device)
For laptops, Raspberry Pis, or personal computers. It connects to the Cloud when online and peers when offline.

Bash
`python ghost_mesh_node.py`
Access: http://localhost:5001

Features: Wallet, Mining, Content Browsing, Offline Sync.

B. Run as a Cloud Server (Mainnet Backbone)
For VPS (DigitalOcean, AWS, etc.). Acts as the primary data repository.

Bash
`python ghost_server.py`
Access: http://YOUR_SERVER_IP:5000

Features: High-availability block storage, centralized sync point.

<a name="-turkish">
🇹🇷 Türkçe</a>

Proje Özeti
GhostProtocol, internet bağlantısı olmasa dahi çalışabilmek üzere tasarlanmış, Proof-of-Work (PoW) tabanlı bir blok zinciridir. Merkeziyetsiz web sitelerine (`.ghost` alan adları) ev sahipliği yapar. İnternet varken bulut sunucularla, yokken ise yerel cihazlarla haberleşen hibrit bir yapıya sahiptir.

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

Ücret: MB başına aylık 0.01 GHOST.

Şeffaflık: Aylık giderler ve kalan süre Dashboard üzerinden takip edilebilir.

🚀 Kurulum
Gereksinimler: Python 3.9+

Bash

# 1. Projeyi indirin
`git clone [https://github.com/jangadeiro/GhostProtocol_Mesh_V2.git](https://github.com/jangadeiro/GhostProtocol_Mesh_V2.git) `

`cd ghostprotocol`

# 2. Gerekli kütüphaneleri yükleyin
pip install flask requests cryptography
💻 Kullanım
Sistemi kullanmak için rolünüze uygun dosyayı çalıştırın.

A. Mesh Düğümü Olarak Çalıştır (Kullanıcı/Saha Cihazı)
Kişisel bilgisayarlar veya Raspberry Pi için. İnternet varken buluta, yokken çevreye bağlanır.

Bash
`python ghost_mesh_node.py`

Erişim: http://localhost:5001

Özellikler: Cüzdan, Madencilik, Site Gezintisi, Çevrimdışı Mod.

B. Bulut Sunucu Olarak Çalıştır (Ana Ağ Omurgası)
VPS (DigitalOcean, AWS vb.) sunucuları için. Veri merkezi görevi görür.

Bash
`python ghost_server.py`

Erişim: http://SUNUCU_IP_ADRESINIZ:5000

Özellikler: Yüksek erişilebilirlik, Ana blok deposu.

# 🇹🇷 Önemli Değişiklikler ve Güncellemeler
Bu bölüm, GhostProtocol ağının merkeziyetsizliğini ve işlevselliğini önemli ölçüde artıran son güncellemeleri içerir.

🔥 Varlık Sunumu ve Merkeziyetsizlik İyileştirmeleri (Asset Serving & Decentralization Enhancements)
1. ghost_server.py Güncellemeleri
Merkeziyetsiz Linkleme: Görüntüleme linkleri artık sunucu adresini içermeyen göreceli URL'ler kullanır. Örneğin, `<a href="/view_asset/<asset_id>` formatı kullanılır. Bu, ağdaki Ghost Mesh Node (GMN) tarafından alıntılamayı destekler.

Kopyalama Linkleri: Kullanıcıların kopyaladığı linkler, kullanım kolaylığı için mutlak URL (http://ip:port/view_asset/<asset_id>) olarak kalmaya devam eder.

2. ghost_mesh_node.py Yeniden Yapılandırması
Rol Değişimi: Kod, sunucu (Backbone) rolünden çıkarılıp, saf bir Ağ Düğümü (Mesh Node) olarak yeniden yapılandırıldı.

Merkeziyetsiz Servis Eklendi: Yeni /view_asset/<asset_id> rotası eklendi. Bu sayede düğüm, merkezi sunucudan bağımsız olarak, zincirden eşlediği varlıkları (medya, domain içeriği) kendi yerel veritabanından doğrudan sunabilir. Bu, içerik dağıtımını tamamen merkeziyetsiz hale getirir.

Veritabanı Sadeleştirmesi: Düğümün yalnızca blokları ve varlıkları saklaması için veritabanı şeması sadeleştirildi. Kullanıcı, cüzdan ve işlem tabloları kaldırıldı.

Çoklu Dil Desteği: Kullanıcı arayüzüne Türkçe, İngilizce, Rusça ve Ermenice dil destekleri eklendi.

3. Genel Etki
Bu değişiklikler, Ghost Mesh Node (GMN) kullanıcılarının, GhostProtocol'e içerik yükleyen kişilerin paylaştığı medyaları veya domainleri, merkezi bir sunucuya gitmeden, doğrudan zincir referansı (Asset ID) üzerinden alıntılayabilmesini sağlar.

# 👻 Ghost Protocol - Gelişmiş Arama Özellikleri

Ghost Protocol, sansüre dayanıklı ve merkeziyetsiz bir içerik platformu olarak tasarlanmıştır. Bu sunucu (Backbone) uygulaması, ağa kaydedilen tüm .ghost alan adlarını ve medya varlıklarını endeksleyerek, kullanıcıların içeriklere kolayca ulaşmasını sağlayan gelişmiş bir arama motoru içerir.

🔍 Ghost Search (Arama) Özellikleri
Geliştirdiğimiz arama motoru, geleneksel dosya adı aramalarının ötesine geçerek, içeriğin kendisini anlamlandırmaya odaklanır.

# 1. Anahtar Kelime Endeksleme (Full-Text Search)
Sisteme kaydedilen her .ghost alan adı içeriği (HTML metni), sunucu tarafında özel bir algoritma (extract_keywords fonksiyonu) ile işlenir. Bu işlem:

HTML etiketlerini, betiklerini ve stil tanımlarını temizler.

Durma kelimelerini (ve, ile, the, and vb.) filtreler.

Kalan metni analiz ederek en alakalı anahtar kelimeleri çıkarır ve veritabanında saklar.

Arama sonucu: Kullanıcı bir terim girdiğinde, hem varlık adları hem de bu çıkarılan anahtar kelimeler arasında hızlı bir eşleşme aranır. Bu sayede, varlığın adını bilmeseniz bile içeriği ile ilgili terimlerle bulabilirsiniz.

# 2. Varlık Adı ve Meta Veri Eşleştirme
Geleneksel arama işlevini korur. Kullanıcı sorgusu, tam eşleşme veya kısmi eşleşme yoluyla:

.ghost alan adlarının adlarıyla,

Yüklenen medya dosyalarının adlarıyla (örn. kedi_fotografi.jpg),

Varlık tipini (domain, image, video vb.) içeren meta verilerle eşleştirilir.

# 3. Merkeziyetsiz Vizyon
Bu Backbone sunucu, ağ üzerindeki en büyük endeks görevi görür. ghost_mesh_node.py uygulamaları da (mobil ve CLI düğümleri), bu merkezi endeksi kullanarak arama yapabilir veya kendi yerel endekslerini oluşturabilir. Arama mekanizması, sansüre dayanıklı bir bilgi keşif katmanı oluşturmanın temelini atmıştır.

# 🇬🇧 Key Changes and Updates
This section details the latest updates that significantly enhance the decentralization and functionality of the GhostProtocol network.

🔥 Asset Serving & Decentralization Enhancements
1. ghost_server.py Updates
Decentralized Linking: Viewing links now use relative URLs that do not include the server address. For example, the format `<a href="/view_asset/<asset_id>` is used. This supports referencing by the Ghost Mesh Node (GMN) across the network.

Copy Links: Links copied by users remain absolute URLs (http://ip:port/view_asset/<asset_id>) for ease of use.

2. ghost_mesh_node.py Refactoring
Role Change: The code was refactored from a Backbone Server role to act as a purely Network Node (Mesh Node).

Decentralized Service Added: A new /view_asset/<asset_id> route was implemented. This allows the node to serve assets (media, domain content) synchronized from the chain directly from its local database, independent of the central server. This fully decentralizes content distribution.

Database Simplification: The database schema was streamlined to only store blocks and assets. Tables for users, wallets, and transactions were removed.

Multi-Language Support: Turkish, English, Russian and Armenian language support was added to the user interface.

3. Overall Impact
These changes enable Ghost Mesh Node (GMN) users to reference media or domains shared by GhostProtocol content creators directly via the chain reference (Asset ID), without needing to route through a centralized server.

# 👻 Ghost Protocol - Advanced Search Features
Ghost Protocol is designed as a censorship-resistant and decentralized content platform. This server (Backbone) application includes an advanced search engine that indexes all .ghost domains and media assets registered on the network, enabling users to easily discover content.

# 🔍 Ghost Search Capabilities
The search engine we developed goes beyond traditional filename searches and focuses on understanding the content itself.

# 1. Keyword Indexing (Full-Text Search)
The content of every .ghost domain registered in the system (HTML text) is processed by a special algorithm (extract_keywords function) on the server side. This process:

Cleans up HTML tags, scripts, and style definitions.

Filters out stop words (the, and, for, ile, ve, etc.).

Analyzes the remaining text to extract the most relevant keywords and stores them in the database.

Search Result: When a user enters a query, a rapid match is sought between both the asset names and these extracted keywords. This allows users to find an asset based on terms related to its content, even if they don't know the exact name.

# 2. Asset Name and Metadata Matching
The traditional search function is preserved. The user query is matched, via exact or partial matches, against:

The names of .ghost domain names.

The names of uploaded media files (e.g., cat_photo.jpg).

Metadata including the asset type (domain, image, video, etc.).

# 3. Decentralized Vision
This Backbone server acts as the largest index on the network. The ghost_mesh_node.py applications (both mobile and CLI nodes) can also perform searches using this central index or build their own local indexes. The search mechanism lays the foundation for creating a censorship-resistant information discovery layer.

# 🇬🇧 GhostProtocol Network also works on mobile platforms!
We haven't forgotten about mobile platforms, which will significantly enhance the decentralization, functionality, and reach of the GhostProtocol network. The GhostProtocol Mobile version, which has a separate Git repository, can be accessed at the following Git address.

https://github.com/jangadeiro/GhostProtocol_Mesh_V2_MOBILE

# 🇹🇷 GhostProtocol Ağı Mobil Platformlarda da Çalışır!
GhostProtocol ağının merkeziyetsizliğini, işlevselliğini ve erişimini önemli ölçüde artıracak olan mobil platformları da unutmadık. Ayrı bir Git Reposuna sahip olan GhostProtocol Mobil versiyona aşağıdaki git adresinden ulaşabilirsiniz.

https://github.com/jangadeiro/GhostProtocol_Mesh_V2_MOBILE

# GhostProtocol with GhostMessenger 👻

**[TR]** Özgür, blokzincir tabanlı, sansürlenemez ve tamamen şifreli bir iletişim & internet altyapısı.
**[EN]** A free, blockchain-based, uncensorable, and fully encrypted communication & internet infrastructure.

---

## 🌍 GhostMessenger Hakkında / About the GhostMessenger

**[TR]**
GhostProtocol, merkeziyetsiz bir ağ (Mesh Network) ve blokzinciri teknolojisi kullanarak internet sansürlerini aşmayı hedefler. Sadece sansürsüz web içeriği barındırmakla kalmaz, aynı zamanda **GhostMessenger** modülü ile tamamen güvenli, uçtan uca şifreli ve anonim bir anlık mesajlaşma deneyimi sunar.

**[EN]**
GhostProtocol aims to bypass internet censorship using a decentralized Mesh Network and blockchain technology. Not only does it host uncensorable web content, but it also provides a secure, end-to-end encrypted, and anonymous instant messaging experience via the **GhostMessenger** module.

---

## 💬 GhostMessenger Özellikleri / Features

### 🔐 Uçtan Uca Şifreleme / End-to-End Encryption
**[TR]** Mesajlarınız yerel veritabanında şifreli olarak saklanır. Sadece gönderen ve alıcı bu mesajları okuyabilir. Merkezi bir sunucu yoktur, bu yüzden mesajlarınız asla "görülemez".
**[EN]** Your messages are stored encrypted in the local database. Only the sender and recipient can read them. Since there is no central server, your messages can never be "seen".

### 📎 Medya Paylaşımı / Media Sharing
**[TR]** "Kayıtlı Varlıklarım" (My Assets) bölümüne yüklediğiniz herhangi bir dosyayı (resim, ses, video, belge vb.) sohbet penceresinden kolayca paylaşabilirsiniz. Bu dosyalar IPFS benzeri dağıtık bir yapıda saklanır.
**[EN]** Easily share any file (image, voice, video, document etc.) uploaded to "My Assets" directly from the chat window. These files are stored in a distributed structure similar to IPFS.

### 💰 Mikro Ödeme Modeli / Micro-Payment Model
**[TR]** Spam'i önlemek ve ağı sürdürülebilir kılmak için her etkileşim küçük bir GHOST coin ödemesi gerektirir:
* **Arkadaş Ekleme:** 0.00001 GHOST
* **Mesaj Gönderme:** 0.00001 GHOST
Bu ücretler, ağı ayakta tutan kullanıcılara dağıtılır.

**[EN]** To prevent spam and ensure network sustainability, every interaction requires a small GHOST coin payment:
* **Add Friend:** 0.00001 GHOST
* **Send Message:** 0.00001 GHOST
These fees are distributed to the users who maintain the network.

---

## 🚀 Nasıl Kullanılır? / How to Use

1.  **Başlat / Start:** Sunucuyu çalıştırın: `python ghost_server.py`
2.  **Giriş / Login:** Tarayıcınızdan `http://localhost:5000` adresine gidin.
3.  **Kazan / Earn:** Başlangıç bakiyeniz 0'dır. "Madencilik" (Mining) sekmesine gidin ve ilk GHOST coinlerinizi üretin.
4.  **Sohbet / Chat:** Sağ alt köşedeki 💬 ikonuna tıklayın.
    * Arkadaşınızın kullanıcı adını girip `+` butonuna basarak davet yollayın.
    * Arkadaşınız listeye eklendiğinde ismine tıklayıp sohbete başlayın.

---

## 📊 İstatistikler / Statistics

**[TR]** Giriş ekranında ve madencilik sayfasında ağın anlık durumunu görebilirsiniz:
* **Toplam Arz:** 100.000.000 GHOST
* **Dolaşımdaki Arz:** Şu ana kadar üretilen miktar.
* **Kalan Arz:** Henüz üretilmemiş miktar.
* **Yarılanma (Halving):** Ödülün yarıya düşmesine kalan blok sayısı.

**[EN]** You can view the live status of the network on the login and mining pages:
* **Total Supply:** 100,000,000 GHOST
* **Circulating Supply:** Amount mined so far.
* **Remaining Supply:** Amount yet to be mined.
* **Halving:** Number of blocks remaining until the reward is halved.

---


# ⚠️ Disclaimer / Yasal Uyarı
GhostProtocol is an experimental software designed for educational and research purposes. Use at your own risk. (GhostProtocol eğitim ve araştırma amaçlı tasarlanmış deneysel bir yazılımdır. Kullanım riski size aittir.)

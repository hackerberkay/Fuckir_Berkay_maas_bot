"""
Ruble Maaş Takip Botu — GitHub Actions sürümü
---------------------------------------------
GitHub her ~5 dakikada bir bu dosyayı çalıştırır:
  1) Google Finance'ten RUB/TRY kurunu alır.
  2) Bota yazılan yeni mesajları okur (kayıt, maaş, eşik soruları).
  3) Her kişiye kendi maaşı ve eşiğine göre bildirim gönderir.

Kayıt akışı (arkadaşlar için):
  /start  -> "Maaşın kaç ruble?"  -> 144000
          -> "Kaç TL değişince haber vereyim?" -> 300
Komutlar: /durum  /maas  /esik  /stop  /yardim

Maaş her 5.000 TL sınırını (80, 85, 90, 95 bin...) yukarı geçtiğinde
mesaja "Berkay'a da bir şeyler ısmarlarsın artık" notu eklenir.

Gizli ayarlar (GitHub > Settings > Secrets and variables > Actions):
  BOT_TOKEN  - BotFather'dan alınan token
  CHAT_ID    - Botun sahibinin sohbet numarası (Berkay)
  MAAS_RUB   - Sahibin maaşı (ruble), örn. 144000
  DAVET_KODU - (isteğe bağlı) Girilirse sadece davet linkiyle gelenler katılabilir:
               https://t.me/BOT_ADI?start=DAVET_KODU

Gizlilik: Herkesin maaşı ve sohbet numarası veri.enc dosyasında ŞİFRELİ durur.
Şifre anahtarı BOT_TOKEN'dan üretilir; depo herkese açık olsa da okunamaz.
(BOT_TOKEN değişirse kayıtlar okunamaz, herkes /start ile yeniden kaydolur.)
"""

import base64
import hashlib
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone

import requests
from cryptography.fernet import Fernet, InvalidToken

SAHIP_ADI = "Berkay"
VARSAYILAN_ESIK = 300   # Sahip için varsayılan eşik (TL)
BAND = 5000             # 80-85-90-95 bin gibi sınırlar
VERI_DOSYASI = "veri.enc"
ESKI_DOSYA = "durum.json"
TR = timezone(timedelta(hours=3))

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("CHAT_ID", "").strip()
MAAS_RUB = os.environ.get("MAAS_RUB", "").strip()
DAVET_KODU = os.environ.get("DAVET_KODU", "").strip()

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

IYI_YORUMLAR = [
    "O yeah amk 🔥",
    "Zengin oluyoruz lan 💸",
    "Ruble uçuyor, biz de uçuyoruz ✈️",
    "Bugün kebap bizden 🍖",
    "Patron gibi hissediyorum amk 😎",
    "Ruble babadır 🫡",
    "Cüzdan gülümsüyor 😁",
    "Bu gidişle Lambo alırız (almayız ama olsun) 🏎️",
    "Kim tutar bizi amk 💪",
    "Hadi bi çay koy, kutlayalım ☕",
    "Yeşil yeşil, mis gibi 📈",
    "Kasaya para giriyor, sesini duyuyon mu? 🤑",
    "Bugün şanslı günümüz amk 🍀",
    "Ruble ayağa kalktı, alkış 👏",
    "Ohh be, ilaç gibi geldi",
    "Maaş fitness yapıyor, kaslanıyor 💪",
    "Bu artış bana iyi geldi amk",
    "Para para para 💰",
    "Böyle devam et ruble, gözünü seveyim",
    "Ekonomist olsam bu kadar sevinmezdim 🎉",

    "Ruble patladı amk, para bize akıyor 🤑",
    "Bu ne lan, zenginlik kokuyor amk 💸",
    "Siktir be, ruble coştu, kebap bizden 🍖",
    "Lan olm ruble uçuyor, cüzdan dans ediyor amk 💃",
    "Orospu çocuğu ruble sonunda yüzümüzü güldürdü 😎",
    "Amk bu artış tam ilaç gibi, devam et ruble 🚀",
    "Ruble kudurdu amk, para kazanıyoruz 💰",
    "Lan bu ne, hesap yeşillendi amk 📈",
    "Siktir lan, bugün patron biziz 😎",
    "Amk ruble baba oldu, önünde eğilin 🫡",
    "Bu gidişle amk zengin oluruz, olmasak da gaz var 💪",
    "Ruble şaha kalktı amk, alkışı hak ediyor 👏",
    "Lan para geliyor, kapıyı açın amk 🚪💸",
    "Amk bu grafik yeşil, içim yeşillendi 📊",
    "Siktir be, ruble bizi sevdi sonunda amk ❤️",
    "Lan cüzdan kas yapıyor amk, maaş fitnessa devam 💪",
    "Amk ruble coştu, çaylar benden lan ☕",
    "Orospu çocuğu grafik tersine döndü, para yağıyor amk 🌧️💸",
    "Lan bu artışla kebap da börek de benden amk 🍖",
    "Siktir lan, ruble baba yola çıktı, biz de arkada 😎",
    "Amk ne güzel gün, hesap yeşil, keyif yerinde 🍀",
    "Lan ruble gülümsüyor, ben de sırıtıyorum amk 😁",
    "Bu ne be amk, para sesi kulaklarımda çınlıyor 🤑",
    "Siktir be ruble, böyle devam et, adam yerine koydun bizi amk 🫡",
    "Amk bu artışla Lambo hayali gerçek oldu (lan yok ama olsun) 🏎️",
    "Lan ruble kendine geldi, cüzdan bayram ediyor amk 🎉",
    "Orospu çocuğu dolar değil ruble bizi uçuruyor amk ✈️",
    "Amk bu grafik bana iyi geldi, doktora gerek yok 📈",
    "Siktir lan, kasaya para giriyor, sesi duyuluyor amk 🤑",
    "Lan bugün şanslı günümüz amk, ruble sağ olsun 🍀",
]

KOTU_YORUMLAR = [
    "Hay amk 😩",
    "Ruble yine düştü, ben de düştüm",
    "Kebap iptal, simit yiyoruz 🥯",
    "Cüzdan ağlıyor 😭",
    "Bu ne lan böyle amk",
    "Kemerleri sıkın arkadaşlar",
    "Ruble tatile çıkmış galiba 🏖️",
    "Kırmızı kırmızı, içim acıdı 📉",
    "Bugün de fakirlik günü amk",
    "Yine mi ya, yine mi",
    "Sabır... sabır... 🧘",
    "Ruble bizi sevmiyor amk 💔",
    "Lambo hayali ertelendi 🚗❌",
    "Bu düşüş beni benden aldı",
    "Çay bile pahalı geldi şu an ☕",
    "Ruble kendine gel amk",
    "Para eriyor, kar gibi ❄️",
    "Neyse ya, yarın çıkar (umarım)",
    "Bugün harcama yok, evde otur",
    "Of of of, maaş diyet yapıyor 😮‍💨",

    "Hay siktiğimin rublesi, yine düştü amk 😩",
    "Lan bu ne amk, cüzdan ağlıyor 😭",
    "Siktir be, ruble yine bizi sikecek galiba 📉",
    "Amk bu düşüş ne lan, kebap iptal 🥯",
    "Orospu çocuğu ruble, bizi sevmiyor amk 💔",
    "Lan yine mi amk, maaş eridi gitti",
    "Siktir lan, ruble tatile çıkmış, biz evde oturuyoruz 🏖️",
    "Amk bu grafik kırmızı, içim kan ağlıyor 📉",
    "Lan bu ne be amk, para kar gibi eriyor ❄️",
    "Siktir be ruble, kendine gel amk",
    "Amk bugün de fakirlik günü, harcama yok",
    "Orospu çocuğu düşüş beni benden aldı amk",
    "Lan cüzdan küstü amk, açmıyor kendini 😤",
    "Siktir lan, ruble bizi sikecek, kemerleri sıkın",
    "Amk bu ne lan, çay bile pahalı geldi ☕",
    "Lan ruble yine yamuk yaptı amk 📉",
    "Siktir be, maaş diyet yapıyor amk 😮‍💨",
    "Amk bu düşüşle Lambo hayali yine yattı 🚗❌",
    "Orospu çocuğu ruble, bizi fakir bıraktın amk",
    "Lan of of of, amk bu ne böyle 😩",
    "Siktir lan, hesap yine kırmızı, keyifler bozuk amk",
    "Amk ruble kendine gel, bizi perişan ettin",
    "Lan bu ne amk, para uçtu gitti 💸📉",
    "Siktir be, bugün harcama yok, evde oturuyoruz amk",
    "Amk bu düşüş beni deli etti lan",
    "Orospu çocuğu grafik, yine aşağı bakıyor amk",
    "Lan ruble, seni sevmiyorum artık amk 💔",
    "Siktir lan, cüzdan ağlıyor, ben de ağlıyorum amk 😭",
    "Amk bu ne lan, ruble bizi sikecek gibi",
    "Lan yine mi amk, sabır taşı çatladı 🧘",
]


# ───────────────────────── yardımcılar ─────────────────────────

def simdi():
    return datetime.now(TR)


def binlik(x):
    """61920.4 -> '61.920'"""
    return f"{round(x):,}".replace(",", ".")


def sayi_oku(metin):
    """'144.000', '144 000', '144000 rub', '144k' -> 144000. Anlaşılmazsa None."""
    t = metin.lower().replace(" ", "").replace(".", "").replace(",", "")
    carpan = 1
    if t.endswith("k") or t.endswith("bin"):
        carpan = 1000
        t = t[:-1] if t.endswith("k") else t[:-3]
    rakamlar = re.sub(r"[^0-9]", "", t)
    if not rakamlar or not re.fullmatch(r"[0-9]+(rub|ruble|tl|₽)?", t):
        return None
    return int(rakamlar) * carpan


def sahipler():
    return [c.strip() for c in CHAT_ID.split(",") if c.strip()]


def isim(kimden):
    ad = " ".join(x for x in [kimden.get("first_name"), kimden.get("last_name")] if x)
    if kimden.get("username"):
        ad += f" (@{kimden['username']})"
    return ad or "Biri"


# ───────────────────────── kur ─────────────────────────

def google_kur():
    """Google Finance RUB-TRY sayfasındaki en son veri noktasını okur."""
    r = requests.get(
        "https://www.google.com/finance/quote/RUB-TRY",
        params={"hl": "en"},
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
        cookies={"CONSENT": "YES+"},
        timeout=20,
    )
    r.raise_for_status()
    # Grafik verisi: [[yıl,ay,gün,saat,dakika,null,null,[...]],[fiyat,...]]
    noktalar = re.findall(
        r"\[\[(\d{4}),(\d{1,2}),(\d{1,2}),(\d{1,2}|null),(\d{1,2}|null),null,null,"
        r"\[[^\]]*\]\],\[([0-9.Ee-]+),",
        r.text,
    )
    if not noktalar:
        raise ValueError("Google sayfasında kur bulunamadı")
    s = lambda v: int(v) if v != "null" else 0
    en_son = max(noktalar, key=lambda p: tuple(s(x) for x in p[:5]))
    return float(en_son[5])


def kur_al():
    """1 RUB kaç TL? Önce Google Finance (anlık), olmazsa ExchangeRate-API (günlük)."""
    try:
        fiyat = google_kur()
        if 0.01 < fiyat < 100:
            print("Kaynak: Google Finance")
            return fiyat
        print(f"Google'dan anormal kur geldi: {fiyat}")
    except Exception as e:
        print(f"Google hatası: {e}")

    print("Kaynak: ExchangeRate-API (yedek, günlük)")
    r = requests.get("https://open.er-api.com/v6/latest/RUB", timeout=20)
    fiyat = float(r.json()["rates"]["TRY"])
    if fiyat <= 0:
        raise ValueError("Geçersiz kur")
    return fiyat


# ───────────────────────── telegram ─────────────────────────

def mesaj_gonder(chat_id, metin):
    """Mesaj gönderir. chat_id tek numara, virgüllü metin veya liste olabilir.
    Dönüş: (başarılı sayısı, botu engelleyenlerin listesi)"""
    if isinstance(chat_id, (list, tuple)):
        kisiler = [str(c).strip() for c in chat_id if str(c).strip()]
    else:
        kisiler = [c.strip() for c in str(chat_id).split(",") if c.strip()]
    basarili, engelleyenler = 0, []
    for kisi in kisiler:
        try:
            r = requests.post(
                f"{API}/sendMessage",
                data={"chat_id": kisi, "text": metin},
                timeout=20,
            )
            if r.ok:
                basarili += 1
            else:
                print(f"Telegram hatası: {r.status_code} {r.text}")
                if r.status_code in (400, 403):
                    engelleyenler.append(kisi)
        except Exception as e:
            print(f"Telegram hatası: {e}")
    return basarili, engelleyenler


def chat_id_bul():
    """CHAT_ID girilmemişse: bota yazılan son mesajdan sohbet numarasını bulur."""
    r = requests.get(f"{API}/getUpdates", timeout=20)
    sohbetler = [
        (g.get("message") or {}).get("chat", {}).get("id")
        for g in r.json().get("result", [])
    ]
    sohbetler = [c for c in sohbetler if c]
    if not sohbetler:
        print("CHAT_ID yok. Telegram'da botunuza /start yazıp bu işlemi tekrar çalıştırın.")
        sys.exit(1)
    cid = sohbetler[-1]
    mesaj_gonder(
        cid,
        "👋 Bot sizi buldu!\n\n"
        f"Sohbet numaranız (CHAT_ID): {cid}\n\n"
        "Bu numarayı GitHub'da CHAT_ID adlı secret olarak ekleyin.",
    )
    print("CHAT_ID bulundu ve Telegram'a gönderildi.")


# ───────────────────────── veri (şifreli) ─────────────────────────

def _fernet():
    anahtar = hashlib.sha256(f"maas-bot:{BOT_TOKEN}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(anahtar))


def yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "rb") as f:
                return json.loads(_fernet().decrypt(f.read().strip()))
        except InvalidToken:
            print("UYARI: veri.enc okunamadı (BOT_TOKEN değişmiş olabilir). Sıfırdan başlanıyor.")
            return {"_sifirlandi": True}
    if os.path.exists(ESKI_DOSYA):
        with open(ESKI_DOSYA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def kaydet(veri):
    with open(VERI_DOSYASI, "wb") as f:
        f.write(_fernet().encrypt(json.dumps(veri, ensure_ascii=False).encode()) + b"\n")
    if os.path.exists(ESKI_DOSYA):
        os.remove(ESKI_DOSYA)  # şifresiz eski dosyayı kaldır


def gecis(veri):
    """Eski sürümün durum.json yapısını yeni yapıya çevirir."""
    kullanicilar = veri.setdefault("kullanicilar", {})
    for kisi in veri.pop("aboneler", []):
        kullanicilar.setdefault(str(kisi), {"maas": None, "esik": None, "adim": "maas",
                                            "ref_kur": None, "band": None, "sor": True})
    ref = veri.pop("referans_kur", None) or veri.pop("onceki_kur", None)
    veri.pop("onceki_kur", None)
    if ref:
        for s in sahipler():
            kullanicilar.setdefault(s, {}).setdefault("ref_kur", ref)


def sahip_kaydi(veri, s):
    """Sahibin kaydı yoksa MAAS_RUB ve varsayılan eşikle oluşturur."""
    k = veri["kullanicilar"].setdefault(s, {})
    if not k.get("maas"):
        try:
            k["maas"] = int(float(MAAS_RUB))
        except ValueError:
            k["maas"] = None
            k["adim"] = "maas"
            k["sor"] = True
    k.setdefault("esik", VARSAYILAN_ESIK)
    k.setdefault("adim", None)
    k.setdefault("ref_kur", None)
    k.setdefault("band", None)
    return k


# ───────────────────────── yorumlar ─────────────────────────

def yorum_sec(veri, tur, liste):
    """Desteden karışık sırayla yorum çeker; deste bitince yeniden karıştırır."""
    anahtar = f"{tur}_deste"
    deste = [i for i in veri.get(anahtar, []) if 0 <= i < len(liste)]
    if not deste:
        deste = list(range(len(liste)))
        random.shuffle(deste)
        son = veri.get(f"{tur}_son")
        if son is not None and len(deste) > 1 and deste[0] == son:
            deste.append(deste.pop(0))  # art arda aynısı gelmesin
    secilen = deste.pop(0)
    veri[anahtar] = deste
    veri[f"{tur}_son"] = secilen
    return liste[secilen]


# ───────────────────────── sohbet ─────────────────────────

SORU_MAAS = "💬 Maaşın kaç ruble? Sadece rakam yaz.\nÖrnek: 144000"
SORU_ESIK = ("💬 Maaşın kaç TL artınca veya düşünce haber vereyim?\n"
             "Örnek: 300")
YARDIM = ("📋 Komutlar:\n"
          "/durum – maaşın şu an kaç TL\n"
          "/maas – maaşını değiştir\n"
          "/esik – kaç TL'de haber vereyim, değiştir\n"
          "/stop – bildirimleri kapat")


def ayar_tamam(k):
    return bool(k.get("maas")) and bool(k.get("esik")) and not k.get("adim")


def durum_metni(k, kur):
    deger = k["maas"] * kur
    return (f"💰 Maaşın şu an: {binlik(deger)} TL\n"
            f"• Maaş: {binlik(k['maas'])} RUB\n"
            f"• Bildirim eşiği: {binlik(k['esik'])} TL\n"
            f"• Kur: 1 RUB = {kur:.4f} TL")


def kurulumu_bitir(k, kur):
    deger = k["maas"] * kur
    k["ref_kur"] = kur
    k["band"] = int(deger // BAND)
    return ("✅ Tamamdır!\n"
            f"💰 Maaşın şu an: {binlik(deger)} TL\n"
            f"{binlik(k['esik'])} TL artınca veya düşünce haber vereceğim.\n\n" + YARDIM)


def mesajlari_isle(veri, kur):
    """Bota yazılan yeni mesajları okur ve cevaplar."""
    try:
        r = requests.get(
            f"{API}/getUpdates",
            params={"offset": veri.get("update_offset", 0), "timeout": 0},
            timeout=20,
        )
        guncellemeler = r.json().get("result", [])
    except Exception as e:
        print(f"Mesaj okuma hatası: {e}")
        return

    kullanicilar = veri["kullanicilar"]
    for g in guncellemeler:
        veri["update_offset"] = g["update_id"] + 1
        mesaj = g.get("message") or {}
        sohbet = mesaj.get("chat", {})
        if sohbet.get("type") != "private":
            continue
        kid = str(sohbet.get("id", ""))
        metin = (mesaj.get("text") or "").strip()
        if not kid or not metin:
            continue
        komut = metin.split()[0].split("@")[0].lower() if metin.startswith("/") else ""
        sahip = kid in sahipler()
        k = kullanicilar.get(kid)

        # Kayıtlı olmayan biri
        if k is None:
            if komut != "/start":
                mesaj_gonder(kid, "👋 Başlamak için /start yaz.")
                continue
            parcalar = metin.split(maxsplit=1)
            kod = parcalar[1].strip() if len(parcalar) > 1 else ""
            if DAVET_KODU and kod != DAVET_KODU:
                mesaj_gonder(kid, "🔒 Bu bot özel. Katılmak için davet linki gerekiyor.")
                continue
            kullanicilar[kid] = {"maas": None, "esik": None, "adim": "maas",
                                 "ref_kur": None, "band": None}
            mesaj_gonder(kid, "👋 Hoş geldin! Birkaç soru soracağım.\n\n" + SORU_MAAS)
            mesaj_gonder(sahipler(), f"👤 Yeni abone: {isim(mesaj.get('from', {}))}")
            continue

        # Komutlar
        if komut == "/start":
            if ayar_tamam(k):
                mesaj_gonder(kid, "Zaten kayıtlısın 👍\n\n" + durum_metni(k, kur) + "\n\n" + YARDIM)
            else:
                k["adim"] = "maas" if not k.get("maas") else "esik"
                mesaj_gonder(kid, SORU_MAAS if k["adim"] == "maas" else SORU_ESIK)
        elif komut == "/stop":
            if sahip:
                mesaj_gonder(kid, "Sen botun sahibisin 😎 Durdurmak için GitHub'da "
                                  "Actions → Maas Takip → Disable workflow.")
            else:
                del kullanicilar[kid]
                mesaj_gonder(kid, "👋 Bildirimler kapandı. Tekrar gelmek istersen /start yaz.")
                mesaj_gonder(sahipler(), f"🚪 Ayrıldı: {isim(mesaj.get('from', {}))}")
        elif komut == "/maas":
            k["adim"] = "maas"
            mesaj_gonder(kid, SORU_MAAS)
        elif komut == "/esik":
            k["adim"] = "esik"
            mesaj_gonder(kid, SORU_ESIK)
        elif komut == "/durum":
            if k.get("maas") and k.get("esik"):
                mesaj_gonder(kid, durum_metni(k, kur))
            else:
                mesaj_gonder(kid, "Önce soruları cevaplaman lazım.\n\n"
                                  + (SORU_MAAS if not k.get("maas") else SORU_ESIK))
        elif komut:
            mesaj_gonder(kid, YARDIM)

        # Soru cevapları
        elif k.get("adim") == "maas":
            maas = sayi_oku(metin)
            if not maas or not (1_000 <= maas <= 100_000_000):
                mesaj_gonder(kid, "🤔 Anlamadım. Maaşını sadece rakamla yaz.\nÖrnek: 144000")
                continue
            k["maas"] = maas
            k["ref_kur"] = None
            if k.get("esik"):
                k["adim"] = None
                mesaj_gonder(kid, kurulumu_bitir(k, kur))
            else:
                k["adim"] = "esik"
                mesaj_gonder(kid, f"👍 {binlik(maas)} RUB, şu an {binlik(maas * kur)} TL ediyor.\n\n"
                                  + SORU_ESIK)
        elif k.get("adim") == "esik":
            esik = sayi_oku(metin)
            if not esik or not (10 <= esik <= 10_000_000):
                mesaj_gonder(kid, "🤔 Anlamadım. Sadece rakam yaz.\nÖrnek: 300")
                continue
            k["esik"] = esik
            k["adim"] = None
            mesaj_gonder(kid, kurulumu_bitir(k, kur))
        else:
            mesaj_gonder(kid, YARDIM)


def ismarla_notu(sahip):
    if sahip:
        return "Kendine bir şeyler ısmarla artık 😎"
    return f"Ekstra {SAHIP_ADI}'a da bir şeyler ısmarlarsın artık 😏"


def bildirimleri_gonder(veri, kur, zaman):
    """Her kişiye kendi maaşı ve eşiğine göre bildirim gönderir."""
    kullanicilar = veri["kullanicilar"]
    toplam_deneme = toplam_basarili = 0
    for kid in list(kullanicilar):
        k = kullanicilar[kid]
        if not ayar_tamam(k):
            continue
        sahip = kid in sahipler()
        deger = k["maas"] * kur
        su_anki_band = int(deger // BAND)

        if not k.get("ref_kur"):
            k["ref_kur"] = kur
            k["band"] = su_anki_band
            continue
        if k.get("band") is None:
            k["band"] = su_anki_band

        fark = deger - k["maas"] * k["ref_kur"]
        esik_gecti = abs(fark) >= k["esik"]
        band_gecti = su_anki_band > k["band"]
        if not band_gecti and deger < k["band"] * BAND - 1000:
            k["band"] = su_anki_band  # belirgin düştü: sınırı aşağı çek

        if not (esik_gecti or band_gecti):
            continue

        satirlar = [f"💰 Maaşın: {binlik(deger)} TL"]
        if esik_gecti and fark > 0:
            satirlar += [f"📈 +{binlik(fark)} TL arttı",
                         f"💬 {yorum_sec(veri, 'iyi', IYI_YORUMLAR)}"]
        elif esik_gecti:
            satirlar += [f"📉 -{binlik(abs(fark))} TL düştü",
                         f"💬 {yorum_sec(veri, 'kotu', KOTU_YORUMLAR)}"]
        if band_gecti:
            satirlar.append(f"🎉 {su_anki_band * BAND // 1000} bin TL'yi geçti! {ismarla_notu(sahip)}")
        satirlar.append(f"🕒 {zaman:%H:%M} • 1 RUB = {kur:.4f} TL")

        toplam_deneme += 1
        basarili, engelleyenler = mesaj_gonder(kid, "\n".join(satirlar))
        toplam_basarili += basarili
        if basarili:
            if esik_gecti:
                k["ref_kur"] = kur
            if band_gecti:
                k["band"] = su_anki_band
        elif engelleyenler and not sahip:
            del kullanicilar[kid]  # botu engellemiş
            print("Botu engelleyen bir abone silindi.")
    return toplam_deneme, toplam_basarili


# ───────────────────────── ana akış ─────────────────────────

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN secret'ı eksik.")
        sys.exit(1)
    if not CHAT_ID:
        chat_id_bul()
        return

    veri = yukle()
    once = json.dumps(veri, sort_keys=True, ensure_ascii=False)
    sifirlandi = veri.pop("_sifirlandi", False)
    gecis(veri)
    for s in sahipler():
        sahip_kaydi(veri, s)

    kur = kur_al()
    zaman = simdi()
    print(f"{zaman:%d.%m.%Y %H:%M} | 1 RUB = {kur:.5f} TL")

    if sifirlandi:
        mesaj_gonder(sahipler(), "⚠️ Kayıtlar okunamadı (BOT_TOKEN değişmiş olabilir). "
                                 "Arkadaşların /start ile yeniden kaydolmalı.")

    # Eski sürümden gelen abonelere maaş sorusunu sor
    for kid, k in veri["kullanicilar"].items():
        if k.pop("sor", False):
            mesaj_gonder(kid, "🆕 Bot güncellendi! Artık herkes kendi maaşını girebiliyor.\n\n"
                              + SORU_MAAS)

    mesajlari_isle(veri, kur)
    deneme, basarili = bildirimleri_gonder(veri, kur, zaman)

    veri["son_gun"] = f"{zaman:%Y-%m-%d}"  # GitHub görevi kapatmasın diye günlük kayıt
    if json.dumps(veri, sort_keys=True, ensure_ascii=False) != once or os.path.exists(ESKI_DOSYA):
        kaydet(veri)
    if deneme and not basarili:
        sys.exit(1)


if __name__ == "__main__":
    main()

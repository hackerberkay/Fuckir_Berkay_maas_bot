"""
Ruble Maaş Takip — GitHub Actions sürümü
----------------------------------------
GitHub her ~10 dakikada bir bu dosyayı çalıştırır ve maaşın TL karşılığını
Telegram'a yazar. Bir önceki mesaja göre arttıysa iyi, düştüyse kötü bir yorum
ekler. Yorumlar karışık sırayla gelir; hepsi bitmeden aynısı tekrar etmez.

Gizli ayarlar (GitHub > Settings > Secrets and variables > Actions):
  BOT_TOKEN  - BotFather'dan alınan token
  CHAT_ID    - Telegram sohbet numaranız (bot ilk çalışmada size söyler).
               Birden fazla kişi için virgülle ayırın: 8943985917,1234567890
  MAAS_RUB   - Maaş (ruble), örn. 144000
  DAVET_KODU - (isteğe bağlı) Girilirse sadece davet linkiyle gelenler katılabilir:
               https://t.me/BOT_ADI?start=DAVET_KODU

Abonelik: Bota /start yazan herkes otomatik eklenir, /stop yazan çıkar.
Sahibine (CHAT_ID) her yeni abone bildirilir.

Not: durum.json dosyasına maaş tutarı değil, kur ve abonelerin sohbet numaraları yazılır.
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import requests

DOSYA = "durum.json"
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


def simdi():
    return datetime.now(TR)


def binlik(x):
    """61920.4 -> '61.920'"""
    return f"{round(x):,}".replace(",", ".")


def kur_al():
    """1 RUB kaç TL? Önce Yahoo (anlık), olmazsa ExchangeRate-API (günlük)."""
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/RUBTRY=X",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        fiyat = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]
        if fiyat and float(fiyat) > 0:
            return float(fiyat)
    except Exception as e:
        print(f"Yahoo hatası: {e}")

    r = requests.get("https://open.er-api.com/v6/latest/RUB", timeout=20)
    fiyat = float(r.json()["rates"]["TRY"])
    if fiyat <= 0:
        raise ValueError("Geçersiz kur")
    return fiyat


def mesaj_gonder(chat_id, metin):
    """Mesajı gönderir. chat_id tek numara, virgüllü metin veya liste olabilir.
    Biri başarısız olursa (ör. botu engellediyse) diğerlerine yine gönderilir.
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
                print(f"Telegram hatası ({kisi}): {r.status_code} {r.text}")
                if r.status_code in (400, 403):
                    engelleyenler.append(kisi)
        except Exception as e:
            print(f"Telegram hatası ({kisi}): {e}")
    return basarili, engelleyenler


def sahipler():
    return [c.strip() for c in CHAT_ID.split(",") if c.strip()]


def isim(kimden):
    ad = " ".join(x for x in [kimden.get("first_name"), kimden.get("last_name")] if x)
    if kimden.get("username"):
        ad += f" (@{kimden['username']})"
    return ad or "Biri"


def abone_isle(durum):
    """Bota yazılan yeni mesajları okur: /start yazanı ekler, /stop yazanı çıkarır."""
    try:
        r = requests.get(
            f"{API}/getUpdates",
            params={"offset": durum.get("update_offset", 0), "timeout": 0},
            timeout=20,
        )
        guncellemeler = r.json().get("result", [])
    except Exception as e:
        print(f"Abone kontrol hatası: {e}")
        return

    aboneler = durum.setdefault("aboneler", [])
    for g in guncellemeler:
        durum["update_offset"] = g["update_id"] + 1
        mesaj = g.get("message") or {}
        sohbet = mesaj.get("chat", {})
        if sohbet.get("type") != "private":
            continue
        kid = str(sohbet.get("id", ""))
        metin = (mesaj.get("text") or "").strip()
        komut = metin.split()[0].split("@")[0].lower() if metin else ""
        if not kid or kid in sahipler():
            continue

        if komut == "/start":
            parcalar = metin.split(maxsplit=1)
            kod = parcalar[1].strip() if len(parcalar) > 1 else ""
            if DAVET_KODU and kod != DAVET_KODU:
                mesaj_gonder(kid, "🔒 Bu bot özel. Katılmak için davet linki gerekiyor.")
                continue
            if kid not in aboneler:
                aboneler.append(kid)
                mesaj_gonder(
                    kid,
                    "✅ Hoş geldin! Artık 10 dakikada bir maaş mesajı gelecek.\n"
                    "Ayrılmak istersen /stop yaz.",
                )
                mesaj_gonder(sahipler(), f"👤 Yeni abone: {isim(mesaj.get('from', {}))}")
        elif komut == "/stop" and kid in aboneler:
            aboneler.remove(kid)
            mesaj_gonder(kid, "👋 Abonelik bitti. Tekrar gelmek istersen /start yaz.")
            mesaj_gonder(sahipler(), f"🚪 Ayrıldı: {isim(mesaj.get('from', {}))}")


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
        "Bu numarayı GitHub'da CHAT_ID adlı secret olarak ekleyin. "
        "Sonra mesajlar otomatik başlayacak.",
    )
    print(f"CHAT_ID bulundu ve Telegram'a gönderildi: {cid}")


def yorum_sec(durum, tur, liste):
    """Desteden karışık sırayla yorum çeker; deste bitince yeniden karıştırır."""
    anahtar = f"{tur}_deste"
    deste = [i for i in durum.get(anahtar, []) if 0 <= i < len(liste)]
    if not deste:
        deste = list(range(len(liste)))
        random.shuffle(deste)
        son = durum.get(f"{tur}_son")
        if son is not None and len(deste) > 1 and deste[0] == son:
            deste.append(deste.pop(0))  # art arda aynısı gelmesin
    secilen = deste.pop(0)
    durum[anahtar] = deste
    durum[f"{tur}_son"] = secilen
    return liste[secilen]


def yukle():
    if os.path.exists(DOSYA):
        with open(DOSYA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def kaydet(durum):
    with open(DOSYA, "w", encoding="utf-8") as f:
        json.dump(durum, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN secret'ı eksik.")
        sys.exit(1)
    if not CHAT_ID:
        chat_id_bul()
        return
    try:
        maas = float(MAAS_RUB)
    except ValueError:
        print("MAAS_RUB secret'ı eksik veya hatalı (örnek: 144000).")
        sys.exit(1)

    durum = yukle()
    kur = kur_al()
    deger = maas * kur
    zaman = simdi()
    print(f"{zaman:%d.%m.%Y %H:%M} | 1 RUB = {kur:.5f} TL")

    satirlar = [f"💰 Maaşın: {binlik(deger)} TL"]

    onceki_kur = durum.get("onceki_kur")
    if onceki_kur:
        fark = round(deger - maas * onceki_kur)
        if fark >= 1:
            satirlar.append(f"📈 +{binlik(fark)} TL arttı")
            satirlar.append(f"💬 {yorum_sec(durum, 'iyi', IYI_YORUMLAR)}")
        elif fark <= -1:
            satirlar.append(f"📉 -{binlik(abs(fark))} TL düştü")
            satirlar.append(f"💬 {yorum_sec(durum, 'kotu', KOTU_YORUMLAR)}")
        else:
            satirlar.append("➖ Değişmedi")
    else:
        satirlar.append("✅ Takip başladı, 10 dakikada bir yazacağım.")

    satirlar.append(f"🕒 {zaman:%H:%M} • 1 RUB = {kur:.4f} TL")

    abone_isle(durum)
    aboneler = durum.get("aboneler", [])
    alicilar = sahipler() + [a for a in aboneler if a not in sahipler()]
    basarili, engelleyenler = mesaj_gonder(alicilar, "\n".join(satirlar))

    # Botu engelleyen aboneleri listeden çıkar
    for kisi in engelleyenler:
        if kisi in aboneler:
            aboneler.remove(kisi)

    durum["onceki_kur"] = kur
    kaydet(durum)
    if basarili == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()


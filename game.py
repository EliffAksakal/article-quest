import random
import secrets
import time

from content import ASAMALAR, ITEMS, ITEMS_BY_ID, MAKALE, ROLLER, ROL_GOREV

MAX_OYUNCU = 200
TAKIM_STILLERI = [
    {"ad": "Kırmızı Takım", "ikon": "", "renk": "#D93A26"},
    {"ad": "Mavi Takım", "ikon": "", "renk": "#2448C9"},
]
CASE_SURELERI = {"bireysel": 30, "tartisma": 45, "takim": 30}
FINAL_SURELERI = {"bireysel": 35, "tartisma": 50, "takim": 30}


class GameError(Exception):
    pass


def takim_boyutlari(n):
    if n <= 0:
        return []
    if n == 1:
        return [1]
    return [n - n // 2, n // 2]


def rolleri_dagit(uye_idleri, tur_no):
    n = len(uye_idleri)
    sonuc = {u: [] for u in uye_idleri}
    if n == 0:
        return sonuc
    for j, rol in enumerate(ROLLER):
        sonuc[uye_idleri[(j + tur_no) % n]].append(rol)
    return sonuc


def soru_sekli(step_item):
    if step_item.get("tur") == "scene":
        return step_item["soru"]
    return step_item


def dogruluk(soru, cevap):
    tur = soru["tur"]
    try:
        if tur in ("mc", "tf"):
            return 1.0 if int(cevap) == soru["dogru"] else 0.0
        if tur == "multi" or (tur == "case" and soru.get("coklu")):
            return 1.0 if sorted(set(int(x) for x in cevap)) == sorted(soru["dogru"]) else 0.0
        if tur == "case":
            return 1.0 if int(cevap) == soru["dogru"] else 0.0
        if tur == "match":
            n = len(soru["sol"])
            if not isinstance(cevap, list) or len(cevap) != n:
                return 0.0
            return sum(1 for i, c in enumerate(cevap) if c is not None and int(c) == i) / n
        if tur == "order":
            n = len(soru["ogeler"])
            if not isinstance(cevap, list) or len(cevap) != n or sorted(int(x) for x in cevap) != list(range(n)):
                return 0.0
            return sum(1 for i, c in enumerate(cevap) if int(c) == i) / n
    except (TypeError, ValueError):
        return 0.0
    return 0.0


def cevap_temizle(soru, cevap):
    tur = soru["tur"]
    try:
        if tur in ("mc", "tf") or (tur == "case" and not soru.get("coklu")):
            i = int(cevap)
            if isinstance(cevap, bool) or not 0 <= i < len(soru["secenekler"]):
                raise ValueError
            return i
        if tur == "case" and soru.get("coklu"):
            secim = sorted(set(int(x) for x in cevap))
            if not secim or any(not 0 <= x < len(soru["secenekler"]) for x in secim):
                raise ValueError
            return secim
        if tur in ("match", "order"):
            n = len(soru["sol"] if tur == "match" else soru["ogeler"])
            if not isinstance(cevap, list) or len(cevap) != n:
                raise ValueError
            return [None if (x is None and tur == "match") else int(x) for x in cevap]
    except (TypeError, ValueError):
        pass
    raise GameError("Geçersiz cevap.")


def akis_olustur(kisa_mod=False, ekler=()):
    ekler = set(ekler)
    secili = []
    for item in ITEMS:
        if item["havuz"] == "ana":
            if kisa_mod and not item.get("kisa_modda", True):
                continue
            secili.append(item)
        elif item["id"] in ekler:
            secili.append(item)
    akis = []
    for asama_id, baslik, aciklama in ASAMALAR:
        parca = [i for i in secili if i["asama"] == asama_id]
        if not parca:
            continue
        akis.append({"tip": "giris", "asama": asama_id, "baslik": baslik, "aciklama": aciklama})
        for item in parca:
            if item["tur"] == "scene":
                akis.append({"tip": "sahne", "asama": asama_id, "item": item["id"]})
                akis.append({"tip": "soru", "asama": asama_id, "item": item["id"], "sahne_sorusu": True})
            elif item["tur"] == "case":
                akis.append({"tip": "vaka", "asama": asama_id, "item": item["id"]})
            else:
                akis.append({"tip": "soru", "asama": asama_id, "item": item["id"]})
        if asama_id in ("bilgi", "vaka"):
            akis.append({"tip": "tablo", "asama": asama_id})
    akis.append({"tip": "sonuc", "asama": "sonuc"})
    for i, s in enumerate(akis):
        s["no"] = i
    return akis


def akistaki_itemler(akis):
    gorulen = []
    for s in akis:
        if "item" in s and s["item"] not in gorulen:
            gorulen.append(s["item"])
    return gorulen


class Oturum:
    def __init__(self, pin=None, rng=None):
        self.pin = pin or "".join(secrets.choice("0123456789") for _ in range(6))
        self.host_token = secrets.token_urlsafe(24)
        self.makale_id = MAKALE["id"]
        self.rng = rng or random.Random()
        self.oyuncular = {}
        self.sira = []
        self.takimlar = []
        self.faz = "lobi"
        self.kisa_mod = False
        self.ekler = set()
        self.onayli = {i["id"] for i in ITEMS}
        self.akis = []
        self.adim = 0
        self.alt = None
        self.bitis = None
        self.basla = None
        self.bireysel = {}
        self.takim_cevap = {}
        self.oyuncu_puan = {}
        self.oyuncu_hiz = {}
        self.takim_bonus = {}
        self.son_kazanc = {}
        self.vaka_sayac = 0
        self.olusturma = time.time()

    def katil(self, ad, token=None):
        ad = (ad or "").strip()
        if token:
            for p in self.oyuncular.values():
                if secrets.compare_digest(p["token"], token):
                    return p
        if self.faz not in ("lobi", "takimlar"):
            raise GameError("Oyun başladı, yeni katılım kapalı.")
        if not 1 <= len(ad) <= 20:
            raise GameError("Takma ad 1–20 karakter olmalı.")
        if any(p["ad"].casefold() == ad.casefold() for p in self.oyuncular.values()):
            raise GameError("Bu takma ad alınmış, başka bir tane dene.")
        if len(self.oyuncular) >= MAX_OYUNCU:
            raise GameError("Oturum dolu.")
        pid = secrets.token_hex(4)
        p = {"id": pid, "ad": ad, "token": secrets.token_urlsafe(18), "takim": None, "bagli": True}
        self.oyuncular[pid] = p
        self.sira.append(pid)
        self.oyuncu_puan[pid] = 0
        self.oyuncu_hiz[pid] = 0
        if self.faz == "takimlar":
            if len(self.takimlar) < 2:
                self.takim_kur()
            else:
                hedef = min(self.takimlar, key=lambda t: len(t["uyeler"]))
                hedef["uyeler"].append(pid)
                p["takim"] = hedef["id"]
        return p

    def yeniden_baglan(self, pid, token):
        p = self.oyuncular.get(pid)
        if not p or not token or not secrets.compare_digest(p["token"], token):
            raise GameError("Oturum bulunamadı, yeniden katıl.")
        p["bagli"] = True
        return p

    def baglanti(self, pid, durum):
        if pid in self.oyuncular:
            self.oyuncular[pid]["bagli"] = durum

    def oyuncu_cikar(self, pid):
        if self.faz not in ("lobi", "takimlar") or pid not in self.oyuncular:
            raise GameError("Oyuncu yalnızca oyun başlamadan çıkarılabilir.")
        del self.oyuncular[pid]
        self.sira.remove(pid)
        self.oyuncu_puan.pop(pid, None)
        self.oyuncu_hiz.pop(pid, None)
        if self.faz == "takimlar":
            self.takim_kur()

    def takim_kur(self):
        if self.faz not in ("lobi", "takimlar"):
            raise GameError("Takımlar yalnızca oyun başlamadan kurulabilir.")
        ids = list(self.sira)
        if not ids:
            raise GameError("Takım kurmak için en az bir katılımcı gerekli.")
        self.rng.shuffle(ids)
        stiller = list(TAKIM_STILLERI)
        self.rng.shuffle(stiller)
        self.takimlar = []
        i = 0
        for t, boyut in enumerate(takim_boyutlari(len(ids))):
            uyeler = ids[i:i + boyut]
            i += boyut
            stil = stiller[t]
            self.takimlar.append({"id": f"t{t}", "ad": stil["ad"], "ikon": stil["ikon"], "renk": stil["renk"], "uyeler": uyeler})
            for u in uyeler:
                self.oyuncular[u]["takim"] = f"t{t}"
        self.takim_bonus = {t["id"]: 0 for t in self.takimlar}
        self.faz = "takimlar"

    def lobiye_don(self):
        if self.faz != "takimlar":
            raise GameError("Yalnızca takım ekranından lobiye dönülebilir.")
        self.takimlar = []
        for p in self.oyuncular.values():
            p["takim"] = None
        self.faz = "lobi"

    def onay(self, item_id, deger):
        if item_id not in ITEMS_BY_ID:
            raise GameError("Bilinmeyen içerik.")
        (self.onayli.add if deger else self.onayli.discard)(item_id)

    def hepsini_onayla(self):
        for i in akistaki_itemler(akis_olustur(self.kisa_mod, self.ekler)):
            self.onayli.add(i)

    def ek(self, item_id, deger):
        item = ITEMS_BY_ID.get(item_id)
        if not item or item["havuz"] != "yedek":
            raise GameError("Yalnızca yedek havuzdaki içerik eklenebilir.")
        if self.faz == "oyun":
            raise GameError("Akış oyun sırasında değiştirilemez.")
        (self.ekler.add if deger else self.ekler.discard)(item_id)

    def kisa(self, deger):
        if self.faz == "oyun":
            raise GameError("Akış oyun sırasında değiştirilemez.")
        self.kisa_mod = bool(deger)

    def onaysizlar(self):
        return [i for i in akistaki_itemler(akis_olustur(self.kisa_mod, self.ekler)) if i not in self.onayli]

    def baslat(self, simdi=None):
        if self.faz != "takimlar":
            raise GameError("Önce takımları oluştur.")
        eksik = self.onaysizlar()
        if eksik:
            raise GameError("Onaylanmamış içerik var: " + ", ".join(eksik))
        self.akis = akis_olustur(self.kisa_mod, self.ekler)
        self.faz = "oyun"
        self.adim = 0
        self._adima_gir(simdi)

    def adim_obj(self):
        if self.faz != "oyun" and self.faz != "bitti":
            return None
        return self.akis[self.adim]

    def _sure_ayarla(self, saniye, simdi):
        simdi = simdi if simdi is not None else time.time()
        self.basla = simdi
        self.bitis = simdi + saniye if saniye else None

    def _adima_gir(self, simdi=None):
        s = self.akis[self.adim]
        self.son_kazanc = {}
        if s["tip"] == "soru":
            soru = soru_sekli(ITEMS_BY_ID[s["item"]])
            self.alt = "acik"
            self._sure_ayarla(soru.get("sure", 20), simdi)
        elif s["tip"] == "vaka":
            item = ITEMS_BY_ID[s["item"]]
            s["tur_no"] = self.vaka_sayac
            self.vaka_sayac += 1
            self.alt = "bireysel"
            self._sure_ayarla(self._vaka_sure(item, "bireysel"), simdi)
        else:
            self.alt = None
            self._sure_ayarla(None, simdi)
        if s["tip"] == "sonuc":
            self.faz = "bitti"

    def _vaka_sure(self, item, alt):
        return (FINAL_SURELERI if item["asama"] == "final" else CASE_SURELERI)[alt]

    def ilerle(self, simdi=None):
        if self.faz not in ("oyun",):
            raise GameError("Oyun aktif değil.")
        s = self.akis[self.adim]
        if s["tip"] == "soru" and self.alt == "acik":
            self._soru_puanla(s)
            self.alt = "sonuc"
            self._sure_ayarla(None, simdi)
            return
        if s["tip"] == "vaka" and self.alt != "sonuc":
            item = ITEMS_BY_ID[s["item"]]
            sira = ["bireysel", "tartisma", "takim", "sonuc"]
            yeni = sira[sira.index(self.alt) + 1]
            if self.alt == "bireysel":
                self._vaka_bireysel_puanla(s)
            if yeni == "sonuc":
                self._vaka_takim_puanla(s)
                self._sure_ayarla(None, simdi)
            else:
                self._sure_ayarla(self._vaka_sure(item, yeni), simdi)
            self.alt = yeni
            return
        if self.adim < len(self.akis) - 1:
            self.adim += 1
            self._adima_gir(simdi)

    def tik(self, simdi=None):
        simdi = simdi if simdi is not None else time.time()
        if self.faz == "oyun" and self.bitis and simdi >= self.bitis:
            self.ilerle(simdi)
            return True
        if self.faz == "oyun" and self.alt in ("acik", "bireysel") and self._herkes_cevapladi():
            self.ilerle(simdi)
            return True
        if self.faz == "oyun" and self.alt == "takim" and self._tum_takimlar_gonderdi():
            self.ilerle(simdi)
            return True
        return False

    def _aktif_oyuncular(self):
        return [p for p in self.oyuncular.values() if p["takim"]]

    def _herkes_cevapladi(self):
        s = self.akis[self.adim]
        aktif = [p for p in self._aktif_oyuncular() if p["bagli"]]
        return bool(aktif) and all((s["no"], p["id"]) in self.bireysel for p in aktif)

    def _tum_takimlar_gonderdi(self):
        s = self.akis[self.adim]
        for t in self.takimlar:
            k = self.takim_cevap.get((s["no"], t["id"]))
            if not k or k.get("cevap") is None or k.get("gerekce") is None:
                return False
        return bool(self.takimlar)

    def roller(self, takim, tur_no):
        return rolleri_dagit(takim["uyeler"], tur_no)

    def _yetkili(self, pid, rol):
        p = self.oyuncular[pid]
        takim = self._takim(p["takim"])
        s = self.akis[self.adim]
        roller = self.roller(takim, s.get("tur_no", 0))
        if rol in roller.get(pid, []):
            return True
        sahip = [u for u, r in roller.items() if rol in r]
        return bool(sahip) and not any(self.oyuncular[u]["bagli"] for u in sahip)

    def _takim(self, tid):
        for t in self.takimlar:
            if t["id"] == tid:
                return t
        return None

    def cevap(self, pid, cevap, simdi=None):
        simdi = simdi if simdi is not None else time.time()
        if self.faz != "oyun" or pid not in self.oyuncular or not self.oyuncular[pid]["takim"]:
            raise GameError("Şu an cevap verilemez.")
        s = self.akis[self.adim]
        if not ((s["tip"] == "soru" and self.alt == "acik") or (s["tip"] == "vaka" and self.alt == "bireysel")):
            raise GameError("Bu soru için cevap süresi kapandı.")
        anahtar = (s["no"], pid)
        if anahtar in self.bireysel:
            raise GameError("Cevabın zaten kaydedildi.")
        item = ITEMS_BY_ID[s["item"]]
        cevap = cevap_temizle(soru_sekli(item) if s["tip"] == "soru" else item, cevap)
        self.bireysel[anahtar] = {"cevap": cevap, "t": simdi - (self.basla or simdi)}
        return True

    def takim_gonder(self, pid, cevap=None, gerekce=None):
        if self.faz != "oyun" or pid not in self.oyuncular:
            raise GameError("Şu an gönderilemez.")
        s = self.akis[self.adim]
        if s["tip"] != "vaka" or self.alt != "takim":
            raise GameError("Takım cevabı şu an açık değil.")
        tid = self.oyuncular[pid]["takim"]
        item = ITEMS_BY_ID[s["item"]]
        if cevap is not None:
            cevap = cevap_temizle(item, cevap)
        if gerekce is not None:
            try:
                gerekce = int(gerekce)
            except (TypeError, ValueError):
                raise GameError("Geçersiz gerekçe.")
            if not 0 <= gerekce < len(item["gerekceler"]):
                raise GameError("Geçersiz gerekçe.")
        kayit = self.takim_cevap.setdefault((s["no"], tid), {"cevap": None, "gerekce": None, "cevap_veren": None, "gerekce_veren": None})
        if cevap is not None:
            if kayit["cevap"] is not None:
                raise GameError("Takım cevabı zaten gönderildi.")
            if not self._yetkili(pid, "Karar verici"):
                raise GameError("Takım cevabını karar verici gönderir.")
            kayit["cevap"] = cevap
            kayit["cevap_veren"] = pid
        if gerekce is not None:
            if kayit["gerekce"] is not None:
                raise GameError("Gerekçe zaten gönderildi.")
            if not self._yetkili(pid, "Gerekçelendirme sorumlusu"):
                raise GameError("Gerekçeyi gerekçelendirme sorumlusu seçer.")
            kayit["gerekce"] = gerekce
            kayit["gerekce_veren"] = pid
        return True

    def _kazan(self, pid, puan, hiz=0):
        self.oyuncu_puan[pid] = self.oyuncu_puan.get(pid, 0) + puan + hiz
        self.oyuncu_hiz[pid] = self.oyuncu_hiz.get(pid, 0) + hiz
        self.son_kazanc[pid] = self.son_kazanc.get(pid, 0) + puan + hiz

    def _soru_puanla(self, s):
        soru = soru_sekli(ITEMS_BY_ID[s["item"]])
        hizli = s["asama"] == "bilgi"
        sure = soru.get("sure", 20)
        for (no, pid), kayit in self.bireysel.items():
            if no != s["no"] or "puan" in kayit:
                continue
            f = dogruluk(soru, kayit["cevap"])
            puan = round(100 * f)
            hiz = round(50 * max(0.0, 1 - kayit["t"] / sure)) if hizli and f == 1.0 else 0
            kayit.update({"dogruluk": f, "puan": puan, "hiz": hiz})
            self._kazan(pid, puan, hiz)

    def _vaka_bireysel_puanla(self, s):
        item = ITEMS_BY_ID[s["item"]]
        carpan = item.get("carpan", 1)
        for (no, pid), kayit in self.bireysel.items():
            if no != s["no"] or "puan" in kayit:
                continue
            f = dogruluk(item, kayit["cevap"])
            puan = round(100 * f) * carpan
            kayit.update({"dogruluk": f, "puan": puan, "hiz": 0})
            self._kazan(pid, puan)

    def _vaka_takim_puanla(self, s):
        item = ITEMS_BY_ID[s["item"]]
        carpan = item.get("carpan", 1)
        for t in self.takimlar:
            kayit = self.takim_cevap.setdefault((s["no"], t["id"]), {"cevap": None, "gerekce": None, "cevap_veren": None, "gerekce_veren": None})
            puan = 0
            kayit["dogru"] = kayit["cevap"] is not None and dogruluk(item, kayit["cevap"]) == 1.0
            kayit["gerekce_dogru"] = kayit["gerekce"] is not None and kayit["gerekce"] == item["dogru_gerekce"]
            kayit["tam_katilim"] = all((s["no"], u) in self.bireysel for u in t["uyeler"])
            if kayit["dogru"]:
                puan += 200
            if kayit["gerekce_dogru"]:
                puan += 100
            if kayit["tam_katilim"]:
                puan += 50
            kayit["puan"] = puan * carpan
            self.takim_bonus[t["id"]] = self.takim_bonus.get(t["id"], 0) + kayit["puan"]

    def takim_puani(self, takim):
        uyeler = takim["uyeler"]
        ort = sum(self.oyuncu_puan.get(u, 0) for u in uyeler) / len(uyeler) if uyeler else 0
        return round(ort + self.takim_bonus.get(takim["id"], 0))

    def siralama(self):
        liste = [{"id": t["id"], "ad": t["ad"], "ikon": t["ikon"], "renk": t["renk"], "puan": self.takim_puani(t), "boyut": len(t["uyeler"])} for t in self.takimlar]
        liste.sort(key=lambda x: -x["puan"])
        for x in liste:
            x["sira"] = 1 + sum(1 for y in liste if y["puan"] > x["puan"])
        return liste

    def rozetler(self):
        if not self.takimlar:
            return {}
        vaka_adimlari = [s for s in self.akis if s["tip"] == "vaka"]
        sonuc = {t["id"]: [] for t in self.takimlar}
        for t in self.takimlar:
            kayitlar = [self.takim_cevap.get((s["no"], t["id"]), {}) for s in vaka_adimlari]
            if vaka_adimlari and all(k.get("tam_katilim") for k in kayitlar):
                sonuc[t["id"]].append({"ad": "Tam kadro", "neden": "Her vakada tüm üyeler bireysel karar verdi."})
            if vaka_adimlari and all(k.get("dogru") for k in kayitlar):
                sonuc[t["id"]].append({"ad": "Kusursuz vaka", "neden": "Bütün takım kararları doğruydu."})
        gerekce = {t["id"]: sum(1 for s in vaka_adimlari if self.takim_cevap.get((s["no"], t["id"]), {}).get("gerekce_dogru")) for t in self.takimlar}
        en = max(gerekce.values()) if gerekce else 0
        if en > 0:
            for tid, v in gerekce.items():
                if v == en:
                    sonuc[tid].append({"ad": "Gerekçe ustası", "neden": f"{v} doğru gerekçe."})
        hiz = {t["id"]: sum(self.oyuncu_hiz.get(u, 0) for u in t["uyeler"]) / max(1, len(t["uyeler"])) for t in self.takimlar}
        en = max(hiz.values()) if hiz else 0
        if en > 0:
            for tid, v in hiz.items():
                if v == en:
                    sonuc[tid].append({"ad": "Şimşek", "neden": "En yüksek ortalama hız bonusu."})
        return sonuc

    def ogrenilenler(self):
        kavramlar = []
        for i in akistaki_itemler(self.akis):
            k = ITEMS_BY_ID[i]["kavram"]
            if k not in kavramlar:
                kavramlar.append(k)
        return kavramlar

    def _kalan(self, simdi):
        if not self.bitis:
            return None
        return max(0.0, self.bitis - simdi)

    def _gosterim_item(self, s, acik_cevap):
        item = ITEMS_BY_ID[s["item"]]
        if s["tip"] == "sahne":
            return {k: item[k] for k in ("id", "baslik", "metin", "gorsel", "gorsel_altyazi", "cikarim", "kaynak", "kavram")}
        soru = soru_sekli(item) if s["tip"] == "soru" else item
        d = {"id": item["id"], "tur": soru["tur"], "metin": soru["metin"], "kaynak": item["kaynak"], "kavram": item["kavram"]}
        if soru.get("coklu"):
            d["coklu"] = True
        for k in ("sol", "etiket"):
            if k in soru:
                d[k] = soru[k]
        if "secenekler" in soru:
            sira = list(range(len(soru["secenekler"])))
            if soru["tur"] != "tf":
                random.Random(f"{self.pin}-{s['no']}-s").shuffle(sira)
            d["secenekler"] = [{"i": i, "metin": soru["secenekler"][i]} for i in sira]
        if "gerekceler" in soru:
            sira = list(range(len(soru["gerekceler"])))
            random.Random(f"{self.pin}-{s['no']}-g").shuffle(sira)
            d["gerekceler"] = [{"i": i, "metin": soru["gerekceler"][i]} for i in sira]
        if "sag" in soru:
            sira = list(range(len(soru["sag"])))
            random.Random(f"{self.pin}-{s['no']}").shuffle(sira)
            d["sag"] = [{"i": i, "metin": soru["sag"][i]} for i in sira]
        if "ogeler" in soru:
            sira = list(range(len(soru["ogeler"])))
            r = random.Random(f"{self.pin}-{s['no']}")
            while sira == sorted(sira):
                r.shuffle(sira)
            d["ogeler"] = [{"i": i, "metin": soru["ogeler"][i]} for i in sira]
        if acik_cevap:
            d["aciklama"] = soru["aciklama"]
            d["celdirici"] = soru.get("celdirici", [])
            if "dogru" in soru:
                d["dogru"] = soru["dogru"]
            if "sag" in soru:
                d["eslesme"] = soru["sag"]
            if "ogeler" in soru:
                d["dogru_sira"] = soru["ogeler"]
            if "dogru_gerekce" in soru:
                d["dogru_gerekce"] = soru["dogru_gerekce"]
                d["gerekce_notlari"] = soru.get("gerekce_notlari", [])
        return d

    def _dagilim(self, s):
        dag = {}
        oranlar = []
        for (no, pid), k in self.bireysel.items():
            if no != s["no"]:
                continue
            c = k["cevap"]
            if isinstance(c, list):
                if "dogruluk" in k:
                    oranlar.append(k["dogruluk"])
                item = ITEMS_BY_ID[s["item"]]
                if item.get("coklu"):
                    for x in c:
                        dag[str(x)] = dag.get(str(x), 0) + 1
            else:
                dag[str(c)] = dag.get(str(c), 0) + 1
        if oranlar:
            dag["ort"] = round(sum(oranlar) / len(oranlar), 2)
        return dag

    def _acik_mi(self, s):
        return (s["tip"] == "soru" and self.alt == "sonuc") or (s["tip"] == "vaka" and self.alt == "sonuc")

    def host_gorunum(self, simdi=None):
        simdi = simdi if simdi is not None else time.time()
        v = {
            "pin": self.pin, "faz": self.faz, "kisa_mod": self.kisa_mod, "makale": MAKALE,
            "oyuncular": [{"id": p["id"], "ad": p["ad"], "takim": p["takim"], "bagli": p["bagli"]} for p in (self.oyuncular[i] for i in self.sira)],
            "takimlar": self.takimlar, "max": MAX_OYUNCU,
        }
        if self.faz in ("lobi", "takimlar"):
            akis = akis_olustur(self.kisa_mod, self.ekler)
            v["icerik"] = [dict(i, onayli=i["id"] in self.onayli, ekli=i["id"] in self.ekler, akista=i["id"] in akistaki_itemler(akis)) for i in ITEMS]
            v["onaysiz"] = self.onaysizlar()
            v["akis_ozet"] = [{"tip": s["tip"], "item": s.get("item"), "baslik": s.get("baslik")} for s in akis]
        if self.faz in ("oyun", "bitti"):
            s = self.akis[self.adim]
            v["adim"] = {"no": s["no"], "tip": s["tip"], "asama": s["asama"], "toplam": len(self.akis), "alt": self.alt, "kalan": self._kalan(simdi), "sure": (self.bitis - self.basla) if self.bitis else None}
            if s["tip"] == "giris":
                v["adim"].update(baslik=s["baslik"], aciklama=s["aciklama"])
            if "item" in s:
                v["adim"]["item"] = self._gosterim_item(s, self._acik_mi(s))
                cevaplayan = [pid for (no, pid) in self.bireysel if no == s["no"]]
                v["adim"]["cevaplayan"] = len(cevaplayan)
                v["adim"]["aktif"] = len(self._aktif_oyuncular())
                if self._acik_mi(s) or self.alt in ("tartisma", "takim"):
                    v["adim"]["dagilim"] = self._dagilim(s)
            if s["tip"] == "vaka":
                v["adim"]["takimlar"] = []
                for t in self.takimlar:
                    k = self.takim_cevap.get((s["no"], t["id"]), {})
                    td = {"id": t["id"], "cevap_geldi": k.get("cevap") is not None, "gerekce_geldi": k.get("gerekce") is not None,
                          "bireysel": sum(1 for u in t["uyeler"] if (s["no"], u) in self.bireysel), "boyut": len(t["uyeler"])}
                    if self.alt == "sonuc":
                        td.update({"cevap": k.get("cevap"), "gerekce": k.get("gerekce"), "dogru": k.get("dogru"), "gerekce_dogru": k.get("gerekce_dogru"), "tam_katilim": k.get("tam_katilim"), "puan": k.get("puan", 0)})
                    v["adim"]["takimlar"].append(td)
            v["siralama"] = self.siralama()
            if self.faz == "bitti":
                v["rozetler"] = self.rozetler()
                v["ogrenilenler"] = self.ogrenilenler()
                v["bireysel_siralama"] = sorted(({"ad": self.oyuncular[p]["ad"], "puan": self.oyuncu_puan.get(p, 0), "takim": self.oyuncular[p]["takim"]} for p in self.sira), key=lambda x: -x["puan"])
        return v

    def oyuncu_gorunum(self, pid, simdi=None):
        simdi = simdi if simdi is not None else time.time()
        p = self.oyuncular.get(pid)
        if not p:
            return {"faz": "yok"}
        v = {"faz": self.faz, "ben": {"id": pid, "ad": p["ad"], "puan": self.oyuncu_puan.get(pid, 0)}, "pin": self.pin}
        takim = self._takim(p["takim"]) if p["takim"] else None
        if takim:
            v["takim"] = {"id": takim["id"], "ad": takim["ad"], "ikon": takim["ikon"], "renk": takim["renk"],
                          "uyeler": [{"id": u, "ad": self.oyuncular[u]["ad"], "bagli": self.oyuncular[u]["bagli"]} for u in takim["uyeler"]],
                          "puan": self.takim_puani(takim)}
        if self.faz in ("oyun", "bitti"):
            s = self.akis[self.adim]
            a = {"no": s["no"], "tip": s["tip"], "asama": s["asama"], "toplam": len(self.akis), "alt": self.alt, "kalan": self._kalan(simdi), "sure": (self.bitis - self.basla) if self.bitis else None}
            if s["tip"] == "giris":
                a.update(baslik=s["baslik"], aciklama=s["aciklama"])
            if "item" in s:
                a["item"] = self._gosterim_item(s, self._acik_mi(s))
                k = self.bireysel.get((s["no"], pid))
                if k:
                    a["benim"] = {"cevap": k["cevap"], "puan": k.get("puan"), "hiz": k.get("hiz"), "dogruluk": k.get("dogruluk")}
                a["kazanc"] = self.son_kazanc.get(pid, 0)
            if s["tip"] == "vaka" and takim:
                roller = self.roller(takim, s.get("tur_no", 0))
                a["roller"] = {u: r for u, r in roller.items()}
                a["gorevim"] = [{"rol": r, "gorev": ROL_GOREV[r]} for r in roller.get(pid, [])]
                a["karar_yetkim"] = self._yetkili(pid, "Karar verici")
                a["gerekce_yetkim"] = self._yetkili(pid, "Gerekçelendirme sorumlusu")
                if self.alt in ("tartisma", "takim", "sonuc"):
                    a["takim_oylari"] = [{"ad": self.oyuncular[u]["ad"], "cevap": self.bireysel.get((s["no"], u), {}).get("cevap")} for u in takim["uyeler"]]
                tk = self.takim_cevap.get((s["no"], takim["id"]), {})
                a["takim_cevap"] = {k2: tk.get(k2) for k2 in ("cevap", "gerekce", "dogru", "gerekce_dogru", "tam_katilim", "puan")}
            sira = self.siralama()
            if takim:
                for x in sira:
                    if x["id"] == takim["id"]:
                        a["takim_sirasi"] = x["sira"]
                a["takim_sayisi"] = len(sira)
            if self.faz == "bitti" and takim:
                a["rozetler"] = self.rozetler().get(takim["id"], [])
                a["ogrenilenler"] = self.ogrenilenler()
            v["adim"] = a
        return v

    def disa_aktar_satirlar(self):
        satirlar = [["kayit", "adim", "icerik", "takim", "oyuncu", "cevap", "gerekce", "dogruluk", "puan", "hiz_bonusu", "sure_sn"]]
        for (no, pid), k in sorted(self.bireysel.items(), key=lambda x: (x[0][0], x[0][1])):
            s = self.akis[no]
            p = self.oyuncular.get(pid, {})
            satirlar.append(["bireysel", no, s.get("item"), p.get("takim"), p.get("ad"), k["cevap"], "", k.get("dogruluk"), k.get("puan"), k.get("hiz"), round(k["t"], 2)])
        for (no, tid), k in sorted(self.takim_cevap.items()):
            s = self.akis[no]
            satirlar.append(["takim", no, s.get("item"), tid, self.oyuncular.get(k.get("cevap_veren"), {}).get("ad", ""), k.get("cevap"), k.get("gerekce"), 1 if k.get("dogru") else 0, k.get("puan"), "", ""])
        for x in self.siralama():
            satirlar.append(["takim_skor", "", "", x["ad"], "", "", "", "", x["puan"], "", ""])
        return satirlar

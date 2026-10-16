import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from content import ITEMS, ITEMS_BY_ID  # noqa: E402
from game import GameError, Oturum, akis_olustur, akistaki_itemler, dogruluk, rolleri_dagit, takim_boyutlari  # noqa: E402


@pytest.mark.parametrize("n,beklenen", [(1, [1]), (2, [1, 1]), (3, [2, 1]), (4, [2, 2]), (7, [4, 3]), (15, [8, 7]), (40, [20, 20])])
def test_her_zaman_iki_takim(n, beklenen):
    assert takim_boyutlari(n) == beklenen


@pytest.mark.parametrize("n", range(2, 60))
def test_dengeli_dagilim(n):
    b = takim_boyutlari(n)
    assert len(b) == 2 and sum(b) == n and max(b) - min(b) <= 1


def oturum_kur(n, kisa=False):
    o = Oturum(pin="123456", rng=random.Random(1))
    for i in range(n):
        o.katil(f"Oyuncu{i}")
    o.kisa(kisa)
    o.takim_kur()
    o.hepsini_onayla()
    o.baslat(simdi=0)
    return o


def test_kapasite_ve_mukerrer():
    o = Oturum(pin="1")
    for i in range(40):
        o.katil(f"k{i}")
    assert len(o.oyuncular) == 40
    o2 = Oturum(pin="2")
    o2.katil("Ali")
    with pytest.raises(GameError):
        o2.katil("ali")


def test_yeniden_baglanma_token_ile():
    o = Oturum(pin="3")
    p = o.katil("Ece")
    o.baglanti(p["id"], False)
    assert o.yeniden_baglan(p["id"], p["token"])["bagli"]
    o.takim_kur()
    assert o.katil("", token=p["token"])["id"] == p["id"]
    yeni = o.katil("Yeni")
    assert yeni["takim"] is not None and len(o.takimlar) == 2
    o.baslat()
    with pytest.raises(GameError):
        o.katil("Geç")


def test_onaysiz_icerikle_baslamaz():
    o = Oturum(pin="4")
    o.katil("a")
    o.katil("b")
    o.takim_kur()
    for i in ITEMS:
        o.onay(i["id"], False)
    with pytest.raises(GameError):
        o.baslat()


def test_tek_cevap_kaydi():
    o = oturum_kur(4)
    while o.akis[o.adim]["tip"] != "soru":
        o.ilerle(simdi=0)
    pid = o.sira[0]
    o.cevap(pid, 0, simdi=1)
    with pytest.raises(GameError):
        o.cevap(pid, 1, simdi=2)


def test_roller_karar_ve_gerekce_farkli_kisilerde():
    for n in (2, 3):
        for tur in range(4):
            r = rolleri_dagit([f"u{i}" for i in range(n)], tur)
            kv = [u for u, x in r.items() if "Karar verici" in x]
            gs = [u for u, x in r.items() if "Gerekçelendirme sorumlusu" in x]
            assert len(kv) == 1 and len(gs) == 1 and kv != gs
            assert all(r[u] for u in r)


def test_roller_her_vakada_doner():
    a = rolleri_dagit(["u0", "u1", "u2"], 0)
    b = rolleri_dagit(["u0", "u1", "u2"], 1)
    assert a != b


def test_dogruluk_turleri():
    assert dogruluk(ITEMS_BY_ID["B1"], 0) == 1.0
    assert dogruluk(ITEMS_BY_ID["B1"], 2) == 0.0
    assert dogruluk(ITEMS_BY_ID["B6"], [0, 1, 3, 2]) == 0.5
    assert dogruluk(ITEMS_BY_ID["V3"], [1, 0]) == 1.0
    assert dogruluk(ITEMS_BY_ID["V3"], [0]) == 0.0
    assert dogruluk(ITEMS_BY_ID["B10"], [0, 1, 2, 3, 4, 5]) == 1.0
    assert dogruluk(ITEMS_BY_ID["B10"], [0, 0, 0, 0, 0, 0]) == 0.0


def test_kucuk_takim_dezavantajli_degil():
    o = oturum_kur(5)
    for p in o.sira:
        o.oyuncu_puan[p] = 100
    puanlar = {t["id"]: o.takim_puani(t) for t in o.takimlar}
    assert len(set(puanlar.values())) == 1


def test_tam_oyun_akisi_ve_puanlama():
    o = oturum_kur(7)
    t = 0
    while o.faz == "oyun":
        s = o.akis[o.adim]
        if s["tip"] == "soru" and o.alt == "acik":
            soru = ITEMS_BY_ID[s["item"]]
            soru = soru.get("soru", soru)
            for pid in o.sira:
                dogru = soru.get("dogru", list(range(len(soru.get("sol") or soru.get("ogeler") or []))))
                o.cevap(pid, dogru, simdi=t + 1)
        if s["tip"] == "vaka" and o.alt == "bireysel":
            item = ITEMS_BY_ID[s["item"]]
            for pid in o.sira:
                o.cevap(pid, item["dogru"], simdi=t + 1)
        if s["tip"] == "vaka" and o.alt == "takim":
            item = ITEMS_BY_ID[s["item"]]
            for takim in o.takimlar:
                r = o.roller(takim, s["tur_no"])
                kv = next(u for u, x in r.items() if "Karar verici" in x)
                gs = next(u for u, x in r.items() if "Gerekçelendirme sorumlusu" in x)
                o.takim_gonder(kv, cevap=item["dogru"])
                o.takim_gonder(gs, gerekce=item["dogru_gerekce"])
        o.ilerle(simdi=t + 2)
        t += 3
    assert o.faz == "bitti"
    sir = o.siralama()
    assert len({x["puan"] for x in sir}) == 1
    roz = o.rozetler()
    assert all(any(r["ad"] == "Kusursuz vaka" for r in v) for v in roz.values())
    assert len(o.disa_aktar_satirlar()) > 10


def test_final_iki_kat():
    o = oturum_kur(2)
    while not (o.akis[o.adim]["tip"] == "vaka" and o.akis[o.adim]["asama"] == "final"):
        o.ilerle(simdi=0)
    pid = o.sira[0]
    o.cevap(pid, ITEMS_BY_ID["F2"]["dogru"], simdi=1)
    once = o.oyuncu_puan[pid]
    o.ilerle(simdi=2)
    assert o.oyuncu_puan[pid] - once == 200


def test_sure_dolunca_kilitlenir():
    o = oturum_kur(2)
    while o.akis[o.adim]["tip"] != "soru":
        o.ilerle(simdi=0)
    assert o.tik(simdi=10_000)
    assert o.alt == "sonuc"
    with pytest.raises(GameError):
        o.cevap(o.sira[0], 0)


def test_karar_verici_cevrimdisiyse_yedek_uye_gonderebilir():
    o = oturum_kur(3)
    while not (o.akis[o.adim]["tip"] == "vaka"):
        o.ilerle(simdi=0)
    o.ilerle(simdi=1)
    o.ilerle(simdi=2)
    takim = o.takimlar[0]
    r = o.roller(takim, o.akis[o.adim]["tur_no"])
    kv = next(u for u, x in r.items() if "Karar verici" in x)
    diger = next(u for u in takim["uyeler"] if u != kv)
    with pytest.raises(GameError):
        o.takim_gonder(diger, cevap=1)
    o.baglanti(kv, False)
    assert o.takim_gonder(diger, cevap=1)


def test_kisa_mod_ve_ekler():
    ana = akistaki_itemler(akis_olustur())
    kisa = akistaki_itemler(akis_olustur(kisa_mod=True))
    ekli = akistaki_itemler(akis_olustur(ekler={"V2", "B3"}))
    assert ana == ["S3", "S5", "B1", "B2", "B6", "B5", "V1", "V3", "F2"]
    assert len(kisa) < len(ana) and "V3" not in kisa
    assert "V2" in ekli and "B3" in ekli


def test_her_icerigin_kaynagi_ve_aciklamasi_var():
    for item in ITEMS:
        assert item.get("kaynak") and item.get("hedef") and item.get("zorluk")
        soru = item.get("soru", item)
        assert soru.get("aciklama")
        if item["tur"] == "case":
            assert "Makaleden türetilmiş kurgu vaka" in item["etiket"] or "makale" in item["etiket"].lower()
            assert len(item["celdirici"]) == len(item["secenekler"])
        if "secenekler" in soru and soru["tur"] in ("mc", "tf", "case"):
            dogrular = soru["dogru"] if isinstance(soru["dogru"], list) else [soru["dogru"]]
            for i, n in enumerate(soru["celdirici"]):
                assert (n is None) == (i in dogrular), (item["id"], i)


def test_oyuncu_gorunumunde_cevap_sizmaz():
    o = oturum_kur(3)
    while o.akis[o.adim]["tip"] != "soru":
        o.ilerle(simdi=0)
    v = o.oyuncu_gorunum(o.sira[0], simdi=0)
    assert "dogru" not in v["adim"]["item"] and "aciklama" not in v["adim"]["item"]


def test_gecersiz_cevaplar_reddedilir():
    import pytest
    from game import Oturum, GameError
    o = Oturum(pin="999999")
    a = o.katil("A")
    o.takim_kur()
    o.hepsini_onayla()
    o.baslat(simdi=0)
    while o.akis[o.adim]["tip"] != "soru":
        o.ilerle(simdi=0)
    for kotu in ("x", 99, -1, True, {"a": 1}, None):
        with pytest.raises(GameError):
            o.cevap(a["id"], kotu, simdi=1)
    assert o.cevap(a["id"], 0, simdi=1)

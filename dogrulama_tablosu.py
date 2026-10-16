import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from content import ITEMS, MAKALE  # noqa: E402
from game import akis_olustur, akistaki_itemler  # noqa: E402

TUR = {"mc": "Çoktan seçmeli", "tf": "Doğru/Yanlış", "match": "Eşleştirme", "order": "Sıralama", "scene": "Sahne + mini soru", "case": "Vaka"}
HARF = "ABCDEF"


def hucre(s):
    return str(s).replace("|", "/").replace("\n", " ")


def dogru_cevap(item):
    s = item.get("soru", item)
    if "sol" in s:
        return "; ".join(f"{l} ↔ {r}" for l, r in zip(s["sol"], s["sag"]))
    if "ogeler" in s:
        return " → ".join(s["ogeler"])
    d = s["dogru"] if isinstance(s["dogru"], list) else [s["dogru"]]
    metin = " + ".join(f"{HARF[i]}) {s['secenekler'][i]}" for i in d)
    if "gerekceler" in s:
        metin += f" · Gerekçe: {s['gerekceler'][s['dogru_gerekce']]}"
    return metin


def main():
    ana = akistaki_itemler(akis_olustur())
    kisa = akistaki_itemler(akis_olustur(kisa_mod=True))
    satir = [f"# Kaynak doğrulama tablosu\n\n{MAKALE['kunye']}\n",
             "Bu tablo `content.py` dosyasından üretilir. İçerik değişince `python tools/dogrulama_tablosu.py` ile yeniden oluştur.\n",
             "## İçerik havuzu\n",
             "| ID | Akış | Tür | Kavram | Soru | Doğru cevap | Makaledeki kaynak | Öğrenme hedefi | Zorluk |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i in ITEMS:
        s = i.get("soru", i)
        akis = "Ana" + (" + kısa" if i["id"] in kisa else "") if i["id"] in ana else "Yedek"
        tur = TUR[i["tur"]] + (" (hata bulma)" if i.get("coklu") else "") + (" (final, 2×)" if i.get("carpan") == 2 else "")
        satir.append(f"| {i['id']} | {akis} | {tur} | {hucre(i['kavram'])} | {hucre(s['metin'])} | {hucre(dogru_cevap(i))} | {hucre(i['kaynak'])} | {hucre(i['hedef'])} | {i['zorluk']} |")
    satir.append("\n## Açıklamalar, çeldiriciler ve vaka etiketleri\n")
    for i in ITEMS:
        s = i.get("soru", i)
        satir.append(f"### {i['id']} · {i['kavram']}\n")
        if i.get("etiket"):
            satir.append(f"*{i['etiket']}*\n")
        if i["tur"] == "scene":
            satir.append(f"Sahne metni: {i['metin']} / {i['gorsel_altyazi']} / {i['cikarim']}\n")
        satir.append(f"Açıklama: {s['aciklama']}\n")
        if s.get("secenekler"):
            for k, n in enumerate(s.get("celdirici", [])):
                if n:
                    satir.append(f"- {HARF[k]}) {s['secenekler'][k]} — neden yanlış: {n}")
        if s.get("gerekceler"):
            for k, n in enumerate(s.get("gerekce_notlari", [])):
                if n:
                    satir.append(f"- Gerekçe {HARF[k]}) {s['gerekceler'][k]} — neden yanlış: {n}")
        satir.append("")
    satir.append("## Makaledeki tutarsızlıklar (soru üretilmedi)\n")
    for t in [
        "s.19: Etik beyan çelişkili; insan katılımcı olmadığı söylenip ardından katılımcılardan onam alındığı yazıyor.",
        "Bölüm 3.4 / Tablo 4: metin dört tematik alan diyor, tabloda üç alan var.",
        "Fullan ve ark. metinde 2024, kaynakçada 2023; atıf yılları sorulmadı.",
        "Bölüm 2.2.2 ile Şekil 1: 15 derlemeden 8'i / yalnızca 8; bu ayrıntı sorulmadı.",
        "Ahmed'in altı evresi numaralı ama makale doğrusal olmadığını vurguluyor; sıralama sorusu yapılmadı.",
        "Savunuculuk ağırlığı 3.2.2'de sınırlılık değil, 5. bölümde sınırlılık olarak geçiyor; D/Y sorusu yapılmadı.",
    ]:
        satir.append(f"- {t}")
    Path(__file__).resolve().parents[1].joinpath("KAYNAK_DOGRULAMA.md").write_text("\n".join(satir) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

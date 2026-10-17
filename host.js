const socket = io({ transports: ["websocket", "polling"] });
const app = document.getElementById("app");
let ses = depoAl("aq-host");
let durum = null;
let anahtar = null;
let cekmeceAcik = false;
let goruluOyuncu = new Set();
let oncekiSira = {};
let sahneZamanlayici = [];
let azHareket = !!depoAl("aq-az");
document.body.classList.toggle("az-hareket", azHareket);

const TUR_ADI = {
  mc: "Çoktan seçmeli", tf: "Doğru / Yanlış", match: "Kavram eşleştirme", order: "Sıralama",
  scene: "Animasyonlu sahne + mini soru", case: "Vaka (takım kararı)",
};
const ASAMA_ADI = { kural: "Nasıl oynanır?", kesif: "Kavramları Keşfet", bilgi: "Bilgi Yarışması", vaka: "Vaka Analizleri", final: "Final", sonuc: "Sonuçlar" };

function eylem(ad, veri) {
  if (ad === "baslat") return tanitimOynat(() => gonderEylem(ad, veri));
  gonderEylem(ad, veri);
}

function gonderEylem(ad, veri) {
  socket.emit("host:eylem", { eylem: ad, veri }, r => { if (r && !r.ok) bildir(r.hata); });
}

function tanitimOynat(sonra) {
  const kaynak = "/static/tanitim.mp4";
  fetch(kaynak, { method: "HEAD" }).then(r => {
    if (!r.ok) return sonra();
    const kat = document.createElement("div");
    kat.className = "tanitim";
    kat.innerHTML = `<video src="${kaynak}" playsinline autoplay></video><div class="tanitim-alt"><span>Makaleyi 30 saniyede tanıyalım</span><button class="btn" type="button">Videoyu geç</button></div>`;
    document.body.appendChild(kat);
    const video = kat.querySelector("video");
    let bitti = false;
    const kapat = () => { if (bitti) return; bitti = true; video.pause(); kat.remove(); sonra(); };
    video.addEventListener("ended", kapat);
    video.addEventListener("error", kapat);
    kat.querySelector("button").onclick = kapat;
    const oynat = video.play();
    if (oynat && oynat.catch) oynat.catch(() => { video.muted = true; video.play().catch(kapat); });
  }).catch(() => sonra());
}

socket.on("connect", () => {
  if (ses) {
    socket.emit("host:merhaba", ses, r => {
      if (!r || !r.ok) { depoSil("aq-host"); ses = null; acilisCiz(); }
    });
  } else {
    acilisCiz();
  }
});
socket.on("disconnect", () => bildir("Sunucu bağlantısı koptu, yeniden bağlanılıyor…"));
socket.on("durum", v => { durum = v; ciz(v); });

async function oturumAc() {
  const r = await fetch("/api/oturum", { method: "POST" });
  const d = await r.json();
  ses = { pin: d.pin, token: d.token, katilim: d.katilim, kisa: d.kisa };
  depoYaz("aq-host", ses);
  socket.emit("host:merhaba", ses, r2 => { if (!r2.ok) bildir(r2.hata); });
}

function yeniOturum() {
  if (durum && durum.faz === "oyun" && !confirm("Devam eden oyun kapanacak. Yeni oturum açılsın mı?")) return;
  depoSil("aq-host");
  ses = null;
  durum = null;
  anahtar = null;
  goruluOyuncu = new Set();
  oturumAc();
}

function ustCiz(v) {
  const oyun = v && (v.faz === "oyun" || v.faz === "bitti");
  const yuzde = oyun ? Math.round(((v.adim.no + 1) / v.adim.toplam) * 100) : 0;
  const mini = oyun && v.adim.tip !== "sonuc" && v.adim.tip !== "tablo"
    ? (v.siralama || []).map(t => `<span class="mini-takim" title="${esc(t.ad)}">${takimIkon(t, 18)}<b>${t.puan}</b></span>`).join("&ensp;") : "";
  return `
    ${oyun ? `<div class="ilerleme" aria-label="İlerleme"><span style="width:${yuzde}%"></span></div>` : `<div class="tayf-cizgi"></div>`}
    <div class="host-ust">
      <span class="marka">${logoSvg()}Prizma</span>
      <span class="asama-adi">${oyun ? esc(ASAMA_ADI[v.adim.asama] || "") : v ? "Ho (2026) · Etik YZ liderliği" : ""}</span>
      <span class="bosluk"></span>
      <span>${mini}</span>
      ${v ? `<span class="pin-kucuk">PIN ${esc(v.pin)}</span>` : ""}
      <button class="btn ikincil kucuk" id="az-btn" aria-pressed="${azHareket}">${azHareket ? "Animasyonlar azaltıldı" : "Animasyonları azalt"}</button>
    </div>`;
}

function sayfa(v, ana, alt) {
  app.innerHTML = `${ustCiz(v)}<main class="host-ana">${ana}</main>${alt ? `<footer class="host-alt">${alt}</footer>` : ""}`;
  document.getElementById("az-btn").onclick = () => {
    azHareket = !azHareket;
    depoYaz("aq-az", azHareket);
    document.body.classList.toggle("az-hareket", azHareket);
    const b = document.getElementById("az-btn");
    b.textContent = azHareket ? "Animasyonlar azaltıldı" : "Animasyonları azalt";
    b.setAttribute("aria-pressed", azHareket);
  };
  app.querySelectorAll("[data-eylem]").forEach(b => b.onclick = () => eylem(b.dataset.eylem));
  const yeni = document.getElementById("yeni-oturum");
  if (yeni) yeni.onclick = yeniOturum;
  const onay = document.getElementById("onay-ac");
  if (onay) onay.onclick = () => { cekmeceAcik = true; cekmeceCiz(); };
}

function acilisCiz() {
  sahneTemizle();
  sayfa(null, `
    <section class="acilis">
      <div>
        <div class="acilis-piramit">${prizmaSvg(420, "buyuk")}</div>
        <h1>Prizma</h1>
        <p class="acilis-slogan">Karar kimde?</p>
        <p>Yapay zekâ çağında okul müdürlüğü üzerine takım oyunu · Ho (2026)</p>
        <button class="btn buyuk" id="ac-btn">Oturum aç</button>
      </div>
    </section>`);
  document.getElementById("ac-btn").onclick = oturumAc;
}

function anahtarHesapla(v) {
  if (v.faz === "lobi") return "lobi";
  if (v.faz === "takimlar") return "takimlar|" + v.takimlar.map(t => t.uyeler.join(",")).join("|");
  return `${v.faz}|${v.adim.no}|${v.adim.alt}`;
}

function ciz(v) {
  const k = anahtarHesapla(v);
  if (k !== anahtar) {
    const onceki = anahtar;
    anahtar = k;
    tamCiz(v, onceki);
  } else {
    guncelle(v);
  }
  if (cekmeceAcik) cekmeceCiz();
}

function tamCiz(v, onceki) {
  sahneTemizle();
  if (v.faz === "lobi") return lobiCiz(v);
  if (v.faz === "takimlar") return takimCiz(v);
  const a = v.adim;
  if (a.tip === "kural") return kuralCiz(v);
  if (a.tip === "giris") return girisCiz(v);
  if (a.tip === "sahne") return sahneCiz(v);
  if (a.tip === "soru") return soruCiz(v);
  if (a.tip === "vaka") return vakaCiz(v);
  if (a.tip === "tablo") return tabloCiz(v);
  if (a.tip === "sonuc") return sonucCiz(v);
}

function guncelle(v) {
  if (v.faz === "lobi") return bulutCiz(v);
  if (v.faz === "takimlar") return takimCiz(v, false);
  const cs = document.getElementById("cs");
  if (cs && v.adim) {
    const yeni = `${v.adim.cevaplayan} / ${v.adim.aktif}`;
    if (cs.textContent !== yeni) {
      cs.textContent = yeni;
      cs.classList.remove("zipla"); void cs.offsetWidth; cs.classList.add("zipla");
    }
  }
  if (v.adim) Saat.ayarla(v.adim.kalan, v.adim.sure);
  const td = document.getElementById("takim-durum");
  if (td && v.adim && v.adim.takimlar) td.innerHTML = takimDurumIc(v);
}

function lobiAlt(v) {
  const eksik = (v.onaysiz || []).length;
  return `
    <button class="btn ikincil" id="yeni-oturum">Yeni oturum</button>
    <button class="btn ikincil" id="onay-ac">${eksik ? `İçeriği onayla (${eksik} bekliyor)` : "İçerik onaylandı ✓"}</button>
    <span class="bosluk"></span>
    <span class="not">${v.oyuncular.length < 2 ? "Takım için en az 2 kişi önerilir." : ""}</span>
    <button class="btn" data-eylem="takim_kur" ${v.oyuncular.length ? "" : "disabled"}>Takımları oluştur</button>`;
}

function lobiCiz(v) {
  goruluOyuncu = new Set();
  const kisa = (ses && ses.kisa) || "";
  sayfa(v, `
    <section class="lobi">
      <div class="lobi-bant">
        <div class="bant-parca">
          <span>Telefonundan gir</span>
          <b id="kisa">${esc(kisa)}</b>
        </div>
        <div class="bant-parca pin-parca">
          <span>Oyun PIN'i</span>
          <span class="pin-karolar">${[...v.pin].map(d => `<i>${esc(d)}</i>`).join("")}</span>
        </div>
      </div>
      <div class="lobi-govde">
        <div class="qr-kart">
          <img src="/qr/${esc(v.pin)}.svg" alt="Oyuna katılım için QR kod">
          <p>ya da okut</p>
        </div>
        <div class="lobi-sag">
          <div class="sayac-buyuk" id="sayi" aria-live="polite"></div>
          <div class="oyuncu-bulutu" id="bulut"></div>
        </div>
      </div>
    </section>`, lobiAlt(v));
  if (!kisa) fetch(`/api/oturum/${v.pin}/adres`).then(r => r.json()).then(d => {
    ses.katilim = d.katilim; ses.kisa = d.kisa; depoYaz("aq-host", ses);
    const el = document.getElementById("kisa"); if (el) el.textContent = d.kisa;
  });
  bulutCiz(v);
}

function bulutCiz(v) {
  const sayi = document.getElementById("sayi");
  if (!sayi) return;
  sayi.innerHTML = `<b>${v.oyuncular.length}</b><small>kişi katıldı</small>`;
  document.getElementById("bulut").innerHTML = v.oyuncular.map(p => {
    const yeni = !goruluOyuncu.has(p.id);
    goruluOyuncu.add(p.id);
    return `<span class="oyuncu-cip cip-${(v.oyuncular.indexOf(p)) % 6} ${yeni ? "yeni" : ""} ${p.bagli ? "" : "kopuk"}">${esc(p.ad)}<button data-cikar="${p.id}" aria-label="${esc(p.ad)} adlı oyuncuyu çıkar">✕</button></span>`;
  }).join("") || `<span class="bos-lobi">Oyuncular bekleniyor…</span>`;
  document.querySelectorAll("[data-cikar]").forEach(b => b.onclick = () => eylem("cikar", { oyuncu: b.dataset.cikar }));
  const alt = app.querySelector(".host-alt");
  if (alt) {
    alt.innerHTML = lobiAlt(v);
    alt.querySelectorAll("[data-eylem]").forEach(b => b.onclick = () => eylem(b.dataset.eylem));
    document.getElementById("yeni-oturum").onclick = yeniOturum;
    document.getElementById("onay-ac").onclick = () => { cekmeceAcik = true; cekmeceCiz(); };
  }
}

function takimCiz(v, animasyon = true) {
  const ad = id => (v.oyuncular.find(p => p.id === id) || {}).ad || "?";
  const eksik = (v.onaysiz || []).length;
  sayfa(v, `
    <section class="takim-izgara ${animasyon ? "karisiyor" : ""}">
      ${v.takimlar.map(t => `
        <article class="takim-kart" style="--renk:${t.renk}">
          <header style="--renk:${t.renk}"><span class="ikon">${takimIkon(t, 40)}</span><h3>${esc(t.ad)}</h3></header>
          <ul>${t.uyeler.map((u, i) => `<li style="animation-delay:${i * .12}s">${esc(ad(u))}</li>`).join("")}</ul>
        </article>`).join("")}
    </section>`, `
    <button class="btn ikincil" data-eylem="lobiye_don">Lobiye dön</button>
    <button class="btn ikincil" data-eylem="karistir">Yeniden karıştır</button>
    <label class="anahtar"><input type="checkbox" id="kisa-mod" ${v.kisa_mod ? "checked" : ""}> Kısa mod</label>
    <span class="bosluk"></span>
    <button class="btn ikincil" id="onay-ac">${eksik ? `İçeriği onayla (${eksik} bekliyor)` : "İçerik onaylandı ✓"}</button>
    <button class="btn buyuk" data-eylem="baslat" ${eksik ? "disabled title=\"Önce akıştaki tüm içeriği onayla\"" : ""}>Oyunu başlat</button>`);
  document.getElementById("kisa-mod").onchange = e => eylem("kisa", { deger: e.target.checked });
}

function cekmeceCiz() {
  let c = document.getElementById("cekmece");
  if (!cekmeceAcik || !durum || !durum.icerik) {
    if (c) c.remove();
    cekmeceAcik = cekmeceAcik && !!(durum && durum.icerik);
    return;
  }
  const kaydir = c ? c.querySelector(".cekmece-ic").scrollTop : 0;
  if (!c) {
    c = document.createElement("div");
    c.id = "cekmece";
    c.className = "cekmece";
    c.setAttribute("role", "dialog");
    c.setAttribute("aria-label", "İçerik onayı");
    document.body.appendChild(c);
  }
  const v = durum;
  const akistaki = v.icerik.filter(i => i.akista).length;
  const gruplar = [["kesif", "Kavramları Keşfet"], ["bilgi", "Bilgi Yarışması"], ["vaka", "Vaka Analizleri"], ["final", "Final"]];
  c.innerHTML = `
    <div class="cekmece-ic">
      <header>
        <h2>İçerik onayı</h2>
        <button class="btn kucuk" id="hepsi">Akıştakilerin hepsini onayla</button>
        <button class="btn ikincil kucuk" id="kapat">Kapat</button>
      </header>
      <p class="normal-not">${esc(v.makale.kunye)}<br>Bütün içerik bu makaleden üretildi ve kaynağı gösteriliyor. Akıştaki her öğe onaylanmadan oyun başlamaz. Bu paneli projeksiyona yansıtma, doğru cevaplar görünür.</p>
      <p><b>Akışta ${akistaki} öğe</b> · <label class="anahtar"><input type="checkbox" id="kisa2" ${v.kisa_mod ? "checked" : ""}> Kısa mod</label></p>
      ${gruplar.map(([g, baslik]) => `
        <div class="icerik-grup"><h3>${baslik}</h3>
          ${v.icerik.filter(i => i.asama === g).map(icerikKart).join("")}
        </div>`).join("")}
    </div>`;
  c.querySelector(".cekmece-ic").scrollTop = kaydir;
  c.onclick = e => { if (e.target === c) { cekmeceAcik = false; cekmeceCiz(); } };
  document.getElementById("kapat").onclick = () => { cekmeceAcik = false; cekmeceCiz(); };
  document.getElementById("hepsi").onclick = () => eylem("hepsini_onayla");
  document.getElementById("kisa2").onchange = e => eylem("kisa", { deger: e.target.checked });
  c.querySelectorAll("[data-onay]").forEach(i => i.onchange = () => eylem("onay", { item: i.dataset.onay, deger: i.checked }));
  c.querySelectorAll("[data-ek]").forEach(i => i.onchange = () => eylem("ek", { item: i.dataset.ek, deger: i.checked }));
}

function secenekListe(secenekler, dogru, notlar) {
  const d = Array.isArray(dogru) ? dogru : [dogru];
  return `<ol type="A">${secenekler.map((s, i) => `<li class="${d.includes(i) ? "dogru" : ""}">${esc(s)}${d.includes(i) ? " ✓" : notlar && notlar[i] ? ` <span class="normal-not">— ${esc(notlar[i])}</span>` : ""}</li>`).join("")}</ol>`;
}

function icerikKart(i) {
  const s = i.soru || i;
  const tur = i.tur === "case" ? (i.asama === "final" ? "Final senaryosu" : i.coklu ? "Hata bulma (takım kararı)" : TUR_ADI.case) : TUR_ADI[i.tur];
  let govde = "";
  if (i.tur === "scene") govde += `<dt>Sahne metni</dt><dd>${esc(i.metin)}<br>${esc(i.gorsel_altyazi)}<br><b>${esc(i.cikarim)}</b></dd><dt>Mini soru (${TUR_ADI[s.tur]})</dt><dd>${esc(s.metin)}</dd>`;
  else govde += `<dt>Soru</dt><dd>${esc(s.metin)}</dd>`;
  if (i.etiket) govde += `<dt>Etiket</dt><dd><span class="etiket-kurgu">${esc(i.etiket)}</span></dd>`;
  if (s.secenekler) govde += `<dt>Seçenekler</dt><dd>${secenekListe(s.secenekler, s.dogru, s.celdirici)}</dd>`;
  if (s.sol) govde += `<dt>Doğru eşleşme</dt><dd><ul>${s.sol.map((l, k) => `<li>${esc(l)} ↔ <span class="dogru">${esc(s.sag[k])}</span></li>`).join("")}</ul></dd>`;
  if (s.ogeler) govde += `<dt>Doğru sıra</dt><dd><ol>${s.ogeler.map(o => `<li>${esc(o)}</li>`).join("")}</ol></dd>`;
  if (s.gerekceler) govde += `<dt>Gerekçe seçenekleri</dt><dd>${secenekListe(s.gerekceler, s.dogru_gerekce, s.gerekce_notlari)}</dd>`;
  govde += `<dt>Açıklama</dt><dd>${esc(s.aciklama)}</dd><dt>Makaledeki kaynak</dt><dd>${esc(i.kaynak)}</dd><dt>Öğrenme hedefi</dt><dd>${esc(i.hedef)}</dd><dt>Zorluk</dt><dd>${esc(i.zorluk)}</dd>`;
  return `
    <article class="icerik-kart ${i.akista ? "" : "akista-degil"}">
      <div class="ust">
        <span class="kimlik">${esc(i.id)}</span><strong>${esc(i.kavram)}</strong><span class="etiket-kaynak">${esc(tur)}</span>
        <span class="bosluk" style="flex:1"></span>
        ${i.havuz === "yedek" ? `<label class="anahtar"><input type="checkbox" data-ek="${i.id}" ${i.ekli ? "checked" : ""}> Akışa ekle</label>` : `<span class="normal-not">${i.akista ? "Ana akış" : "Kısa modda çıkarıldı"}</span>`}
        <label class="anahtar"><input type="checkbox" data-onay="${i.id}" ${i.onayli ? "checked" : ""}> Onaylandı</label>
      </div>
      <dl>${govde}</dl>
    </article>`;
}

function ilerleDugmesi(etiket, birincil = true) {
  return `<button class="btn ${birincil ? "buyuk" : ""}" id="ilerle-btn">${etiket}</button>`;
}

function baglaIlerle() {
  const b = document.getElementById("ilerle-btn");
  if (b) b.onclick = () => eylem("ilerle");
}

const KURALLAR = [
  ["Telefonundan cevapla", "Sorular bu ekranda, cevaplar telefonunda. Seçtiğin cevap kilitlenir."],
  ["Hızlı ol", "Doğru cevap 100 puan. Ne kadar hızlıysan o kadar bonus."],
  ["Önce sen, sonra takımın", "Vakalarda önce tek başına karar ver, sonra takımınla tartışıp ortak kararı gönderin."],
  ["Adil puan", "Takım puanı kişi sayısına göre dengelenir. Küçük takım dezavantajlı olmaz."],
];

function kuralCiz(v) {
  sayfa(v, `
    <section class="kurallar">
      <h1>Nasıl oynanır?</h1>
      <div class="kural-izgara">${KURALLAR.map((k, i) => `<article class="kural-kart" style="animation-delay:${0.1 + i * 0.12}s"><span class="kural-no kutu-${i}">${i + 1}</span><h3>${esc(k[0])}</h3><p>${esc(k[1])}</p></article>`).join("")}</div>
    </section>`, `<span class="not">Boşluk tuşu veya sağ ok ile ilerleyebilirsin.</span><span class="bosluk"></span>${ilerleDugmesi("Başlayalım")}`);
  baglaIlerle();
}

function girisCiz(v) {
  const a = v.adim;
  sayfa(v, `
    <section class="sahne-giris asama-${esc(a.asama)}"><div>
      <h1>${esc(a.baslik)}</h1>
      <p>${esc(a.aciklama)}</p>
    </div></section>`, `<span class="not">Boşluk tuşu veya sağ ok ile ilerleyebilirsin.</span><span class="bosluk"></span>${ilerleDugmesi("Başla")}`);
  baglaIlerle();
}

function sahneTemizle() {
  sahneZamanlayici.forEach(clearTimeout);
  sahneZamanlayici = [];
}

function sahneCiz(v) {
  const it = v.adim.item;
  sayfa(v, `
    <section class="sahne adim-0" id="sahne">
      <h1 class="sahne-baslik">${esc(it.baslik)}</h1>
      <div class="gorsel-alan" id="gorsel"></div>
      <div>
        <p class="altyazi" id="altyazi" aria-live="polite"></p>
        <div class="sahne-noktalar" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
        <p style="margin-top:1rem"><span class="etiket-kaynak">Kaynak: ${esc(it.kaynak)}</span></p>
      </div>
    </section>`, `<button class="btn ikincil" id="tekrar">Sahneyi tekrar oynat</button><span class="bosluk"></span>${ilerleDugmesi("Mini soruya geç")}`);
  baglaIlerle();
  document.getElementById("tekrar").onclick = () => { sahneTemizle(); sahneOynat(it); };
  sahneOynat(it);
}

function sahneOynat(it) {
  const sahne = document.getElementById("sahne");
  const gorsel = document.getElementById("gorsel");
  const alt = document.getElementById("altyazi");
  const noktalar = sahne.querySelectorAll(".sahne-noktalar i");
  const adimlar = [
    [0, () => { gorsel.innerHTML = ""; alt.innerHTML = ""; alt.className = "altyazi"; }],
    [2200, () => { alt.innerHTML = `<span>${esc(it.metin)}</span>`; }],
    [7500, () => { gorsel.innerHTML = SAHNE_GORSEL[it.gorsel] || ""; alt.innerHTML = `<span>${esc(it.gorsel_altyazi)}</span>`; }],
    [16000, () => { alt.className = "altyazi cikarim"; alt.innerHTML = `<span>${esc(it.cikarim)}</span>`; }],
  ];
  const hizli = azHareket || matchMedia("(prefers-reduced-motion: reduce)").matches;
  adimlar.forEach(([t, fn], i) => sahneZamanlayici.push(setTimeout(() => {
    fn();
    sahne.className = `sahne adim-${i}`;
    noktalar.forEach((n, k) => n.classList.toggle("aktif", k <= i));
  }, hizli ? t * .6 : t)));
}

function sayacHtml() {
  return `<div class="sayac" id="sayac" role="timer" aria-label="Kalan süre"><svg viewBox="0 0 120 120"><circle class="iz" cx="60" cy="60" r="52"/><circle class="dolu" cx="60" cy="60" r="52" stroke-dasharray="326.7" stroke-dashoffset="0"/></svg><b>–</b></div>`;
}

function sayacDongusu() {
  const el = document.getElementById("sayac");
  if (el) {
    const k = Saat.kalan();
    if (k == null) el.style.visibility = "hidden";
    else {
      el.style.visibility = "visible";
      el.querySelector("b").textContent = Math.ceil(k);
      el.querySelector(".dolu").setAttribute("stroke-dashoffset", 326.7 * (1 - k / (Saat.toplam || 1)));
      el.classList.toggle("az", k <= 5);
    }
  }
  requestAnimationFrame(sayacDongusu);
}
requestAnimationFrame(sayacDongusu);

function secenekKutulari(it, acik, dagilim, tekSutun) {
  const dogrular = Array.isArray(it.dogru) ? it.dogru : [it.dogru];
  return `<div class="secenek-izgara ${tekSutun ? "tek-sutun" : ""}">${it.secenekler.map((o, k) => {
    const i = o.i;
    const sinif = acik ? (dogrular.includes(i) ? "dogru" : "yanlis") : "";
    const adet = dagilim && dagilim[String(i)] != null ? dagilim[String(i)] : (acik ? 0 : null);
    const not = acik && it.celdirici && it.celdirici[i] ? `<span class="not">${esc(it.celdirici[i])}</span>` : "";
    return `<div class="secenek kutu-${k % 4} ${sinif}">${sekil(k)}<span>${esc(o.metin)}${not}</span>${adet != null ? `<span class="adet">${adet}</span>` : ""}</div>`;
  }).join("")}</div>`;
}

function soruGovde(it, acik, dagilim) {
  if (it.tur === "mc" || it.tur === "tf") return secenekKutulari(it, acik, dagilim, false);
  if (it.tur === "match") {
    if (!acik) return `<div class="esleme-tablo">${it.sol.map((l, i) => `<div class="esleme-satir" style="animation-delay:${i * .08}s"><span>${esc(l)}</span><span>↔</span><span class="normal-not">?</span></div>`).join("")}</div>`;
    return `<div class="esleme-tablo">${it.sol.map((l, i) => `<div class="esleme-satir"><span>${esc(l)}</span><span>↔</span><span class="ok">${esc(it.eslesme[i])}</span></div>`).join("")}</div>`;
  }
  if (it.tur === "order") {
    if (!acik) return `<div class="esleme-tablo">${it.ogeler.map((o, i) => `<div class="esleme-satir" style="grid-template-columns:1fr;animation-delay:${i * .08}s"><span>${esc(o.metin)}</span></div>`).join("")}</div>`;
    return `<div class="esleme-tablo">${it.dogru_sira.map((o, i) => `<div class="esleme-satir" style="grid-template-columns:2.4rem 1fr"><span class="ok">${i + 1}.</span><span>${esc(o)}</span></div>`).join("")}</div>`;
  }
  return "";
}

function soruCiz(v) {
  const a = v.adim, it = a.item, acik = a.alt === "sonuc";
  Saat.ayarla(a.kalan, a.sure);
  const ort = acik && a.dagilim && a.dagilim.ort != null ? `<span>Ortalama doğruluk: <b>%${Math.round(a.dagilim.ort * 100)}</b></span>` : "";
  sayfa(v, `
    <section class="soru-alan ${acik ? "acik" : ""}">
      <div class="soru-ust"><h2>${esc(it.metin)}</h2>${acik ? "" : sayacHtml()}</div>
      ${soruGovde(it, acik, a.dagilim)}
      <div class="soru-alt">
        ${acik ? `<div class="aciklama-kutu" style="flex:1">${esc(it.aciklama)}<div style="margin-top:.5rem"><span class="etiket-kaynak">Kaynak: ${esc(it.kaynak)}</span></div></div>` : `<span><span class="cevap-sayaci" id="cs">${a.cevaplayan} / ${a.aktif}</span> kişi cevapladı</span>`}
        ${ort}
      </div>
    </section>`, acik ? `<span class="bosluk"></span>${ilerleDugmesi("Devam")}` : `<span class="not">Herkes cevaplayınca soru kendiliğinden kapanır.</span><span class="bosluk"></span>${ilerleDugmesi("Süreyi bitir", false)}`);
  baglaIlerle();
}

function takimDurumIc(v) {
  const a = v.adim;
  return v.siralama.map(s => {
    const t = a.takimlar.find(x => x.id === s.id);
    const tk = v.takimlar.find(x => x.id === s.id);
    let govde = "";
    if (a.alt === "bireysel") govde = `<div class="satir"><span>Bireysel karar</span><span class="${t.bireysel === t.boyut ? "ok" : "bekle"}">${t.bireysel}/${t.boyut}</span></div>`;
    if (a.alt === "tartisma") govde = `<div class="satir"><span>Oylar</span><span>${t.bireysel}/${t.boyut}</span></div><div class="satir"><span>Durum</span><span class="bekle">tartışıyor</span></div>`;
    if (a.alt === "takim") govde = `<div class="satir"><span>Takım kararı</span>${t.cevap_geldi ? `<span class="ok kilit-anim">🔒 kilitlendi</span>` : `<span class="bekle">bekleniyor</span>`}</div><div class="satir"><span>Gerekçe</span>${t.gerekce_geldi ? `<span class="ok kilit-anim">🔒 kilitlendi</span>` : `<span class="bekle">bekleniyor</span>`}</div>`;
    if (a.alt === "sonuc") {
      const cevap = harfler(a.item.secenekler, t.cevap);
      govde = `<div class="satir"><span>Karar: <b>${cevap}</b></span><span class="${t.dogru ? "ok" : "bekle"}">${t.dogru ? "✓ doğru" : "✗"}</span></div>
        <div class="satir"><span>Gerekçe: <b>${harfler(a.item.gerekceler, t.gerekce)}</b></span><span class="${t.gerekce_dogru ? "ok" : "bekle"}">${t.gerekce_dogru ? "✓" : "✗"}</span></div>
        <div class="satir"><span>Tam katılım</span><span class="${t.tam_katilim ? "ok" : "bekle"}">${t.tam_katilim ? "✓" : "✗"}</span></div>
        <div class="satir"><span>Takım puanı</span><b class="kazanc" style="font-size:1.4rem">+${t.puan}</b></div>`;
    }
    return `<div class="kutu" style="--renk:${tk.renk}"><h4>${takimIkon(tk, 22)} ${esc(tk.ad)}</h4>${govde}</div>`;
  }).join("");
}

function vakaCiz(v) {
  const a = v.adim, it = a.item, acik = a.alt === "sonuc";
  Saat.ayarla(a.kalan, a.sure);
  const bilgi = {
    bireysel: "Herkes önce tek başına karar veriyor. Takım arkadaşının cevabına bakma.",
    tartisma: "Telefonlarınızda takım arkadaşlarınızın oyları açıldı. Vaka analisti başlatsın, birlikte tartışın.",
    takim: "Karar verici takım cevabını, gerekçelendirme sorumlusu gerekçeyi gönderiyor.",
    sonuc: "",
  }[a.alt];
  const dugme = { bireysel: ["Tartışmayı başlat", false], tartisma: ["Takım kararına geç", true], takim: ["Sonucu göster", false], sonuc: ["Devam", true] }[a.alt];
  const gerekceler = acik ? `<div class="aciklama-kutu"><b>Doğru gerekçe:</b> ${esc(metinBul(it.gerekceler, it.dogru_gerekce))}<br>${esc(it.aciklama)}<div style="margin-top:.5rem"><span class="etiket-kaynak">Kaynak: ${esc(it.kaynak)}</span></div></div>` : "";
  if (acik) {
    sayfa(v, `
      <section class="soru-alan vaka acik vaka-acik">
        <div class="soru-ust"><h2>${esc(it.metin)}</h2></div>
        <div class="vaka-sonuc">
          ${secenekKutulari(it, true, a.dagilim, true)}
          <div style="display:grid;gap:1rem;align-content:start">${gerekceler}<div class="takim-durum" id="takim-durum">${takimDurumIc(v)}</div></div>
        </div>
      </section>`, `<span class="etiket-kurgu">${esc(it.etiket)}</span><span class="bosluk"></span>${ilerleDugmesi(dugme[0], dugme[1])}`);
    baglaIlerle();
    return;
  }
  sayfa(v, `
    <section class="soru-alan vaka" style="grid-template-rows:auto auto auto 1fr">
      <div><span class="etiket-kurgu">${esc(it.etiket)}</span></div>
      <div class="soru-ust"><h2>${esc(it.metin)}</h2>${sayacHtml()}</div>
      ${a.alt === "bireysel" || acik ? secenekKutulari(it, acik, acik ? a.dagilim : null, true) : `<p class="normal-not" style="font-size:1.2rem">${esc(bilgi)}</p>`}
      <div style="display:grid;gap:1rem;align-content:start">
        ${gerekceler}
        ${a.alt === "bireysel" ? `<p class="normal-not">${esc(bilgi)} <span class="cevap-sayaci" id="cs">${a.cevaplayan} / ${a.aktif}</span></p>` : ""}
        <div class="takim-durum" id="takim-durum">${takimDurumIc(v)}</div>
      </div>
    </section>`, `<span class="bosluk"></span>${ilerleDugmesi(dugme[0], dugme[1])}`);
  baglaIlerle();
}

function baslikKazanan(v) {
  const birinciler = (v.siralama || []).filter(t => t.sira === 1);
  if (!birinciler.length) return "Oyun bitti";
  if (birinciler.length === 1) return `${esc(birinciler[0].ad)} kazandı`;
  return `Berabere: ${birinciler.map(t => esc(t.ad)).join(" ve ")}`;
}

function podyum(v) {
  const ilk = v.siralama.slice(0, 3);
  const dizi = [1, 0, 2].filter(i => ilk[i]).map(i => [ilk[i], i]);
  const boy = [230, 180, 140];
  return `<div class="podyum">${dizi.map(([t]) => { const r = Math.min(t.sira, 3); return `<div class="podyum-sutun" style="--renk:${t.renk}"><span class="podyum-puan">${t.puan}</span>${piramitSvg(boy[r - 1], t.renk, "")}<span class="podyum-ad"><b>${t.sira}</b> ${esc(t.ad)}</span></div>`; }).join("")}</div>`;
}

function siraSatirlari(v) {
  return v.siralama.map(t => `
    <div class="sira-satir" data-id="${t.id}" style="--renk:${t.renk}">
      <span class="no">${t.sira}.</span><span>${takimIkon(t, 34)}</span>
      <span>${esc(t.ad)}<span class="boyut">${t.boyut} kişi</span>${(v.rozetler && v.rozetler[t.id] || []).map(r => `<span class="rozet" title="${esc(r.neden)}">★ ${esc(r.ad)}</span>`).join("")}</span>
      <span class="puan" data-puan="${t.puan}">${t.puan}</span>
    </div>`).join("");
}

function flip(kap) {
  const satirlar = [...kap.querySelectorAll(".sira-satir")];
  const yuk = satirlar[0] ? satirlar[0].offsetHeight + 11 : 0;
  satirlar.forEach((s, i) => {
    const eski = oncekiSira[s.dataset.id];
    if (eski != null && eski !== i) {
      s.style.transform = `translateY(${(eski - i) * yuk}px)`;
      requestAnimationFrame(() => requestAnimationFrame(() => { s.style.transition = "transform .9s cubic-bezier(.2,1,.3,1)"; s.style.transform = ""; }));
    }
    const p = s.querySelector(".puan");
    const hedef = +p.dataset.puan, bas = performance.now(), ilk = s.dataset.id in eskiPuan ? eskiPuan[s.dataset.id] : 0;
    (function say(t) { const k = Math.min(1, (t - bas) / 900); p.textContent = Math.round(ilk + (hedef - ilk) * k); if (k < 1) requestAnimationFrame(say); })(bas);
  });
  oncekiSira = Object.fromEntries(satirlar.map((s, i) => [s.dataset.id, i]));
  eskiPuan = Object.fromEntries(satirlar.map(s => [s.dataset.id, +s.querySelector(".puan").dataset.puan]));
}
let eskiPuan = {};

function tabloCiz(v) {
  sayfa(v, `
    <section class="tablo-alan">
      <h2>Takım sıralaması</h2>
      <div style="display:grid;gap:.7rem" id="tablo">${siraSatirlari(v)}</div>
      <p class="normal-not">Bireysel puanlar takım büyüklüğüne göre ortalanır, takım kararı puanları eklenir. Böylece küçük takımlar dezavantajlı olmaz.</p>
    </section>`, `<span class="bosluk"></span>${ilerleDugmesi("Devam")}`);
  baglaIlerle();
  flip(document.getElementById("tablo"));
}

function sonucCiz(v) {
  sayfa(v, `
    <section class="sonuc-alan">
      <div>
        <h2>${baslikKazanan(v)}</h2>
        ${podyum(v)}
        <div style="display:grid;gap:.7rem" id="tablo">${siraSatirlari(v)}</div>
        <p class="normal-not">Puanlar takım büyüklüğüne göre normalize edildi.</p>
      </div>
      <div>
        <h3 style="font-size:1.6rem;margin-bottom:.8rem">Bu oyunda çalıştığımız kavramlar</h3>
        <ul class="ogrenilen">${(v.ogrenilenler || []).map(k => `<li>${esc(k)}</li>`).join("")}</ul>
        <h3 style="font-size:1.2rem;margin:1.4rem 0 .6rem">En çok puan toplayanlar</h3>
        <ol>${(v.bireysel_siralama || []).slice(0, 3).map(p => `<li><b>${esc(p.ad)}</b> · ${p.puan}</li>`).join("")}</ol>
        <p class="normal-not" style="margin-top:1rem">Kaynak: ${esc(v.makale.kunye)}</p>
      </div>
    </section>`, `<button class="btn ikincil" id="yeni-oturum">Yeni oturum</button><span class="bosluk"></span><a class="btn" href="/disa-aktar/${esc(v.pin)}.csv?token=${encodeURIComponent(ses ? ses.token : "")}">Sonuçları indir (CSV)</a>`);
  flip(document.getElementById("tablo"));
  konfeti();
}

document.addEventListener("keydown", e => {
  if (e.key === "Escape" && cekmeceAcik) { cekmeceAcik = false; cekmeceCiz(); return; }
  if (e.target.closest("input, textarea, select") || cekmeceAcik) return;
  if (e.key === "ArrowRight" || e.key === " ") {
    const b = document.getElementById("ilerle-btn");
    if (b) { e.preventDefault(); b.click(); }
  }
});

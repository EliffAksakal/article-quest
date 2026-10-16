const socket = io({ transports: ["websocket", "polling"] });
const app = document.getElementById("app");
let ses = depoAl("aq-oyuncu");
let durum = null;
let anahtar = null;
let yerel = { adim: null, secim: [], esle: {}, sira: null };
let gonderiliyor = false;

if (ses && window.PIN && ses.pin !== window.PIN) { depoSil("aq-oyuncu"); ses = null; }

socket.on("connect", () => {
  if (ses) {
    socket.emit("oyuncu:merhaba", ses, r => {
      if (!r || !r.ok) { depoSil("aq-oyuncu"); ses = null; girisCiz(r && r.hata); }
    });
  } else girisCiz();
});
socket.on("disconnect", () => { if (ses) bildir("Bağlantı koptu, yeniden bağlanılıyor…"); });
socket.on("baska_cihaz", () => { app.innerHTML = `<main class="oyuncu-ana"><div class="bekleme"><div><h2>Bu oturum başka bir sekmede açıldı.</h2><p>Oyuna oradan devam et.</p></div></div></main>`; socket.disconnect(); });
socket.on("durum", v => { durum = v; ciz(v); });

function girisCiz(hata) {
  anahtar = "giris";
  const pinVar = !!window.PIN;
  app.innerHTML = `
    <main class="oyuncu-ana giris-ekran">
      <div class="giris-piramit">${prizmaSvg(270, "buyuk")}</div>
      <h1 class="giris-logo">Prizma</h1>
      <p class="giris-alt">Karar kimde?</p>
      <form class="form-alan giris-kart" id="katil-form" autocomplete="off">
        ${pinVar ? `<p class="pin-hazir">PIN <b>${esc(window.PIN)}</b></p>` : `<label for="pin">Oyun PIN'i</label><input id="pin" class="pin-giris" inputmode="numeric" maxlength="6" required placeholder="000000">`}
        <label for="ad">Takma adın</label>
        <input id="ad" maxlength="20" required placeholder="Ör. Deniz">
        <button class="btn buyuk">Oyuna katıl</button>
        ${hata ? `<p role="alert" class="giris-hata">${esc(hata)}</p>` : ""}
      </form>
    </main>`;
  document.getElementById("katil-form").onsubmit = e => {
    e.preventDefault();
    const pin = pinVar ? window.PIN : document.getElementById("pin").value.trim();
    const ad = document.getElementById("ad").value.trim();
    socket.emit("oyuncu:katil", { pin, ad }, r => {
      if (!r.ok) return girisCiz(r.hata);
      ses = { pin: r.pin, id: r.id, token: r.token };
      depoYaz("aq-oyuncu", ses);
    });
  };
}

function gonder(olay, veri) {
  if (gonderiliyor) return;
  gonderiliyor = true;
  socket.emit(olay, veri, r => {
    gonderiliyor = false;
    if (r && !r.ok) bildir(r.hata);
  });
}

function anahtarHesapla(v) {
  const a = v.adim || {};
  return JSON.stringify([v.faz, a.no, a.alt, !!a.benim, a.takim_cevap && [a.takim_cevap.cevap != null, a.takim_cevap.gerekce != null], a.takim_oylari, v.takim && v.takim.uyeler.map(u => u.bagli), a.karar_yetkim, a.gerekce_yetkim]);
}

function ciz(v) {
  if (v.faz === "yok") { depoSil("aq-oyuncu"); ses = null; return girisCiz("Oturum bulunamadı."); }
  if (v.adim && yerel.adim !== `${v.adim.no}|${v.adim.alt}`) {
    yerel = { adim: `${v.adim.no}|${v.adim.alt}`, secim: [], esle: {}, sira: null };
  }
  if (v.adim) Saat.ayarla(v.adim.kalan, v.adim.sure);
  const k = anahtarHesapla(v);
  if (k === anahtar) return ustGuncelle(v);
  anahtar = k;
  const t = v.takim;
  document.documentElement.style.setProperty("--takim", t ? t.renk : "#161B3D");
  app.innerHTML = `${ustHtml(v)}<main class="oyuncu-ana" id="ana"></main>`;
  const ana = document.getElementById("ana");
  if (v.faz === "lobi") return lobi(ana, v);
  if (v.faz === "takimlar") return takimEkran(ana, v);
  const a = v.adim;
  if (a.tip === "giris") ana.innerHTML = `<div class="bekleme"><div><h1>${esc(a.baslik)}</h1><p>${esc(a.aciklama)}</p><p class="normal-not">Büyük ekrana bak.</p></div></div>`;
  else if (a.tip === "sahne") sahne(ana, a);
  else if (a.tip === "soru") soru(ana, v);
  else if (a.tip === "vaka") vaka(ana, v);
  else if (a.tip === "tablo") tablo(ana, v);
  else if (a.tip === "sonuc") sonuc(ana, v);
}

function ustHtml(v) {
  const t = v.takim;
  return `<header class="oyuncu-ust">
    <span class="ikon">${takimIkon(t, 30)}</span>
    <span class="ad">${esc(v.ben.ad)}<small>${t ? esc(t.ad) : "Lobide"}</small></span>
    <span class="puan" id="puan" aria-label="Puanın">${v.ben.puan}</span>
  </header>${v.adim && v.adim.kalan != null ? `<div class="zaman-cubugu" aria-hidden="true"><span id="zaman"></span></div>` : ""}`;
}

function ustGuncelle(v) {
  const p = document.getElementById("puan");
  if (p) p.textContent = v.ben.puan;
}

function zamanDongusu() {
  const z = document.getElementById("zaman");
  if (z) {
    const k = Saat.kalan();
    z.style.transform = `scaleX(${k == null ? 0 : k / (Saat.toplam || 1)})`;
  }
  requestAnimationFrame(zamanDongusu);
}
requestAnimationFrame(zamanDongusu);

function lobi(ana, v) {
  ana.innerHTML = `<div class="bekleme"><div>
    <div class="buyuk-ikon">${piramitSvg(120, "var(--mor)", "")}</div>
    <h1>Hoş geldin, ${esc(v.ben.ad)}!</h1>
    <p>Takımlar kurulunca burada göreceksin.</p>
    <div class="nabiz" style="margin-top:1.5rem"></div>
  </div></div>`;
}

function takimEkran(ana, v) {
  const t = v.takim;
  ana.innerHTML = `<div class="bekleme"><div>
    <div class="buyuk-ikon">${takimIkon(t, 120)}</div>
    <h1>${esc(t.ad)}</h1>
    <p>Takım arkadaşların:</p>
    <div class="oylar kart" style="text-align:left">${t.uyeler.map(u => `<div><span>${esc(u.ad)}${u.id === v.ben.id ? " (sen)" : ""}</span><span>${u.bagli ? "🟢" : "⚪"}</span></div>`).join("")}</div>
    <p class="normal-not" style="margin-top:1rem">Yanlarına geç. Oyun birazdan başlıyor.</p>
  </div></div>`;
}

function sahne(ana, a) {
  const it = a.item;
  ana.innerHTML = `
    <p class="normal-not">Büyük ekrandaki sahneyi izle. Altyazısı burada:</p>
    <h2>${esc(it.baslik)}</h2>
    <div class="kart">${esc(it.metin)}</div>
    <div class="kart">${esc(it.gorsel_altyazi)}</div>
    <div class="kart rol"><h3>Kritik çıkarım</h3>${esc(it.cikarim)}</div>
    <span class="etiket-kaynak">Kaynak: ${esc(it.kaynak)}</span>`;
}

function kilitli(ana, mesaj) {
  ana.innerHTML = `<div class="kilitlendi"><div class="kilit">${piramitSvg(130, "var(--mor)")}</div><h2>Cevabın kilitlendi</h2><p class="normal-not">${esc(mesaj || "Diğerleri cevaplarken büyük ekrana bak.")}</p></div>`;
}

function secenekDugmeleri(secenekler, coklu, notr) {
  return `<div class="mobil-secenekler">${secenekler.map((o, k) => `
    <button class="mobil-secenek kutu-${k % 4} ${notr ? "notr" : "dolu"} ${yerel.secim.includes(o.i) ? "secili" : ""}" data-i="${o.i}" aria-pressed="${yerel.secim.includes(o.i)}">
      ${sekil(k)}<span>${esc(o.metin)}</span>
    </button>`).join("")}</div>${coklu ? `<button class="btn buyuk" id="gonder" ${yerel.secim.length ? "" : "disabled"}>Gönder</button>` : ""}`;
}

function secenekBagla(ana, coklu, gonderFn) {
  ana.querySelectorAll(".mobil-secenek").forEach(b => b.onclick = () => {
    const i = +b.dataset.i;
    if (!coklu) {
      ana.querySelectorAll(".mobil-secenek").forEach(x => x.classList.toggle("soluk", x !== b));
      b.classList.add("secili");
      return gonderFn(i);
    }
    yerel.secim = yerel.secim.includes(i) ? yerel.secim.filter(x => x !== i) : [...yerel.secim, i];
    b.classList.toggle("secili");
    b.setAttribute("aria-pressed", yerel.secim.includes(i));
    ana.querySelector("#gonder").disabled = !yerel.secim.length;
  });
  const g = ana.querySelector("#gonder");
  if (g) g.onclick = () => gonderFn([...yerel.secim].sort());
}

function soru(ana, v) {
  const a = v.adim, it = a.item;
  if (a.alt === "sonuc") return soruSonuc(ana, a);
  if (a.benim) return kilitli(ana);
  const cevapla = c => gonder("oyuncu:cevap", { cevap: c });
  if (it.tur === "mc" || it.tur === "tf") {
    ana.innerHTML = `<h2>${esc(it.metin)}</h2>${secenekDugmeleri(it.secenekler, false)}`;
    return secenekBagla(ana, false, cevapla);
  }
  if (it.tur === "match") {
    ana.innerHTML = `<h2>${esc(it.metin)}</h2><div class="esle-mobil">${it.sol.map((l, i) => `
      <div><label for="e${i}">${esc(l)}</label><select id="e${i}" data-i="${i}"><option value="">Seç…</option>${it.sag.map(r => `<option value="${r.i}" ${yerel.esle[i] == r.i ? "selected" : ""}>${esc(r.metin)}</option>`).join("")}</select></div>`).join("")}</div>
      <button class="btn buyuk" id="gonder">Gönder</button>`;
    const kontrol = () => { document.getElementById("gonder").disabled = it.sol.some((_, i) => yerel.esle[i] == null || yerel.esle[i] === ""); };
    ana.querySelectorAll("select").forEach(s => s.onchange = () => { yerel.esle[s.dataset.i] = s.value === "" ? null : +s.value; kontrol(); });
    kontrol();
    document.getElementById("gonder").onclick = () => cevapla(it.sol.map((_, i) => yerel.esle[i]));
    return;
  }
  if (it.tur === "order") {
    if (!yerel.sira) yerel.sira = it.ogeler.map(o => o.i);
    const metin = Object.fromEntries(it.ogeler.map(o => [o.i, o.metin]));
    const ciz2 = () => {
      ana.innerHTML = `<h2>${esc(it.metin)}</h2><p class="normal-not">İlk adım en üstte olacak şekilde sırala.</p>
        <ol class="sira-liste">${yerel.sira.map((x, k) => `<li><b>${k + 1}.</b><span>${esc(metin[x])}</span>
          <button data-yukari="${k}" aria-label="Yukarı taşı" ${k === 0 ? "disabled" : ""}>↑</button>
          <button data-asagi="${k}" aria-label="Aşağı taşı" ${k === yerel.sira.length - 1 ? "disabled" : ""}>↓</button></li>`).join("")}</ol>
        <button class="btn buyuk" id="gonder">Gönder</button>`;
      ana.querySelectorAll("[data-yukari]").forEach(b => b.onclick = () => { const k = +b.dataset.yukari; [yerel.sira[k - 1], yerel.sira[k]] = [yerel.sira[k], yerel.sira[k - 1]]; ciz2(); });
      ana.querySelectorAll("[data-asagi]").forEach(b => b.onclick = () => { const k = +b.dataset.asagi; [yerel.sira[k + 1], yerel.sira[k]] = [yerel.sira[k], yerel.sira[k + 1]]; ciz2(); });
      document.getElementById("gonder").onclick = () => cevapla(yerel.sira);
    };
    ciz2();
  }
}

function sonucRozet(dogruluk, cevapVar, kazanc) {
  const sinif = !cevapVar || dogruluk === 0 ? "yanlis" : dogruluk === 1 ? "dogru" : "kismi";
  const baslik = !cevapVar ? "Cevap vermedin" : dogruluk === 1 ? "Doğru!" : dogruluk > 0 ? `%${Math.round(dogruluk * 100)} doğru` : "Bu sefer olmadı";
  return `<div class="sonuc-rozet ${sinif}"><h2>${baslik}</h2>${kazanc ? `<div class="kazanc">+${kazanc}</div>` : ""}</div>`;
}

function soruSonuc(ana, a) {
  const it = a.item;
  const b = a.benim;
  let dogruMetin = "";
  if (it.secenekler) dogruMetin = `<b>Doğru cevap:</b> ${esc(metinBul(it.secenekler, it.dogru))}`;
  if (it.eslesme) dogruMetin = `<b>Doğru eşleşme:</b><ul>${it.sol.map((l, i) => `<li>${esc(l)} ↔ ${esc(it.eslesme[i])}</li>`).join("")}</ul>`;
  if (it.dogru_sira) dogruMetin = `<b>Doğru sıra:</b><ol>${it.dogru_sira.map(o => `<li>${esc(o)}</li>`).join("")}</ol>`;
  ana.innerHTML = `${sonucRozet(b ? b.dogruluk : 0, !!b, a.kazanc)}
    <div class="kart">${dogruMetin}</div>
    <div class="kart">${esc(it.aciklama)}</div>
    <span class="etiket-kaynak">Kaynak: ${esc(it.kaynak)}</span>`;
}

function rolKart(a) {
  return (a.gorevim || []).map(g => `<div class="kart rol"><h3>Bu turdaki görevin: ${esc(g.rol)}</h3>${esc(g.gorev)}</div>`).join("");
}


function vaka(ana, v) {
  const a = v.adim, it = a.item, tc = a.takim_cevap || {};
  const metin = `<span class="etiket-kurgu">${esc(it.etiket)}</span><div class="kart">${esc(it.metin)}</div>`;
  const H = c => harfler(it.secenekler, c);
  const liste = `<ol type="A" class="kart" style="padding-left:2.2rem;margin:0">${it.secenekler.map(o => `<li>${esc(o.metin)}</li>`).join("")}</ol>`;
  const oylar = a.takim_oylari ? `<div class="kart"><h3>Takımının bireysel oyları</h3><div class="oylar">${a.takim_oylari.map(o => `<div><span>${esc(o.ad)}</span><b>${o.cevap == null ? "oy vermedi" : H(o.cevap)}</b></div>`).join("")}</div></div>` : "";
  if (a.alt === "bireysel") {
    if (a.benim) {
      ana.innerHTML = rolKart(a);
      ana.insertAdjacentHTML("afterbegin", `<div class="kilitlendi"><div class="kilit">${piramitSvg(130, "var(--mor)")}</div><h2>Kararın kaydedildi</h2><p class="normal-not">Herkes karar verince tartışma başlayacak.</p></div>`);
      return;
    }
    ana.innerHTML = `${rolKart(a)}${metin}<h2>Önce tek başına karar ver${it.coklu ? " (iki seçenek)" : ""}</h2>${secenekDugmeleri(it.secenekler, !!it.coklu, true)}`;
    return secenekBagla(ana, !!it.coklu, c => gonder("oyuncu:cevap", { cevap: c }));
  }
  if (a.alt === "tartisma") {
    ana.innerHTML = `<h2>Takımınla tartış</h2>${rolKart(a)}${oylar}${metin}${liste}`;
    return;
  }
  if (a.alt === "takim") {
    let ic = `${rolKart(a)}${oylar}`;
    const kararBekliyor = tc.cevap == null, gerekceBekliyor = tc.gerekce == null;
    if (a.karar_yetkim && kararBekliyor) {
      ic += `<h2>Takımın ortak cevabını gönder</h2><div id="takim-sec">${secenekDugmeleri(it.secenekler, !!it.coklu, true)}</div>`;
    } else {
      ic += `<div class="kart"><b>Takım kararı:</b> ${kararBekliyor ? "karar verici seçiyor…" : `<span class="ok kilit-anim">🔒 ${H(tc.cevap)}</span>`}</div>`;
    }
    if (a.gerekce_yetkim && gerekceBekliyor) {
      ic += `<h2>Gerekçeyi seç</h2><div class="mobil-secenekler" id="gerekce">${it.gerekceler.map((g, k) => `<button class="mobil-secenek notr kutu-${k % 4}" data-g="${g.i}">${sekil(k)}<span>${esc(g.metin)}</span></button>`).join("")}</div>`;
    } else {
      ic += `<div class="kart"><b>Gerekçe:</b> ${gerekceBekliyor ? "gerekçelendirme sorumlusu seçiyor…" : `<span class="ok kilit-anim">🔒 ${harfler(it.gerekceler, tc.gerekce)}</span>`}</div>`;
    }
    ic += metin;
    ana.innerHTML = ic;
    if (a.karar_yetkim && kararBekliyor) secenekBagla(document.getElementById("takim-sec"), !!it.coklu, c => gonder("oyuncu:takim", { cevap: c }));
    ana.querySelectorAll("[data-g]").forEach(b => b.onclick = () => { b.classList.add("secili"); gonder("oyuncu:takim", { gerekce: +b.dataset.g }); });
    return;
  }
  const b = a.benim;
  const sozcu = (a.gorevim || []).some(g => g.rol === "Takım sözcüsü");
  const dogruHarf = H(it.dogru);
  ana.innerHTML = `
    <div class="sonuc-rozet ${tc.dogru ? "dogru" : "yanlis"}"><h2>${tc.dogru ? "Takım kararı doğru!" : "Takım kararı yanlış"}</h2>${tc.puan ? `<div class="kazanc">+${tc.puan}</div>` : ""}<p style="margin:.3rem 0 0">takım puanı</p></div>
    ${sozcu ? `<div class="kart rol"><h3>Sözcü olarak sıra sende</h3>Takımınızın kararını ve gerekçesini sınıfa kısaca açıkla.</div>` : ""}
    <div class="kart"><div class="oylar">
      <div><span>Senin kararın</span><b>${b ? H(b.cevap) : "vermedin"} ${b && b.dogruluk === 1 ? "✓" : "✗"}</b></div>
      <div><span>Takım kararı</span><b>${H(tc.cevap)} ${tc.dogru ? "✓" : "✗"}</b></div>
      <div><span>Gerekçe</span><b>${harfler(it.gerekceler, tc.gerekce)} ${tc.gerekce_dogru ? "✓" : "✗"}</b></div>
      <div><span>Tam katılım</span><b>${tc.tam_katilim ? "✓" : "✗"}</b></div>
    </div></div>
    <div class="kart"><b>Doğru cevap: ${dogruHarf}</b><br>${esc(it.aciklama)}<br><br><b>Doğru gerekçe:</b> ${esc(metinBul(it.gerekceler, it.dogru_gerekce))}</div>
    <span class="etiket-kaynak">Kaynak: ${esc(it.kaynak)}</span>`;
}

function tablo(ana, v) {
  const a = v.adim;
  ana.innerHTML = `<div class="bekleme"><div>
    <div class="buyuk-ikon">${takimIkon(v.takim, 120)}</div>
    <h1>${a.takim_sirasi}. sıradasınız</h1>
    <p>${a.takim_sayisi} takım arasında · takım puanı <b>${v.takim.puan}</b></p>
    <p class="normal-not">Senin puanın: ${v.ben.puan}</p>
  </div></div>`;
}

function sonuc(ana, v) {
  const a = v.adim;
  ana.innerHTML = `<div class="bekleme"><div>
    <div class="buyuk-ikon">${takimIkon(v.takim, a.takim_sirasi === 1 ? 170 : 120)}</div>
    <h1>${a.takim_sirasi === 1 ? "Kazandınız!" : `${a.takim_sirasi}. sıra`}</h1>
    <p>Takım puanı <b>${v.takim.puan}</b> · senin puanın <b>${v.ben.puan}</b></p>
    ${(a.rozetler || []).map(r => `<span class="rozet" style="font-size:.9rem">★ ${esc(r.ad)}</span>`).join("")}
  </div></div>
  <div class="kart"><h3>Bu oyunda çalıştığımız kavramlar</h3><ul>${(a.ogrenilenler || []).map(k => `<li>${esc(k)}</li>`).join("")}</ul></div>`;
}

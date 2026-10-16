const SPEKTRUM = ["#D93A26", "#F2B705", "#1F8A4C", "#2448C9"];
const HARFLER = ["A", "B", "C", "D", "E", "F"];

function piramitSvg(boyut, renk, sinif) {
  return `<svg class="piramit ${sinif || ""}" width="${boyut}" height="${boyut}" viewBox="0 0 100 100" aria-hidden="true"${renk ? ` style="--p:${renk}"` : ""}><polygon class="yuz-a" points="50,2 1.6,80 55.8,97.2"/><polygon class="yuz-b" points="50,2 55.8,97.2 98.4,76.6"/><polyline class="kenar" points="1.6,80 50,2 98.4,76.6"/><line class="sirt" x1="50" y1="2" x2="55.8" y2="97.2"/></svg>`;
}

function prizmaSvg(genislik, sinif) {
  const y = Math.round(genislik * 2 / 3);
  return `<svg class="prizma ${sinif || ""}" width="${genislik}" height="${y}" viewBox="0 0 300 200" aria-hidden="true"><line class="prz-isin" x1="4" y1="120" x2="105" y2="120"/>${SPEKTRUM.map((r, i) => `<line class="prz-renk" x1="197" y1="126" x2="294" y2="${62 + i * 40}" stroke="${r}"/>`).join("")}<polygon class="prz-f1" points="150,18 78,182 150,127"/><polygon class="prz-f2" points="150,18 150,127 222,182"/><polygon class="prz-f3" points="78,182 222,182 150,127"/><polyline class="prz-ic" points="105,120 150,127 197,126"/><path class="prz-kesik" d="M150 18 L150 127 M78 182 L150 127 L222 182"/><polygon class="prz-dis" points="150,18 78,182 222,182"/></svg>`;
}

function logoSvg() {
  return `<span class="logo-piramit">${prizmaSvg(66)}</span>`;
}

function takimIkon(t, boyut) {
  return piramitSvg(boyut || 26, t ? t.renk : null);
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function sekil(i) {
  return `<span class="secenek-sekil" aria-hidden="true">${piramitSvg(56, "")}<b>${HARFLER[i] || ""}</b></span>`;
}

function bildir(metin) {
  const eski = document.querySelector(".hata-bildirim");
  if (eski) eski.remove();
  const d = document.createElement("div");
  d.className = "hata-bildirim";
  d.setAttribute("role", "status");
  d.textContent = metin;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 3500);
}

function depoAl(k) {
  try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; }
}

function depoYaz(k, v) {
  try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {}
}

function depoSil(k) {
  try { localStorage.removeItem(k); } catch (e) {}
}

const Saat = {
  bitis: null,
  toplam: null,
  ayarla(kalan, sure) {
    this.bitis = kalan == null ? null : performance.now() + kalan * 1000;
    this.toplam = sure;
  },
  kalan() {
    return this.bitis == null ? null : Math.max(0, (this.bitis - performance.now()) / 1000);
  },
};

function konfeti() {
  const c = document.getElementById("konfeti");
  if (!c || matchMedia("(prefers-reduced-motion: reduce)").matches || document.body.classList.contains("az-hareket")) return;
  const ctx = c.getContext("2d");
  c.width = innerWidth;
  c.height = innerHeight;
  const renk = ["#D93A26", "#F2B705", "#1F8A4C", "#2448C9", "#1B1B1B"];
  const p = Array.from({ length: 160 }, () => ({
    x: Math.random() * c.width, y: -20 - Math.random() * c.height * .5,
    vx: (Math.random() - .5) * 3, vy: 2 + Math.random() * 4, r: Math.random() * Math.PI,
    vr: (Math.random() - .5) * .3, w: 6 + Math.random() * 8, h: 8 + Math.random() * 10, c: renk[Math.floor(Math.random() * renk.length)],
  }));
  const bas = performance.now();
  (function kare(t) {
    ctx.clearRect(0, 0, c.width, c.height);
    p.forEach(q => {
      q.x += q.vx; q.y += q.vy; q.r += q.vr; q.vy += .03;
      ctx.save(); ctx.translate(q.x, q.y); ctx.rotate(q.r); ctx.fillStyle = q.c; ctx.beginPath(); ctx.moveTo(0, -q.h / 2); ctx.lineTo(q.w / 2, q.h / 2); ctx.lineTo(-q.w / 2, q.h / 2); ctx.closePath(); ctx.fill(); ctx.restore();
    });
    if (t - bas < 5000) requestAnimationFrame(kare); else ctx.clearRect(0, 0, c.width, c.height);
  })(bas);
}

function harfBul(liste, i) {
  const k = (liste || []).findIndex(o => o.i === i);
  return k < 0 ? "?" : HARFLER[k];
}

function metinBul(liste, i) {
  const o = (liste || []).find(o => o.i === i);
  return o ? o.metin : "";
}

function harfler(liste, c) {
  if (c == null) return "—";
  return Array.isArray(c) ? c.map(x => harfBul(liste, x)).join(" + ") : harfBul(liste, c);
}

const SAHNE_GORSEL = {
  prizma: `
<svg viewBox="0 0 930 360" role="img" aria-label="Tek bir ışın prizmaya girip bireysel, kurumsal ve sistemik olmak üzere üç ışına ayrılıyor">
  <line class="isin" x1="20" y1="190" x2="330" y2="190" stroke="#161B3D" stroke-width="6" stroke-linecap="round"/>
  <polygon class="belir" style="animation-delay:.6s" points="400,40 300,300 500,300" fill="#fff" stroke="#161B3D" stroke-width="4" stroke-linejoin="round"/>
  <text class="belir" style="animation-delay:.9s" x="400" y="235" text-anchor="middle" font-family="var(--baslik)" font-weight="800" font-size="30" fill="#161B3D">PEAIL</text>
  <line class="isin" style="animation-delay:1.3s" x1="455" y1="170" x2="760" y2="70" stroke="#D93A26" stroke-width="10" stroke-linecap="round"/>
  <line class="isin" style="animation-delay:1.6s" x1="465" y1="190" x2="760" y2="185" stroke="#1F8A4C" stroke-width="10" stroke-linecap="round"/>
  <line class="isin" style="animation-delay:1.9s" x1="470" y1="210" x2="760" y2="300" stroke="#2448C9" stroke-width="10" stroke-linecap="round"/>
  <text class="belir" style="animation-delay:2.4s" x="770" y="60" font-size="26" font-weight="700" fill="#D93A26">Bireysel</text>
  <text class="belir" style="animation-delay:2.6s" x="770" y="178" font-size="26" font-weight="700" fill="#1F8A4C">Kurumsal</text>
  <text class="belir" style="animation-delay:2.8s" x="770" y="318" font-size="26" font-weight="700" fill="#2448C9">Sistemik</text>
</svg>`,
  kilit: `
<svg viewBox="0 0 820 360" role="img" aria-label="Disiplin, okul yerleştirmesi ve yüksek riskli değerlendirmeler kilitli; YZ önerisi insan kararından geçiyor ve gerekçe belgeleniyor">
  <g font-size="22" font-weight="700" text-anchor="middle">
    <g class="belir" style="animation-delay:.2s"><rect x="40" y="40" width="220" height="130" rx="18" fill="#fff" stroke="#161B3D" stroke-width="3"/><text x="150" y="98" fill="#161B3D">Disiplin</text><text x="150" y="140" font-size="34">🔒</text></g>
    <g class="belir" style="animation-delay:.6s"><rect x="300" y="40" width="220" height="130" rx="18" fill="#fff" stroke="#161B3D" stroke-width="3"/><text x="410" y="98" fill="#161B3D">Okul yerleştirmesi</text><text x="410" y="140" font-size="34">🔒</text></g>
    <g class="belir" style="animation-delay:1s"><rect x="560" y="40" width="220" height="130" rx="18" fill="#fff" stroke="#161B3D" stroke-width="3"/><text x="670" y="90" fill="#161B3D">Yüksek riskli</text><text x="670" y="116" fill="#161B3D">değerlendirmeler</text><text x="670" y="152" font-size="34">🔒</text></g>
  </g>
  <g class="belir" style="animation-delay:1.8s" font-size="22" font-weight="700">
    <rect x="80" y="240" width="160" height="70" rx="35" fill="#E8EDF8"/><text x="160" y="283" text-anchor="middle" fill="#2448C9">YZ önerisi</text>
    <line x1="250" y1="275" x2="350" y2="275" stroke="#161B3D" stroke-width="4" marker-end="url(#ok)"/>
    <rect x="360" y="240" width="160" height="70" rx="35" fill="#161B3D"/><text x="440" y="283" text-anchor="middle" fill="#fff">İnsan kararı</text>
    <line x1="530" y1="275" x2="610" y2="275" stroke="#161B3D" stroke-width="4" marker-end="url(#ok)"/>
    <rect x="620" y="240" width="170" height="70" rx="12" fill="#FFF4DC" stroke="#C98A00" stroke-width="3"/><text x="705" y="270" text-anchor="middle" fill="#6B4300">Gerekçe</text><text x="705" y="296" text-anchor="middle" fill="#6B4300">belgelenir</text>
  </g>
  <defs><marker id="ok" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#161B3D"/></marker></defs>
</svg>`,
  ikiyon: `
<svg viewBox="0 0 820 360" role="img" aria-label="Ahlaki kişi ve ahlaki yönetici olmak üzere etik liderliğin iki yönü">
  <g class="belir" style="animation-delay:.2s">
    <circle cx="270" cy="180" r="150" fill="#D93A26" fill-opacity=".12" stroke="#D93A26" stroke-width="4"/>
    <text x="230" y="120" text-anchor="middle" font-size="28" font-weight="800" fill="#D93A26">Ahlaki kişi</text>
    <text x="220" y="175" text-anchor="middle" font-size="22" fill="#161B3D">dürüstlük</text>
    <text x="220" y="210" text-anchor="middle" font-size="22" fill="#161B3D">güvenilirlik</text>
    <text x="220" y="245" text-anchor="middle" font-size="22" fill="#161B3D">empati</text>
  </g>
  <g class="belir" style="animation-delay:1s">
    <circle cx="550" cy="180" r="150" fill="#2448C9" fill-opacity=".12" stroke="#2448C9" stroke-width="4"/>
    <text x="595" y="120" text-anchor="middle" font-size="28" font-weight="800" fill="#2448C9">Ahlaki yönetici</text>
    <text x="600" y="175" text-anchor="middle" font-size="22" fill="#161B3D">iletişim</text>
    <text x="600" y="210" text-anchor="middle" font-size="22" fill="#161B3D">rol modelliği</text>
    <text x="600" y="245" text-anchor="middle" font-size="22" fill="#161B3D">hesap verebilirlik</text>
  </g>
</svg>`,
  kirilma: `
<svg viewBox="0 0 820 360" role="img" aria-label="Altı evre bir çizgi üzerinde, ardından bir kırılma ve İnsan-YZ Ortak Yaşamı merceği">
  <line class="isin" x1="40" y1="180" x2="500" y2="180" stroke="#161B3D" stroke-width="5"/>
  <g font-size="22" font-weight="700" text-anchor="middle" fill="#fff">
    ${[0,1,2,3,4,5].map(i => `<g class="belir" style="animation-delay:${.3 + i * .2}s"><circle cx="${70 + i * 80}" cy="180" r="26" fill="#161B3D"/><text x="${70 + i * 80}" y="188">${i + 1}</text></g>`).join("")}
  </g>
  <path class="isin" style="animation-delay:1.8s" d="M545 70 L520 140 L560 180 L515 230 L545 300" fill="none" stroke="#D93A26" stroke-width="7" stroke-linejoin="round"/>
  <g class="belir" style="animation-delay:2.4s">
    <circle cx="680" cy="170" r="80" fill="#fff" stroke="#2448C9" stroke-width="8"/>
    <line x1="737" y1="227" x2="790" y2="290" stroke="#2448C9" stroke-width="12" stroke-linecap="round"/>
    <text x="680" y="162" text-anchor="middle" font-size="22" font-weight="800" fill="#2448C9">İnsan-YZ</text>
    <text x="680" y="190" text-anchor="middle" font-size="20" font-weight="700" fill="#2448C9">ortak yaşamı</text>
  </g>
  <text class="belir" style="animation-delay:1s" x="270" y="250" text-anchor="middle" font-size="20" fill="#565F82">Ahmed'in (2025) altı evresi</text>
</svg>`,
  halka: `
<svg viewBox="0 0 880 380" role="img" aria-label="Merkezde sosyo-teknik vasi olarak müdür, çevresinde dört alan, en dışta dış yönetişim ortamı">
  <circle class="belir" style="animation-delay:1.6s" cx="410" cy="190" r="180" fill="#2448C9" fill-opacity=".08" stroke="#2448C9" stroke-width="3" stroke-dasharray="8 8"/>
  <circle class="belir" style="animation-delay:.8s" cx="410" cy="190" r="118" fill="#fff" stroke="#2448C9" stroke-width="3"/>
  <circle class="belir" style="animation-delay:.2s" cx="410" cy="190" r="58" fill="#161B3D"/>
  <text class="belir" style="animation-delay:.3s" x="410" y="186" text-anchor="middle" font-size="20" font-weight="800" fill="#fff">Müdür</text>
  <text class="belir" style="animation-delay:.3s" x="410" y="210" text-anchor="middle" font-size="14" fill="#fff">sosyo-teknik vasi</text>
  <g class="belir" style="animation-delay:1s" font-size="16" font-weight="700" fill="#2448C9" text-anchor="middle">
    <text x="410" y="105">Zorluklar</text><text x="500" y="196">Stratejiler</text><text x="410" y="288">Çıktılar</text><text x="320" y="196">Faktörler</text>
  </g>
  <g class="belir" style="animation-delay:1.9s" font-size="17" font-weight="700" fill="#2448C9">
    <text x="60" y="60">Tedarikçi gücü</text><text x="610" y="60">Opak algoritmalar</text>
    <text x="30" y="340">Uluslararası düzenlemeler</text><text x="600" y="340">Küresel değerler / SKA'lar</text>
  </g>
</svg>`,
};

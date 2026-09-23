/* Landing hero illustration — redrawn from the reference: wind turbines, solar homes,
   charger + EV, fireflies and a grainy violet dusk. Generated so it stays crisp at any size. */
const BRAND_MARK = `<svg class="brand-mark" viewBox="0 0 34 34" aria-hidden="true"><circle cx="17" cy="17" r="13" fill="none" stroke="currentColor" stroke-width="3.4" stroke-dasharray="64 18" stroke-linecap="round" transform="rotate(-72 17 17)"/><path d="M18.6 7.5 11 18.6h5.2L15.2 26.5 23 15.3h-5.2z" fill="#f5b041"/></svg>`;

function heroArt() {
  const turbine = (x, y, s, cls, col) => `<g class="turb ${cls}" transform="translate(${x} ${y}) scale(${s})">
    <path d="M-4.4 300 L4.4 300 L1.7 0 L-1.7 0Z" fill="${col}"/>
    <g class="blades">${[0, 120, 240].map(a => `<path transform="rotate(${a})" d="M0 -3 C-7 -20 -5 -52 0 -94 C5 -52 7 -20 0 -3Z" fill="${col}"/>`).join('')}</g>
    <circle r="5.5" fill="${col}"/></g>`;
  const tree = cs => cs.map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r + 8}" fill="#e2a72c"/>`).join('') + cs.map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="#70401d"/>`).join('') + cs.map(([x, y, r]) => `<circle cx="${x - r * .28}" cy="${y - r * .3}" r="${r * .55}" fill="#8a5222" opacity=".55"/>`).join('');
  const house = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s})">
    <rect x="158" y="-2" width="30" height="58" fill="#c9581c"/><rect x="154" y="-8" width="38" height="12" fill="#e98a2e"/>
    <rect x="0" y="100" width="230" height="150" fill="#f2b96e"/>
    <polygon points="0,102 115,10 230,102" fill="#f2b96e"/>
    <rect x="0" y="100" width="230" height="150" fill="url(#wallShade)"/>
    <polyline points="-14,110 115,-6 244,110" fill="none" stroke="#d9682a" stroke-width="28" stroke-linejoin="round" stroke-linecap="round"/>
    <polyline points="-14,122 115,6 244,122" fill="none" stroke="#f0a83a" stroke-width="5" stroke-linejoin="round" stroke-linecap="round" opacity=".9"/>
    <g transform="translate(9 88) rotate(-41.5)"><rect x="0" y="-12" width="104" height="24" rx="2" fill="#27216d" stroke="#9a96ec" stroke-width="1.6"/>
      ${[17, 34, 51, 68, 85].map(v => `<line x1="${v}" x2="${v}" y1="-12" y2="12" stroke="#6764c8" stroke-width="1.2"/>`).join('')}<line x1="0" x2="104" y1="0" y2="0" stroke="#6764c8" stroke-width="1.2"/></g>
    <rect x="118" y="126" width="84" height="70" rx="3" fill="#e0752b"/>
    ${[0, 1, 2].map(c => [0, 1].map(rw => `<rect x="${123 + c * 25.5}" y="${131 + rw * 32}" width="22" height="28" fill="#b9b3ee"/>`).join('')).join('')}
    <rect x="34" y="150" width="46" height="100" rx="3" fill="#dc6427"/><circle cx="72" cy="202" r="3" fill="#f5c860"/>
  </g>`;
  const leaf = (x, y, h, rot, c) => `<path transform="translate(${x} ${y}) rotate(${rot})" d="M0 0 C-${h * .32} -${h * .4} -${h * .18} -${h * .8} 0 -${h} C${h * .18} -${h * .8} ${h * .32} -${h * .4} 0 0Z" fill="${c}"/>`;
  const ff = [[212, 615, 0], [345, 640, 1.2], [648, 610, 2.1], [880, 606, 0.6], [952, 630, 1.8], [420, 585, 2.6], [120, 600, 3], [1090, 622, 1.4], [760, 640, 2.3], [560, 648, 0.3]]
    .map(([x, y, d]) => `<circle class="ff" cx="${x}" cy="${y}" r="3.2" fill="#ffe7a0" style="animation-delay:${d}s"/><circle cx="${x}" cy="${y}" r="9" fill="#ffe7a0" opacity=".12"/>`).join('');
  const spokes = [0, 72, 144, 216, 288].map(a => `<rect x="-3" y="-30" width="6" height="30" rx="2" fill="#2a2660" transform="rotate(${a})"/>`).join('');
  const wheel = (cx, cy) => `<g transform="translate(${cx} ${cy})"><circle r="53" fill="#231b58"/><circle r="45" fill="#15122f"/><circle r="32" fill="#c3c2d6"/><circle r="32" fill="url(#rim)"/>${spokes}<circle r="8" fill="#f1f0ff"/></g>`;

  return `<svg viewBox="0 0 1200 680" preserveAspectRatio="xMidYMax slice" role="img" aria-label="Illustration: wind turbines, solar-roofed homes and an electric car charging at dusk">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8e79d2"/><stop offset=".45" stop-color="#7a66c6"/><stop offset=".72" stop-color="#6553b4"/><stop offset="1" stop-color="#3f2f8c"/></linearGradient>
    <radialGradient id="sun" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#efe6ff" stop-opacity=".55"/><stop offset="1" stop-color="#efe6ff" stop-opacity="0"/></radialGradient>
    <linearGradient id="hill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6553b6"/><stop offset="1" stop-color="#4a3a9a"/></linearGradient>
    <linearGradient id="road" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a2b80"/><stop offset="1" stop-color="#241a5a"/></linearGradient>
    <linearGradient id="car" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b8b8f6"/><stop offset="1" stop-color="#8f8fe0"/></linearGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity=".55"/><stop offset="1" stop-color="#6d6a92" stop-opacity=".5"/></linearGradient>
    <linearGradient id="wallShade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#c46a25" stop-opacity=".0"/><stop offset="1" stop-color="#c46a25" stop-opacity=".35"/></linearGradient>
    <filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .9 -.32"/></filter>
    <filter id="soft"><feGaussianBlur stdDeviation="14"/></filter>
  </defs>
  <rect width="1200" height="680" fill="url(#sky)"/>
  <circle cx="150" cy="70" r="150" fill="url(#sun)"/>
  <path d="M0 348 L96 280 L170 322 L285 214 L392 318 L472 268 L582 344 L690 300 L760 352 L760 440 L0 440Z" fill="#b1a4e6" opacity=".5"/>
  <path d="M0 372 L140 318 L250 356 L372 292 L470 360 L610 322 L740 372 L740 440 L0 440Z" fill="#9887d6" opacity=".55"/>
  ${turbine(84, 178, .95, 't1', '#33296f')}${turbine(196, 232, .74, 't2', '#42367f')}${turbine(342, 168, 1.02, 't3', '#2c2367')}${turbine(432, 248, .7, 't4', '#42367f')}
  ${tree([[798, 128, 56], [850, 84, 52], [764, 176, 42], [838, 176, 58], [886, 146, 46]])}
  ${tree([[1000, 116, 60], [1052, 74, 54], [1104, 122, 58], [1030, 168, 52], [1088, 172, 44]])}
  ${tree([[1172, 150, 48], [1150, 200, 44], [1190, 96, 40]])}
  ${house(686, 214, 1)}${house(922, 168, 1.12)}
  <path d="M0 468 C160 428 380 418 640 428 S1000 420 1200 424 L1200 690 L0 690Z" fill="url(#hill)"/>
  <path d="M0 592 C260 576 640 584 1200 572 L1200 690 L0 690Z" fill="url(#road)"/>
  <ellipse cx="960" cy="612" rx="290" ry="12" fill="#1b1246" opacity=".55"/>
  <!-- charger -->
  <g transform="translate(646 384)">
    <ellipse cx="31" cy="202" rx="60" ry="9" fill="#21174f" opacity=".6"/>
    <rect x="-14" y="188" width="90" height="14" rx="4" fill="#7b5bc4"/>
    <rect x="0" y="0" width="62" height="196" rx="12" fill="#5b3a93"/><rect x="0" y="0" width="62" height="42" rx="12" fill="#3f2672"/>
    <rect x="11" y="58" width="40" height="70" rx="8" fill="#241650"/><path d="M35 66 21 95h9l-4 24 16-30H32z" fill="#cdb9ff"/>
    <rect x="10" y="142" width="42" height="6" rx="3" fill="#7d5dbb"/><rect x="10" y="154" width="26" height="6" rx="3" fill="#7d5dbb" opacity=".6"/>
  </g>
  <path d="M708 410 C770 402 722 505 746 546" fill="none" stroke="#9b5db3" stroke-width="6.5" stroke-linecap="round"/>
  <!-- EV -->
  <g transform="translate(725 456)">
    <path d="M0 102 C0 78 24 66 64 58 L120 24 C154 6 236 2 286 10 L340 48 C384 54 424 66 452 88 L470 98 L470 122 L0 122Z" fill="url(#car)" stroke="#dfe2ff" stroke-width="3" stroke-linejoin="round"/>
    <path d="M112 50 L150 22 Q172 12 218 12 L221 50Z" fill="#e3e6ff" opacity=".55"/><path d="M231 12 Q272 12 296 22 L332 50 L231 50Z" fill="#e3e6ff" opacity=".55"/>
    <path d="M225 50 L225 108 M212 66 h16" stroke="#dfe2ff" stroke-width="2.6" fill="none" stroke-linecap="round" opacity=".9"/>
    <path d="M26 92 C60 80 110 80 150 84" stroke="#e8eaff" stroke-width="2.4" fill="none" opacity=".7"/>
    <path d="M330 62 C372 66 410 76 440 94" stroke="#e8eaff" stroke-width="2.4" fill="none" opacity=".6"/>
    ${wheel(100, 118)}${wheel(382, 118)}
  </g>
  <!-- foreground -->
  ${leaf(48, 700, 130, -18, '#2b2775')}${leaf(80, 700, 168, 4, '#3a3488')}${leaf(112, 700, 116, 24, '#2b2775')}${leaf(20, 700, 96, -38, '#4a43a0')}
  ${leaf(1150, 700, 120, -10, '#2b2775')}${leaf(1180, 700, 96, 18, '#3a3488')}
  <path d="M0 640 C90 622 150 640 220 650 L220 700 L0 700Z" fill="#2c2273" opacity=".7"/>
  <ellipse cx="18" cy="662" rx="46" ry="26" fill="#7b6c99" opacity=".8"/><ellipse cx="1176" cy="670" rx="58" ry="30" fill="#5a3a7a" opacity=".85"/>
  ${ff}
  <rect width="1200" height="680" filter="url(#grain)" opacity=".38" style="mix-blend-mode:soft-light"/>
  </svg>`;
}

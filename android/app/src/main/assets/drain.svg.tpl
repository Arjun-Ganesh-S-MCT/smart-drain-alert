<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 220" width="560" height="220">
 <defs>
  <linearGradient id="dSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9ccbe8"/><stop offset="1" stop-color="#d7ebf5"/></linearGradient>
  <linearGradient id="dSoil" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8b6b4a"/><stop offset=".55" stop-color="#6e5238"/><stop offset="1" stop-color="#4f3a27"/></linearGradient>
  <linearGradient id="dConc" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#9ea3a7"/><stop offset=".5" stop-color="#c3c7ca"/><stop offset="1" stop-color="#8f9498"/></linearGradient>
  <linearGradient id="dConcV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c9cdd0"/><stop offset="1" stop-color="#8b9094"/></linearGradient>
  <linearGradient id="dBore" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#14181b"/><stop offset="1" stop-color="#2c343a"/></linearGradient>
  <linearGradient id="dChamber" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#101417"/><stop offset="1" stop-color="#27313a"/></linearGradient>
  <linearGradient id="wg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{{WG1}}"/><stop offset="1" stop-color="{{WG2}}"/></linearGradient>
  <linearGradient id="dSteel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9dde0"/><stop offset=".5" stop-color="#9aa1a6"/><stop offset="1" stop-color="#6d7479"/></linearGradient>
  <radialGradient id="dDebris" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="#a98a5e"/><stop offset=".6" stop-color="#6f5638"/><stop offset="1" stop-color="#3f2f1f"/></radialGradient>
  
  
 </defs>
 
 <rect x="0" y="0" width="560" height="30" fill="url(#dSky)" opacity=".55"/>
 <rect x="0" y="44" width="560" height="176" fill="url(#dSoil)"/>
 
 <path d="M0 74 C80 68 140 82 220 76 S400 70 560 78" fill="none" stroke="#00000030" stroke-width="2"/>
 <path d="M0 190 C90 184 170 196 260 189 S440 184 560 192" fill="none" stroke="#00000030" stroke-width="2"/>
 <rect x="0" y="28" width="560" height="16" fill="#3a3d40"/>
 <rect x="0" y="28" width="560" height="3" fill="#55595d"/>
 <path d="M170 36 H210 M250 36 H290 M330 36 H370 M410 36 H450 M490 36 H530" stroke="#e8e2c8" stroke-width="2" stroke-dasharray="14 10" opacity=".7"/>
 <rect x="0" y="24" width="14" height="6" rx="1.5" fill="#b6b9bc"/>
 
 <rect x="23" y="30" width="114" height="139" fill="url(#dChamber)"/>
 <rect x="14" y="28" width="9" height="150" fill="url(#dConc)"/>
 <rect x="137" y="28" width="9" height="90" fill="url(#dConc)"/>
 <rect x="137" y="160" width="9" height="18" fill="url(#dConc)"/>
 <rect x="14" y="168" width="132" height="12" fill="url(#dConcV)"/>
 
 <g>
  <path d="{{WATER}}" fill="url(#wg)" opacity=".92"/>
  <g fill="#ffffff"><circle cx="48" cy="{{B1Y}}" r="2" opacity="{{B1O}}"/><circle cx="96" cy="{{B2Y}}" r="1.6" opacity="{{B2O}}"/><circle cx="118" cy="{{B3Y}}" r="2.2" opacity="{{B3O}}"/></g>
  <rect x="23" y="30" width="114" height="139" fill="url(#dChamber)" opacity="0" />
 </g>
 <path d="{{SURF}}" fill="none" stroke="#ffffff" stroke-width="1.6" opacity=".55" stroke-linejoin="round"/>
 <g fill="#8cc8f0">{{DROPS}}</g>
 
 <rect x="26" y="26" width="108" height="8" rx="1.5" fill="#26292b"/>
 <g stroke="#7d8388" stroke-width="3"><path d="M34 26 V34 M46 26 V34 M58 26 V34 M70 26 V34 M82 26 V34 M94 26 V34 M106 26 V34 M118 26 V34 M130 26 V34"/></g>
 
 <g>
  <rect x="27" y="34" width="7" height="118" rx="2" fill="url(#dSteel)" stroke="#5a6065"/>
  <rect x="34" y="125.3" width="16" height="3" rx="1.5" fill="#cbd2d6"/><circle cx="54" cy="126.8" r="3.6" fill="#4ade80" stroke="#ffffff66" opacity="{{P1}}"/>
  <rect x="34" y="87.8" width="16" height="3" rx="1.5" fill="#cbd2d6"/><circle cx="54" cy="89.3" r="3.6" fill="#fbbf24" stroke="#ffffff66" opacity="{{P2}}"/>
  <rect x="34" y="50.3" width="16" height="3" rx="1.5" fill="#cbd2d6"/><circle cx="54" cy="51.8" r="3.6" fill="#ef4444" stroke="#ffffff66" opacity="{{P3}}"/>
 </g>
  <rect x="124" y="82" width="4" height="62" rx="2" fill="url(#dSteel)"/><rect x="120" y="140" width="12" height="9" rx="2.5" fill="#2a3035" stroke="#aab0b4"/>
 <circle cx="126" cy="144.5" r="2" fill="#fde68a" opacity="{{LED}}"/>
 
 <rect x="146" y="116" width="414" height="44" fill="url(#dConcV)"/>
 <rect x="146" y="123" width="414" height="30" fill="url(#dBore)"/>
 <rect x="146" y="139" width="414" height="14" fill="url(#wg)" opacity=".85"/>
 <path d="M150 142 H556" fill="none" stroke="#bfe6fb" stroke-width="2.4" stroke-linecap="round" opacity=".8" stroke-dasharray="10 8" stroke-dashoffset="{{PIPE}}"/>
 <path d="M150 148 H556" fill="none" stroke="#bfe6fb" stroke-width="1.6" stroke-linecap="round" opacity=".55" stroke-dasharray="10 8" stroke-dashoffset="{{PIPE2}}"/>
 <g fill="#00000033"><rect x="230" y="116" width="5" height="44"/><rect x="330" y="116" width="5" height="44"/><rect x="500" y="116" width="5" height="44"/></g>
 <rect x="146" y="116" width="414" height="3" fill="#ffffff55"/>
 
 <rect x="262" y="104" width="46" height="14" rx="3" fill="url(#dSteel)" stroke="#5a6065"/><rect x="262" y="154" width="46" height="9" rx="3" fill="url(#dSteel)" stroke="#5a6065"/>
 <circle cx="272" cy="111" r="2" fill="#4ade80" opacity="{{LED}}"/><path d="M285 111 H302" stroke="#3a4146" stroke-width="2"/>
 
 <g><rect x="376" y="104" width="30" height="14" rx="3" fill="url(#dSteel)" stroke="#5a6065"/><rect x="388" y="86" width="6" height="18" fill="#8b9296"/><ellipse cx="391" cy="84" rx="16" ry="4.5" fill="none" stroke="#c0452f" stroke-width="3.5"/><circle cx="391" cy="84" r="2.5" fill="#c0452f"/></g>
 
 <g opacity="{{DEBRIS}}">
  <path d="M424 150 Q432 124 452 128 Q468 134 466 152 Z" fill="url(#dDebris)"/>
  <path d="M428 136 Q440 122 460 134 L452 146 Z" fill="#d9d4c2" opacity=".8"/>
  <rect x="446" y="136" width="18" height="6" rx="3" fill="#e9695c" transform="rotate(-24 455 139)"/>
  <circle cx="436" cy="148" r="3" fill="#2f2417"/><circle cx="462" cy="147" r="2.6" fill="#2f2417"/>
  <text x="418" y="176" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">BLOCKAGE</text><text x="418" y="176" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="#ffffff">BLOCKAGE</text>
 </g>
 
 
 <g><rect x="196" y="22" width="40" height="8" rx="2" fill="#4a5056" stroke="#8a9096"/><path d="M200 26 H232" stroke="#8cc8f0" stroke-width="2" stroke-linecap="round" opacity="{{WET}}"/></g>
 
 <text x="34" y="22" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">LEVEL PROBES</text><text x="34" y="22" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="#ffffff">LEVEL PROBES</text><text x="196" y="18" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">RAIN PLATE</text><text x="196" y="18" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="#ffffff">RAIN PLATE</text><text x="258" y="98" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">FLOW SENSOR</text><text x="258" y="98" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="#ffffff">FLOW SENSOR</text><text x="368" y="72" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">VALVE</text><text x="368" y="72" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="#ffffff">VALVE</text><text x="28" y="196" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">CATCH BASIN</text><text x="28" y="196" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="#ffffff">CATCH BASIN</text><text x="150" y="108" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">TURBIDITY</text><text x="150" y="108" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="#ffffff">TURBIDITY</text><text x="480" y="108" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">TO SEWER</text><text x="480" y="108" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4" fill="#ffffff">TO SEWER</text>
 <path d="M520 132 l12 0 m-5 -5 l5 5 l-5 5" fill="none" stroke="#bfe6fb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity=".7"/>
</svg>
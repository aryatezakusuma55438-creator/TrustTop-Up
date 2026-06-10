// ============ STARS ============
const starsContainer = document.getElementById('stars-container');
if (starsContainer) {
  for (let i = 0; i < 80; i++) {
    const star = document.createElement('div');
    star.classList.add('star');
    const size = Math.random() * 3 + 1;
    star.style.cssText = `width:${size}px;height:${size}px;top:${Math.random()*100}%;left:${Math.random()*100}%;animation-delay:${Math.random()*3}s;animation-duration:${1.5+Math.random()*2}s;`;
    starsContainer.appendChild(star);
  }
}

// ============ INTRO ============
const introEl = document.getElementById('intro');
if (introEl) {
  const scenes  = ['scene-face','scene-diamond','scene-text1','scene-text2'];
  const timings = [3000,3000,4000,4500];
  function showScene(idx) {
    scenes.forEach(id => { const el=document.getElementById(id); if(el) el.classList.remove('active'); });
    if (idx >= scenes.length) { endIntro(); return; }
    const el = document.getElementById(scenes[idx]);
    if (el) el.classList.add('active');
    setTimeout(() => { if(el) el.classList.remove('active'); setTimeout(()=>showScene(idx+1),600); }, timings[idx]);
  }
  function endIntro() {
    introEl.style.transition='opacity 0.8s ease'; introEl.style.opacity='0';
    setTimeout(()=>{ introEl.style.display='none'; const m=document.getElementById('main-site'); if(m) m.classList.add('visible'); },800);
  }
  setTimeout(()=>showScene(0),400);
}

// ============ NAV ============
document.addEventListener('click',(e)=>{
  const menu=document.getElementById('dotsMenu');
  const btn=document.getElementById('dotsBtn');
  if(menu&&btn&&!menu.contains(e.target)&&e.target!==btn) menu.classList.remove('open');
});
function toggleMenu() { const m=document.getElementById('dotsMenu'); if(m) m.classList.toggle('open'); }
function scrollToGames() { const el=document.getElementById('games-section'); if(el) el.scrollIntoView({behavior:'smooth'}); }

// ============ GAME CONFIG ============
const GAME_CONFIG = {
  'Mobile Legends': {
    userLabel:'User ID', userPlaceholder:'Contoh: 123456789',
    serverType:'input', serverLabel:'Server ID', serverPlaceholder:'Contoh: 1234',
    packages:[
      {label:'86 Diamond',  price:'Rp 19.000'},
      {label:'172 Diamond', price:'Rp 38.000'},
      {label:'257 Diamond', price:'Rp 57.000'},
      {label:'344 Diamond', price:'Rp 76.000'},
      {label:'514 Diamond', price:'Rp 112.000'},
    ]
  },
  'Free Fire': {
    userLabel:'Player ID', userPlaceholder:'Contoh: 123456789',
    serverType:'none',
    packages:[
      {label:'70 Diamond',  price:'Rp 15.000'},
      {label:'140 Diamond', price:'Rp 29.000'},
      {label:'355 Diamond', price:'Rp 72.000'},
      {label:'720 Diamond', price:'Rp 143.000'},
    ]
  },
  'PUBG Mobile': {
    userLabel:'Character ID', userPlaceholder:'Contoh: 123456789',
    serverType:'none',
    packages:[
      {label:'60 UC',  price:'Rp 15.000'},
      {label:'120 UC', price:'Rp 29.000'},
      {label:'325 UC', price:'Rp 75.000'},
      {label:'660 UC', price:'Rp 149.000'},
    ]
  },
  'Roblox': {
    userLabel:'Username Roblox', userPlaceholder:'Contoh: myusername123',
    serverType:'none',
    packages:[
      {label:'400 Robux',  price:'Rp 55.000'},
      {label:'800 Robux',  price:'Rp 109.000'},
      {label:'1700 Robux', price:'Rp 219.000'},
    ]
  },
  'Genshin Impact': {
    userLabel:'UID', userPlaceholder:'Contoh: 812345678',
    serverType:'select',
    packages:[
      {label:'60 Primogem',  price:'Rp 15.000'},
      {label:'300 Primogem', price:'Rp 75.000'},
      {label:'980 Primogem', price:'Rp 149.000'},
    ]
  },
  'Honkai Star Rail': {
    userLabel:'UID', userPlaceholder:'Contoh: 812345678',
    serverType:'select',
    packages:[
      {label:'60 Stellar Jade',  price:'Rp 15.000'},
      {label:'300 Stellar Jade', price:'Rp 75.000'},
      {label:'980 Stellar Jade', price:'Rp 149.000'},
    ]
  },
};

let currentGame = '';

function renderAmounts(pkgs) {
  const container = document.getElementById('diamond-amounts');
  if (!container) return;
  container.innerHTML = pkgs.map((p,i) =>
    `<button class="amount-btn ${i===0?'selected':''}" onclick="selectAmount(this)"
       data-price="${p.price}" data-label="${p.label}">
      <div style="font-weight:700;color:#f59e0b;">${p.price}</div>
      <div class="amt-diamond">💎 ${p.label}</div>
    </button>`
  ).join('');
}

function selectAmount(btn) {
  document.querySelectorAll('.amount-btn').forEach(b=>b.classList.remove('selected'));
  btn.classList.add('selected');
}

// ============ MODALS ============
function openModal(game) {
  currentGame = game;
  const cfg   = GAME_CONFIG[game] || GAME_CONFIG['Mobile Legends'];

  document.getElementById('modal-game-name').textContent = game;
  const labelUID = document.getElementById('label-user-id');
  if (labelUID) labelUID.textContent = cfg.userLabel;
  const userInput = document.getElementById('user-id');
  if (userInput) { userInput.placeholder=cfg.userPlaceholder; userInput.value=''; userInput.style.borderColor=''; }

  const serverInputWrapper  = document.getElementById('server-id-wrapper');
  const serverSelectWrapper = document.getElementById('server-select-wrapper');
  const serverInput         = document.getElementById('server-id');
  if (serverInput) serverInput.value='';

  if (cfg.serverType==='input') {
    const lbl=document.getElementById('label-server-id');
    if (lbl) lbl.textContent=cfg.serverLabel||'Server ID';
    if (serverInput) serverInput.placeholder=cfg.serverPlaceholder||'';
    if (serverInputWrapper) serverInputWrapper.style.display='';
    if (serverSelectWrapper) serverSelectWrapper.style.display='none';
  } else if (cfg.serverType==='select') {
    if (serverInputWrapper) serverInputWrapper.style.display='none';
    if (serverSelectWrapper) serverSelectWrapper.style.display='';
  } else {
    if (serverInputWrapper) serverInputWrapper.style.display='none';
    if (serverSelectWrapper) serverSelectWrapper.style.display='none';
  }

  renderAmounts(cfg.packages);
  document.getElementById('topup-modal').classList.add('open');
}

function closeModal() {
  const m=document.getElementById('topup-modal'); if(m) m.classList.remove('open');
}
function openDonate(e) {
  if(e) e.preventDefault();
  const menu=document.getElementById('dotsMenu'); if(menu) menu.classList.remove('open');
  const d=document.getElementById('donate-modal'); if(d) d.classList.add('open');
}
function closeDonate() { const d=document.getElementById('donate-modal'); if(d) d.classList.remove('open'); }

const topupModal  = document.getElementById('topup-modal');
const donateModal = document.getElementById('donate-modal');
if (topupModal)  topupModal.addEventListener('click', e=>{ if(e.target===topupModal) closeModal(); });
if (donateModal) donateModal.addEventListener('click', e=>{ if(e.target===donateModal) closeDonate(); });

function highlight(id) {
  const el=document.getElementById(id); if(!el) return;
  el.style.borderColor='#ef4444'; el.focus();
  setTimeout(()=>el.style.borderColor='',2000);
}

function processTopup() {
  const cfg = GAME_CONFIG[currentGame] || GAME_CONFIG['Mobile Legends'];
  const uid = document.getElementById('user-id')?.value.trim();
  if (!uid) { highlight('user-id'); showToast('Masukkan User ID kamu!'); return; }

  let serverId = '';
  if (cfg.serverType==='input') {
    serverId = document.getElementById('server-id')?.value.trim();
    if (!serverId) { highlight('server-id'); showToast('Masukkan Server ID!'); return; }
  } else if (cfg.serverType==='select') {
    serverId = document.getElementById('server-select')?.value||'';
  }

  const selectedBtn = document.querySelector('.amount-btn.selected');
  if (!selectedBtn) { showToast('Pilih jumlah diamond dulu!'); return; }

  const diamond = selectedBtn.dataset.label;
  const price   = selectedBtn.dataset.price;

  // Submit ke Flask — payment "Midtrans" karena semua lewat Midtrans
  const form = document.createElement('form');
  form.method='POST'; form.action='/checkout';

  const fields = {
    game:       currentGame,
    user_id:    uid,
    server_id:  serverId,
    diamond:    diamond,
    price:      price,
    payment:    'Midtrans',
    csrf_token: document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')||''
  };

  for (const [key,val] of Object.entries(fields)) {
    const input=document.createElement('input');
    input.type='hidden'; input.name=key; input.value=val;
    form.appendChild(input);
  }

  document.body.appendChild(form);
  showToast('Memproses pesanan...');
  setTimeout(()=>form.submit(),400);
}

function showToast(msg) {
  const t=document.getElementById('toast'); if(!t) return;
  t.textContent=msg; t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3500);
}

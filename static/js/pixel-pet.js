/**
 * 米豆 MeDou — 全站像素小寵物
 * 單一狀態機引擎，驅動頁面上所有 [data-mipet-root] 節點。
 * 顏色來自 pixel-pet.css 的 CSS 變數，跟隨全站的 .dark（darkMode: class）。
 */

(function() {
  if (window.MiPet) return;

  const config = {
    sleepAfterMs: 60000,
  };

  // 11 格寬的像素小貓：o 身體、e 眼睛、p 腮紅、w 鼻頭、k 嘴／細節
  const W = 11;
  const BASE = [
    '..o.....o..',
    '..oo...oo..',
    '.ooooooooo.',
    'ooooooooooo',
    'ooooooooooo',
    '.ooooooooo.',
    '..ooooooo..',
    '...ooooo...',
  ];
  const MOUTH = {
    smile: { p: [5, 3], k: [4, 5], k2: [5, 5] },
    open:  { p: [5, 3], k: [4, 5], k2: [6, 5] },
    wave:  { k: [4, 5], k2: [5, 5], k3: [6, 5], k4: [7, 5] },
  };
  const COLORS = {
    o: 'var(--mipet-body)',
    e: 'var(--mipet-eye)',
    p: 'var(--mipet-cheek)',
    w: 'var(--mipet-muzzle)',
    k: 'var(--mipet-eye)',
    h: 'var(--mipet-cheek)',
  };
  const LABEL = {
    idle: '閒置中',
    thinking: '思考中…',
    talking: '說話中',
    error: '出錯了',
    sleep: '睡覺中',
  };
  const NAME = '米豆 MeDou';
  const HEART = [[0, 0], [2, 0], [0, 1], [1, 1], [2, 1], [1, 2]];

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function frame(o) {
    o = o || {};
    const rows = BASE.map(r => r.split(''));
    rows[3][1] = 'p';
    rows[3][9] = 'p';
    const eyes = (o.eyes === undefined) ? [2, 8] : o.eyes;
    if (o.x) {
      rows[2][2] = 'e'; rows[3][1] = 'e'; rows[3][3] = 'e'; rows[4][2] = 'e';
      rows[2][8] = 'e'; rows[3][7] = 'e'; rows[3][9] = 'e'; rows[4][8] = 'e';
    } else if (eyes === null) {
      rows[4][2] = 'e';
      rows[4][8] = 'e';
    } else {
      rows[3][eyes[0]] = 'e';
      rows[3][eyes[1]] = 'e';
    }
    if (o.mouth) {
      const m = MOUTH[o.mouth];
      if (m.p) rows[m.p[1]][m.p[0]] = 'w';
      if (m.k) rows[m.k[1]][m.k[0]] = 'k';
      if (m.k2) rows[m.k2[1]][m.k2[0]] = 'k';
      if (m.k3) rows[m.k3[1]][m.k3[0]] = 'k';
      if (m.k4) rows[m.k4[1]][m.k4[0]] = 'k';
    }
    return rows.map(r => r.join(''));
  }

  function svgFor(f, extras) {
    const h = f.length;
    let rects = '';
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < W; x++) {
        const c = COLORS[f[y][x]];
        if (c) rects += `<rect x="${x}" y="${y}" width="1" height="1" fill="${c}"/>`;
      }
    }
    for (const px of extras) {
      rects += `<rect x="${px.x}" y="${px.y}" width="1" height="1" fill="${px.c}"/>`;
    }
    return `<svg viewBox="0 0 ${W} ${h + 1}" role="img" aria-label="${NAME}"><g>${rects}</g></svg>`;
  }

  let state = 'idle';
  let t = 0;
  let look = [2, 8];
  let fx = null; // 瞬態特效 { kind: 'cheer'|'hop'|'hearts'|'stars', left, total, back }
  let errorTimer = null;
  let lastActivity = Date.now();
  let timer = null;
  let chatToggle = null; // 有 AI 聊天時，小版點擊改走這裡（取代隨機反應）
  const roots = [];

  function renderAll() {
    const { f, dy, extras } = computeFrame();
    const svg = svgFor(f, extras);
    const label = LABEL[state];
    for (const r of roots) {
      r.box.dataset.state = state;
      r.sprite.innerHTML = svg;
      const svgEl = r.sprite.firstChild;
      if (svgEl) {
        const unit = (r.sprite.clientWidth || 44) / W;
        svgEl.style.transform = dy ? `translateY(${(dy * unit).toFixed(1)}px)` : '';
      }
      // 地面陰影跟著浮動縮放
      const sc = dy < 0 ? 1 + dy * 0.25 : 1 - dy * 0.2;
      r.shadow.style.transform = `scaleX(${sc})`;
      r.shadow.style.opacity = dy < 0 ? 0.09 : 0.14;
      if (r.status) r.status.textContent = label;
    }
  }

  function computeFrame() {
    let dy = 0;
    const extras = [];
    let f;
    if (state === 'sleep') {
      f = frame({ eyes: null, mouth: 'smile' });
      if (!reduce) dy = t % 16 < 8 ? 0 : -0.5;
    } else if (state === 'thinking') {
      f = frame({ eyes: [3, 9], mouth: 'smile' });
      if (!reduce) dy = -0.5;
    } else if (state === 'talking') {
      f = frame({ eyes: [2, 8], mouth: t % 4 < 2 ? 'open' : 'smile' });
      if (!reduce) dy = t % 3 === 2 ? -1 : 0;
    } else if (state === 'error') {
      f = frame({ x: true, mouth: 'wave' });
      if (!reduce) dy = 0.5;
    } else {
      if (t % 17 === 12) look = [1, 7];
      if (t % 17 === 14) look = [3, 9];
      if (t % 17 === 16) look = [2, 8];
      const blink = t % 9 === 8 || Math.floor(t / 20) % 11 === 9;
      if (!reduce && t % 7 === 3 && Math.random() < 0.4) {
        extras.push({ x: Math.random() < 0.5 ? 0 : 10, y: 1 + Math.floor(Math.random() * 3), c: COLORS.p });
      }
      f = frame({ eyes: blink ? null : look, mouth: 'smile' });
      if (!reduce) dy = t % 8 < 4 ? 0 : -0.5;
    }
    if (fx) {
      const el = fx.total - fx.left;
      if (fx.kind === 'cheer' || fx.kind === 'hop') {
        if (!reduce) dy = el % 2 === 0 ? -1 : 0;
      }
      if (fx.kind === 'cheer' || fx.kind === 'hearts') {
        const show = el % 4;
        for (const [cx, on] of [[0, show < 2], [8, show >= 2]]) {
          if (!on) continue;
          for (const [dx, dyi] of HEART) extras.push({ x: cx + dx, y: dyi, c: COLORS.h });
        }
      }
      if (fx.kind === 'stars') {
        extras.push(reduce
          ? { x: 10, y: 1, c: COLORS.p }
          : { x: Math.random() < 0.5 ? 0 : 10, y: 1 + Math.floor(Math.random() * 3), c: COLORS.p });
      }
    }
    return { f, dy, extras };
  }

  function setState(s) {
    if (!LABEL[s] || s === state) return;
    state = s;
    t = 0;
    fx = null;
    if (errorTimer) { clearTimeout(errorTimer); errorTimer = null; }
    if (s === 'error') {
      errorTimer = setTimeout(() => {
        errorTimer = null;
        if (state === 'error') setState('idle');
      }, 2500);
    }
    renderAll();
  }

  function wake() {
    if (state !== 'sleep') return;
    state = 'idle';
    t = 0;
    fx = { kind: 'hop', left: 4, total: 4, back: null };
    renderAll();
  }

  function cheer() {
    // 一律回 idle：error 也不例外，否則 errorTimer 被清掉後會卡在 error
    state = 'idle';
    t = 0;
    fx = { kind: 'cheer', left: 10, total: 10, back: null };
    if (errorTimer) { clearTimeout(errorTimer); errorTimer = null; }
    renderAll();
  }

  function pet() {
    wake();
    if (state === 'error') return;
    const kinds = ['hop', 'hearts', 'stars'];
    fx = { kind: kinds[Math.floor(Math.random() * kinds.length)], left: 8, total: 8, back: null };
    renderAll();
  }

  function tick() {
    t++;
    if (fx) {
      fx.left--;
      if (fx.left <= 0) {
        const back = fx.back;
        fx = null;
        if (back && back !== state) {
          state = back;
          t = 0;
        }
      }
    }
    if (state !== 'sleep' && Date.now() - lastActivity >= config.sleepAfterMs) {
      state = 'sleep';
      t = 0;
      fx = null;
    }
    renderAll();
  }

  function stopTick() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  function startTick() {
    if (!timer) timer = setInterval(tick, reduce ? 700 : 350);
  }

  function onActivity() {
    lastActivity = Date.now();
    if (state === 'sleep') wake();
  }
  ['pointerdown', 'keydown', 'touchstart'].forEach(ev => {
    window.addEventListener(ev, onActivity, { passive: true });
  });
  // scroll 不會冒泡，要 capture 才收得到內部容器（如聊天訊息區）的捲動
  window.addEventListener('scroll', onActivity, { passive: true, capture: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopTick();
    } else {
      startTick();
      lastActivity = Date.now();
      renderAll();
    }
  });

  function buildRoot(el) {
    const large = el.getAttribute('data-mipet-size') === 'large';
    const box = document.createElement('div');
    box.className = 'mipet ' + (large ? 'mipet--large' : 'mipet--small');
    box.innerHTML =
      '<div class="mipet-col">' +
        '<div class="mipet-thought" aria-hidden="true"><i></i><i></i><i></i></div>' +
        '<div class="mipet-zzz" aria-hidden="true"><span>z</span><span>z</span><span>z</span></div>' +
        '<div class="mipet-sprite"></div>' +
        '<div class="mipet-shadow"></div>' +
      '</div>' +
      (large
        ? '<div class="mipet-meta"><div class="mipet-name">' + NAME + '</div><div class="mipet-status"></div></div>'
        : '');
    if (!large) {
      box.setAttribute('role', 'button');
      box.setAttribute('tabindex', '0');
      box.setAttribute('aria-label', NAME + '，點擊逗逗我');
      const activate = () => (chatToggle ? chatToggle() : pet());
      box.addEventListener('click', activate);
      box.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          activate();
        }
      });
    }
    el.appendChild(box);
    roots.push({
      box,
      sprite: box.querySelector('.mipet-sprite'),
      shadow: box.querySelector('.mipet-shadow'),
      status: large ? box.querySelector('.mipet-status') : null,
      small: !large,
    });
  }

  function init() {
    const els = document.querySelectorAll('[data-mipet-root]');
    for (const el of els) buildRoot(el);
    renderAll();
    startTick();
  }
  // DOMContentLoaded 而非直接執行：聊天視窗的大版根節點在腳本之後才解析
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.MiPet = {
    setState(s) { setState(s); },
    cheer() { cheer(); },
    bindOpenChat(fn) {
      chatToggle = fn;
      for (const r of roots) {
        if (r.small) r.box.setAttribute('aria-label', NAME + '，點擊開啟 AI 聊天');
      }
    },
  };
})();

/**
 * 米豆 MeDou — 全站像素小寵物
 * 單一狀態機引擎，驅動頁面上所有 [data-mipet-root] 節點。
 *
 * 畫面來自 static/img/medou/medou-sheet.png（scripts/medou/build_sprites.py 產生）：
 * 一張水平精靈圖，每格 48×48，用 background-position 切換影格，
 * 只有影格真的變了才寫 DOM。
 *
 * 公開 API（window.MiPet）：
 *   setState(s)       idle | thinking | talking | error | sleep | notify | cheer
 *                     （hover 只由滑鼠移入／鍵盤聚焦浮動小版觸發，外部傳 'hover' 會被忽略）
 *   cheer()           慶祝一下（s7），結束後回 idle
 *   pulse()           串流每收到一段 delta 呼叫一次：切到 talking 並讓嘴巴開合，
 *                     最後一次 pulse 後約 600ms 闔嘴
 *   bindOpenChat(fn, opts?)  小版改成開關聊天視窗；opts.controls 可指定面板 id
 *   setChatOpen(open) 同步小版的 aria-expanded（也會自動觀察 html.mipet-chat-open）
 */

(function() {
  if (window.MiPet) return;

  const config = {
    sleepAfterMs: 60000,   // 無互動多久後睡著
    busyTimeoutMs: 30000,  // thinking / talking 多久沒有新事件就回 idle
    errorMs: 2500,
    cheerMs: 2400,
    notifyMs: 4000,
    mouthCloseMs: 600,     // 最後一次 pulse 後多久闔嘴
    tickMs: 300,
  };

  // 精靈圖影格索引（順序見 build_sprites.py 的 FRAME_ORDER）
  const FRAME = {
    idle: 0, blink: 1, thinking: 2, talking: 3, talkingShut: 4,
    error: 5, sleep: 6, hover: 7, notify: 8, cheer: 9,
  };
  // 各狀態的代表影格（減少動態時只畫這張）
  const STATE_FRAME = {
    idle: FRAME.idle,
    thinking: FRAME.thinking,
    talking: FRAME.talking,
    error: FRAME.error,
    sleep: FRAME.sleep,
    hover: FRAME.hover,
    notify: FRAME.notify,
    cheer: FRAME.cheer,
  };
  const LABEL = {
    idle: '閒置中',
    thinking: '思考中…',
    talking: '說話中',
    error: '出錯了',
    sleep: '睡覺中',
    hover: '在這裡！',
    notify: '有新消息',
    cheer: '好耶！',
  };
  const NAME = '米豆 MeDou';

  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  let reduce = motionQuery.matches;

  let state = 'idle';
  let tick = 0;            // 進入目前狀態後經過的 tick 數
  let blinkAt = 0;          // 下一次眨眼的 tick
  let lastPulse = 0;        // 最近一次 pulse() 的時間；0 表示這輪 talking 沒有 pulse
  let hovered = false;      // 滑鼠／焦點在小版上
  let hoverBack = 'idle';   // hover 結束後回到的狀態
  let backTimer = null;     // error / cheer / notify 自動回 idle
  let busyTimer = null;     // thinking / talking 安全逾時
  let sleepTimer = null;
  let timer = null;
  let openChatHandler = null; // 有 AI 聊天時，小版點擊開關聊天視窗（取代逗逗反應）
  let controlsId = null;
  let chatOpen = false;
  const roots = [];

  // label 的單點來源：bindOpenChat 可能先於 buildRoot 執行（Alpine x-init 早於
  // DOMContentLoaded），所以 buildRoot 與 bindOpenChat 都從這裡取
  const smallLabel = () => NAME + (openChatHandler ? '，點擊開啟 AI 聊天' : '，點擊逗逗我');

  function scheduleBlink() {
    blinkAt = tick + 10 + Math.floor(Math.random() * 14); // 約 3–7 秒眨一次
  }

  function currentFrame() {
    if (reduce) return STATE_FRAME[state];
    if (state === 'idle') return tick === blinkAt ? FRAME.blink : FRAME.idle;
    if (state === 'talking') {
      if (lastPulse) {
        // 跟著串流：最近有 delta 就開合，停下來就闔嘴
        if (Date.now() - lastPulse > config.mouthCloseMs) return FRAME.talkingShut;
        return tick % 2 === 0 ? FRAME.talking : FRAME.talkingShut;
      }
      return tick % 4 < 2 ? FRAME.talking : FRAME.talkingShut;
    }
    return STATE_FRAME[state];
  }

  function render() {
    const frame = currentFrame();
    const label = LABEL[state];
    for (const r of roots) {
      if (r.frame !== frame) {
        r.frame = frame;
        r.sprite.style.setProperty('--mipet-frame', frame);
      }
      if (r.state !== state) {
        r.state = state;
        r.box.dataset.state = state;
        // aria-live：只在狀態真的改變時寫入，避免每個 tick 都朗讀
        if (r.status) r.status.textContent = label;
      }
    }
  }

  function clearTimer(id) {
    if (id) clearTimeout(id);
    return null;
  }

  function armSleep() {
    sleepTimer = clearTimer(sleepTimer);
    sleepTimer = setTimeout(() => {
      sleepTimer = null;
      if (state === 'idle' && !hovered) setState('sleep');
    }, config.sleepAfterMs);
  }

  function armBusy() {
    busyTimer = clearTimer(busyTimer);
    busyTimer = setTimeout(() => {
      busyTimer = null;
      if (state === 'thinking' || state === 'talking') setState('idle');
    }, config.busyTimeoutMs);
  }

  function setState(s) {
    if (!LABEL[s]) return;
    if (s === 'thinking' || s === 'talking') armBusy();
    if (s === state) return;
    state = s;
    tick = 0;
    scheduleBlink();
    backTimer = clearTimer(backTimer);
    if (s !== 'thinking' && s !== 'talking') busyTimer = clearTimer(busyTimer);
    if (s !== 'talking') lastPulse = 0;
    const back = { error: config.errorMs, cheer: config.cheerMs, notify: config.notifyMs }[s];
    if (back) {
      backTimer = setTimeout(() => {
        backTimer = null;
        if (state === s) setState(hovered ? 'hover' : 'idle');
      }, back);
    }
    if (s === 'idle') armSleep();
    hop(s === 'cheer');
    render();
  }

  // 小跳一下（CSS 動畫）；減少動態時不跳
  function hop(on) {
    for (const r of roots) {
      r.box.classList.remove('mipet--hop');
      if (on && !reduce) {
        void r.box.offsetWidth; // 重新觸發動畫
        r.box.classList.add('mipet--hop');
      }
    }
  }

  function cheer() {
    // 一律從 cheer 回 idle：error 也不例外，否則 backTimer 被清掉後會卡在 error
    if (state === 'cheer') state = 'idle';
    setState('cheer');
  }

  function pulse() {
    onActivity();
    if (state !== 'talking') setState('talking');
    armBusy();
    lastPulse = Date.now();
    tick -= tick % 2; // 每個 delta 都先張嘴（偶數 tick = 張嘴），下一個 tick 闔上
    render();
  }

  function pet() {
    if (state === 'error') return;
    cheer();
  }

  function onTick() {
    tick++;
    if (state === 'idle' && tick > blinkAt + 1) scheduleBlink();
    render();
  }

  function stopTick() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  function startTick() {
    if (!timer && !reduce && !document.hidden) timer = setInterval(onTick, config.tickMs);
  }

  function onActivity() {
    if (state === 'sleep') setState(hovered ? 'hover' : 'idle');
    else if (state === 'idle') armSleep();
  }
  ['pointerdown', 'keydown', 'touchstart'].forEach(ev => {
    window.addEventListener(ev, onActivity, { passive: true });
  });
  // scroll 不會冒泡，要 capture 才收得到內部容器（如聊天訊息區）的捲動
  window.addEventListener('scroll', onActivity, { passive: true, capture: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopTick();
      resetHover();
    } else {
      startTick();
      onActivity();
      render();
    }
  });

  function onMotionChange(e) {
    reduce = e.matches;
    if (reduce) {
      stopTick();
      hop(false);
    } else {
      startTick();
    }
    render();
  }
  if (motionQuery.addEventListener) motionQuery.addEventListener('change', onMotionChange);
  else if (motionQuery.addListener) motionQuery.addListener(onMotionChange);

  function hoverStart() {
    if (hovered) return;
    hovered = true;
    if (state === 'idle' || state === 'sleep') {
      hoverBack = 'idle';
      setState('hover');
    }
  }
  function hoverEnd() {
    if (!hovered) return;
    hovered = false;
    if (state === 'hover') setState(hoverBack);
  }

  // 強制離開 hover：小版被隱藏（聊天視窗開啟）、視窗失焦或分頁切走時，
  // mouseleave / blur 不一定會觸發，不重設的話 hovered 會卡住（不會睡著、
  // 狀態結束後又回到 hover，聊天 header 的大版也會顯示「點我」影格）
  function resetHover() {
    hovered = false;
    if (state === 'hover') setState(hoverBack);
  }
  window.addEventListener('blur', resetHover);

  function syncExpanded() {
    for (const r of roots) {
      if (!r.small) continue;
      if (openChatHandler) {
        r.box.setAttribute('aria-expanded', chatOpen ? 'true' : 'false');
        if (controlsId) r.box.setAttribute('aria-controls', controlsId);
      } else {
        r.box.removeAttribute('aria-expanded');
        r.box.removeAttribute('aria-controls');
      }
    }
  }

  // 聊天面板 id：明確指定優先；否則用聊天視窗裡大版米豆所在的面板（x-show 節點）
  function resolveControls() {
    if (controlsId || !openChatHandler) return;
    const large = document.querySelector('[data-mipet-root][data-mipet-size="large"]');
    const panel = large && large.closest('[x-show]');
    if (!panel) return;
    if (!panel.id) panel.id = 'mipet-chat-panel';
    controlsId = panel.id;
  }

  function buildRoot(el) {
    const large = el.getAttribute('data-mipet-size') === 'large';
    const box = document.createElement('div');
    box.className = 'mipet ' + (large ? 'mipet--large' : 'mipet--small');
    box.innerHTML =
      '<div class="mipet-col">' +
        '<div class="mipet-sprite" aria-hidden="true"></div>' +
      '</div>' +
      (large
        ? '<div class="mipet-meta"><div class="mipet-name">' + NAME + '</div>' +
          '<div class="mipet-status" role="status" aria-live="polite">' + LABEL[state] + '</div></div>'
        : '');
    if (!large) {
      box.setAttribute('role', 'button');
      box.setAttribute('tabindex', '0');
      box.setAttribute('aria-label', smallLabel());
      const activate = () => (openChatHandler ? openChatHandler() : pet());
      box.addEventListener('click', activate);
      box.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          activate();
        }
      });
      box.addEventListener('mouseenter', hoverStart);
      box.addEventListener('mouseleave', hoverEnd);
      box.addEventListener('focus', hoverStart);
      box.addEventListener('blur', hoverEnd);
    }
    el.appendChild(box);
    roots.push({
      box,
      sprite: box.querySelector('.mipet-sprite'),
      status: large ? box.querySelector('.mipet-status') : null,
      small: !large,
      frame: -1,
      // 初始狀態文字已寫在 markup 裡，不經 aria-live 朗讀；之後狀態改變才更新
      state,
    });
  }

  function init() {
    const els = document.querySelectorAll('[data-mipet-root]');
    for (const el of els) buildRoot(el);
    // 沒有 bottom nav 的頁面（未登入、建立／上傳等全螢幕表單）把浮動小版放低，
    // 預設值則保留 bottom nav 上方的安全距離（見 pixel-pet.css 的 --mipet-bottom）
    if (!document.getElementById('bottom-nav')) document.documentElement.classList.add('mipet-no-nav');
    chatOpen = document.documentElement.classList.contains('mipet-chat-open');
    resolveControls();
    syncExpanded();
    // 聊天 widget 以 html.mipet-chat-open 表示視窗開關，觀察它來同步 aria-expanded
    new MutationObserver(() => {
      const open = document.documentElement.classList.contains('mipet-chat-open');
      if (open !== chatOpen) {
        chatOpen = open;
        syncExpanded();
        resetHover();
      }
    }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    scheduleBlink();
    armSleep();
    render();
    startTick();
  }
  // DOMContentLoaded 而非直接執行：聊天視窗的大版根節點在腳本之後才解析
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.MiPet = {
    // hover 只能由小版的滑鼠／焦點事件進出；外部設定 hover 沒有回程（沒有 backTimer、
    // 不會 armSleep），所以直接忽略
    setState(s) { if (s !== 'hover') setState(s); },
    cheer() { cheer(); },
    pulse() { pulse(); },
    bindOpenChat(fn, opts) {
      openChatHandler = fn;
      if (opts && opts.controls) controlsId = opts.controls;
      resolveControls();
      for (const r of roots) {
        if (r.small) r.box.setAttribute('aria-label', smallLabel());
      }
      syncExpanded();
    },
    setChatOpen(open) {
      chatOpen = !!open;
      syncExpanded();
      resetHover();
    },
    get state() { return state; },
  };
})();

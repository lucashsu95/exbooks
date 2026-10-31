// chatWidget 行為測試 driver（由 test_chat_widget_template.py 注入渲染後的 widget script 再用 node 執行）。
const assert = require('node:assert/strict');

const store = new Map();
globalThis.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    key: (i) => [...store.keys()][i] ?? null,
    get length() { return store.size; },
};
const listeners = {};
globalThis.document = {
    cookie: 'csrftoken=abc',
    addEventListener: (type, fn) => { (listeners[type] ||= []).push(fn); },
    documentElement: { classList: { toggle() {} } },
};
globalThis.HTMLFormElement = class {};
globalThis.Element = class {};
const pet = { pulses: 0, states: [], pulse() { this.pulses++; }, setState(s) { this.states.push(s); }, cheer() {}, bindOpenChat() {} };
globalThis.window = { MiPet: pet, location: { origin: 'http://test', href: 'http://test/books/' } };

/*__WIDGET__*/

function sse(...frames) {
    return frames.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify({ type: event, ...data })}\n\n`).join('');
}

function makeWidget() {
    const w = chatWidget('7', '/accounts/logout/');
    w.$nextTick = (fn) => fn();
    w.$refs = {};
    w.init();
    return w;
}

async function send(w, text, fetchImpl) {
    globalThis.fetch = fetchImpl;
    w.userInput = text;
    await w.sendMessage();
}

const last = (w) => w.messages[w.messages.length - 1];

(async () => {
    // 舊版共用 key 在 init 時被丟棄；新 key 依使用者分開
    store.set('chat_history', JSON.stringify([{ role: 'user', content: '別人的對話' }]));
    let w = makeWidget();
    assert.equal(store.has('chat_history'), false);
    assert.equal(w.messages.length, 0);
    assert.equal(w.storageKey, 'chat_history:7');

    // 打開時本機產生問候語（不依賴任何連線）
    w.setOpen(true);
    assert.equal(w.messages.length, 1);
    assert.match(w.messages[0].content, /米豆/);

    // 1. 串流沒有 done 就結束：輸入仍要解鎖；每個 content delta pulse 一次
    pet.pulses = 0;
    await send(w, '你好', async () => new Response(sse(['status', { state: 'thinking' }], ['content', { delta: '**哈囉**' }])));
    assert.equal(w.isTyping, false);
    assert.equal(pet.pulses, 1);
    assert.equal(last(w).content, '哈囉');

    // 2. 空串流（沒有 content 也沒有 done）：解鎖並提示中斷
    await send(w, '再來', async () => new Response(''));
    assert.equal(w.isTyping, false);
    assert.match(last(w).content, /中斷/);

    // 3. 網路錯誤：解鎖並顯示中文錯誤
    await send(w, '斷線', async () => { throw new TypeError('network'); });
    assert.equal(w.isTyping, false);
    assert.match(last(w).content, /失敗/);

    // 4. 逾時（AbortError）：解鎖並提示等太久
    await send(w, '很慢', async () => { const e = new Error('aborted'); e.name = 'AbortError'; throw e; });
    assert.equal(w.isTyping, false);
    assert.match(last(w).content, /太久/);

    // 5. 429／400：顯示伺服器回的中文訊息
    await send(w, '太快', async () => new Response(JSON.stringify({ error: '訊息送得太頻繁了' }), { status: 429 }));
    assert.equal(w.isTyping, false);
    assert.equal(last(w).content, '訊息送得太頻繁了');

    // 6. consent：人類可讀描述
    await send(w, '延期', async () => new Response(sse(
        ['consent_required', { tool: 'request_renewal', args: { deal_id: 'x', days: 7 }, token: 't1', description: '申請延長借閱《小王子》7 天' }],
        ['content', { delta: '請確認' }],
        ['done', {}],
    )));
    const consent = w.messages.find((m) => m.type === 'consent');
    assert.equal(consent.content, '確認要申請延長借閱《小王子》7 天嗎？');

    // 7. consent 失敗：終止狀態（不可重試），提示重新詢問
    globalThis.fetch = async () => new Response(JSON.stringify({ error: '這個確認請求已失效。' }), { status: 404 });
    await w.sendAction(consent, 'confirm');
    assert.equal(consent.consentState, 'failed');
    assert.equal(consent.token, null);
    assert.match(last(w).content, /再問/);

    // 8. consent 成功：把 result 顯示成米豆的訊息
    consent.consentState = 'pending';
    consent.token = 't2';
    globalThis.fetch = async () => new Response(JSON.stringify({ status: 'success', result: '已提交延長 7 天的申請' }));
    await w.sendAction(consent, 'confirm');
    assert.equal(consent.consentState, 'done');
    assert.equal(last(w).role, 'assistant');
    assert.equal(last(w).content, '已提交延長 7 天的申請');

    // 9. 儲存上限：只留最後 50 則，且不存 token
    for (let i = 0; i < 80; i++) w.addMessage('user', `m${i}`);
    const saved = JSON.parse(store.get('chat_history:7'));
    assert.equal(saved.length, 50);
    assert.equal(saved[saved.length - 1].content, 'm79');
    assert.ok(saved.every((m) => !('token' in m)));

    // 10. 登出（表單送出或連結點擊）清掉所有 chat_history* key
    store.set('chat_history:8', '[]');
    store.set('other', 'keep');
    const form = Object.assign(new HTMLFormElement(), { getAttribute: () => '/accounts/logout/' });
    listeners.submit.forEach((fn) => fn({ target: form }));
    assert.equal([...store.keys()].filter((k) => k.startsWith('chat_history')).length, 0);
    assert.equal(store.get('other'), 'keep');

    store.set('chat_history:7', '[]');
    const link = Object.assign(new Element(), { closest: () => ({ getAttribute: () => 'http://test/accounts/logout/' }) });
    listeners.click.forEach((fn) => fn({ target: link }));
    assert.equal(store.has('chat_history:7'), false);

    // 其他表單不清
    store.set('chat_history:7', '[]');
    const other = Object.assign(new HTMLFormElement(), { getAttribute: () => '/books/' });
    listeners.submit.forEach((fn) => fn({ target: other }));
    assert.equal(store.has('chat_history:7'), true);

    // localStorage 不可用（隱私模式：任何存取都拋 SecurityError）：
    // init／開窗／對話／清除／登出都不得拋錯
    const realStorage = globalThis.localStorage;
    const deny = () => { const e = new Error('denied'); e.name = 'SecurityError'; throw e; };
    globalThis.localStorage = {
        getItem: deny, setItem: deny, removeItem: deny, key: deny,
        get length() { return deny(); },
    };
    w = makeWidget();
    assert.equal(w.messages.length, 0);
    w.setOpen(true);
    assert.equal(w.messages.length, 1);
    await send(w, '隱私模式', async () => new Response(sse(['content', { delta: '收到' }], ['done', {}])));
    assert.equal(w.isTyping, false);
    assert.equal(last(w).content, '收到');
    globalThis.fetch = async () => new Response('{}');
    w.clearHistory();
    assert.equal(w.messages.length, 0);
    listeners.submit.forEach((fn) => fn({ target: form }));
    globalThis.localStorage = realStorage;

    // MiPet 不存在時 pulse 呼叫是 no-op
    globalThis.window.MiPet = undefined;
    w = makeWidget();
    await send(w, '沒有寵物', async () => new Response(sse(['content', { delta: 'ok' }], ['done', {}])));
    assert.equal(w.isTyping, false);
})().catch((e) => {
    console.log(e && e.stack ? e.stack : e);
    process.exitCode = 1;
});

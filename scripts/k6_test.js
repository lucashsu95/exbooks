/**
 * Exbooks 壓力測試腳本 (k6 v1.4+)
 *
 * 使用方式：
 *   1. 先用 seed 指令產生測試資料：
 *      python manage.py seed --amount small
 *
 *   2. 啟動服務（Docker 或 dev server）：
 *      docker compose up -d
 *      # 或 python manage.py runserver
 *
 *   3. 執行測試：
 *      k6 run scripts/k6_test.js
 *
 *   可自訂目標網址：
 *      k6 run -e BASE_URL=http://staging.example.com scripts/k6_test.js
 *
 * 情境說明：
 *   - smoke:    快速驗證基本功能是否正常 (1 VU, 30s)
 *   - load:     模擬日常中等流量 (20 VU, 3m)
 *   - stress:   逐步加壓找出瓶頸點 (ramp up to 50 VU)
 *   - peak:     瞬間高負載測試 (0→40 VU in 10s)
 *
 * 執行單一情境：
 *   k6 run --scenario smoke scripts/k6_test.js
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ── 自訂 Metrics ───────────────────────────────────────────────
const failRate = new Rate("failed_requests");
const authDuration = new Trend("auth_duration");
const bookListDuration = new Trend("book_list_duration");
const healthDuration = new Trend("health_duration");

// ── 設定 ────────────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";
const DEFAULT_PASSWORD = "testpass123";

// 從 seed data 中取出測試用使用者
const TEST_USERS = Array.from({ length: 10 }, (_, i) => ({
  username: `user${i}`,
  password: DEFAULT_PASSWORD,
}));

// ── 選項 ────────────────────────────────────────────────────────
export const options = {
  // 閾值：失敗率 < 1%，健康檢查 p95 < 500ms
  thresholds: {
    failed_requests: ["rate<0.01"],
    health_duration: ["p(95)<500"],
    book_list_duration: ["p(95)<2000"],
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<3000"],
  },

  scenarios: {
    smoke: {
      executor: "constant-vus",
      vus: 1,
      duration: "30s",
      tags: { scenario: "smoke" },
    },

    load: {
      executor: "ramping-vus",
      startVUs: 5,
      stages: [
        { duration: "30s", target: 10 },
        { duration: "2m", target: 20 },
        { duration: "30s", target: 0 },
      ],
      tags: { scenario: "load" },
      startTime: "10s",
    },

    stress: {
      executor: "ramping-vus",
      startVUs: 5,
      stages: [
        { duration: "1m", target: 10 },
        { duration: "1m", target: 20 },
        { duration: "1m", target: 35 },
        { duration: "1m", target: 50 },
        { duration: "30s", target: 0 },
      ],
      tags: { scenario: "stress" },
      startTime: "5s",
    },

    peak: {
      executor: "ramping-arrival-rate",
      startRate: 5,
      timeUnit: "1s",
      preAllocatedVUs: 10,
      maxVUs: 40,
      stages: [
        { duration: "10s", target: 20 },
        { duration: "30s", target: 20 },
        { duration: "10s", target: 50 },
        { duration: "20s", target: 50 },
        { duration: "10s", target: 0 },
      ],
      tags: { scenario: "peak" },
      startTime: "5s",
    },
  },
};

// ── Helpers ─────────────────────────────────────────────────────

/** 從測試使用者池中依 VU 編號選取使用者 */
function getTestUser(vuNumber) {
  return TEST_USERS[vuNumber % TEST_USERS.length];
}

/** 登入取得 JWT token pair */
function login(username, password) {
  const url = `${BASE_URL}/api/token/`;
  const payload = JSON.stringify({ username, password });
  const params = {
    headers: { "Content-Type": "application/json" },
    tags: { name: "login" },
  };

  const res = http.post(url, payload, params);
  authDuration.add(res.timings.duration);
  failRate.add(!res.hasOwnProperty("json") || !res.json().access);

  const success = check(res, {
    "login status 200": (r) => r.status === 200,
    "login has access token": (r) => r.json("access") !== undefined,
  });

  if (!success) {
    console.warn(`Login failed for ${username}: ${res.status} ${res.body}`);
    return null;
  }

  return {
    access: res.json("access"),
    refresh: res.json("refresh"),
  };
}

/** 匿名瀏覽公共頁面 */
function browsePublicPages() {
  group("anonymous browsing", () => {
    let res = http.get(`${BASE_URL}/health/`, { tags: { name: "health" } });
    healthDuration.add(res.timings.duration);
    check(res, { "health status 200": (r) => r.status === 200 });
    failRate.add(res.status >= 400);
    sleep(1);

    res = http.get(`${BASE_URL}/`, { tags: { name: "landing" } });
    check(res, { "landing status 200": (r) => r.status === 200 });
    failRate.add(res.status >= 400);
    sleep(0.5);

    res = http.get(`${BASE_URL}/api/official/`, {
      tags: { name: "official-books" },
    });
    bookListDuration.add(res.timings.duration);
    check(res, {
      "official books status 200": (r) => r.status === 200,
      "official books has results": (r) => r.json("results") !== undefined,
    });
    failRate.add(res.status >= 400);
    sleep(0.5);

    res = http.get(`${BASE_URL}/api/shared/`, {
      tags: { name: "shared-books" },
    });
    bookListDuration.add(res.timings.duration);
    check(res, {
      "shared books status 200": (r) => r.status === 200,
      "shared books has results": (r) => r.json("results") !== undefined,
    });
    failRate.add(res.status >= 400);
    sleep(1);
  });
}

/** 已認證使用者的操作 */
function authenticatedOperations(token) {
  const authParams = {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  };
  const authGet = (url, name) =>
    http.get(url, {
      ...authParams,
      tags: { name },
    });

  group("authenticated operations", () => {
    let res = authGet(`${BASE_URL}/api/me/`, "my-profile");
    check(res, { "profile status 200": (r) => r.status === 200 });
    failRate.add(res.status >= 400);
    sleep(1);

    res = authGet(`${BASE_URL}/api/deals/`, "my-deals");
    check(res, {
      "deals status 200": (r) => r.status === 200 || r.status === 404,
    });
    failRate.add(res.status >= 500);
    sleep(1);

    res = authGet(`${BASE_URL}/api/notifications/`, "notifications");
    check(res, { "notifications status 200": (r) => r.status === 200 });
    failRate.add(res.status >= 400);
    sleep(0.5);

    res = authGet(`${BASE_URL}/api/extensions/`, "extensions");
    check(res, { "extensions status 200": (r) => r.status === 200 });
    failRate.add(res.status >= 400);
    sleep(1);
  });
}

// ── 主要流程 ────────────────────────────────────────────────────
export default function () {
  const vuId = __VU;
  const user = getTestUser(vuId);

  browsePublicPages();

  const tokens = login(user.username, user.password);
  if (tokens) {
    authenticatedOperations(tokens.access);
  } else {
    console.warn(`VU ${vuId}: skipping authenticated ops (login failed)`);
  }

  sleep(2);
}

// ── 結束回呼 ────────────────────────────────────────────────────
export function teardown(data) {
  console.log("Test finished. Check the summary above for results.");
}

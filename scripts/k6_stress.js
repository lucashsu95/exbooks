/**
 * Exbooks 壓力測試腳本 (k6 v1.4+)
 *
 * 使用前先用 seed_stress 塞資料：
 *   docker compose exec web python manage.py seed_stress --scale large
 *
 * 然後取得 JWT token 設為環境變數：
 *   export K6_JWT=$(docker compose exec web python -c "
 *     import django; django.setup()
 *     from django.contrib.auth import authenticate
 *     from rest_framework_simplejwt.tokens import AccessToken
 *     print(AccessToken.for_user(authenticate(username='user1', password='testpass123')))
 *   ")
 *
 * 執行：
 *   k6 run -e BASE_URL=http://127.0.0.1 -e JWT_TOKEN=$K6_JWT scripts/k6_stress.js
 *
 * 或跳過登入（只測匿名端點）：
 *   k6 run -e BASE_URL=http://127.0.0.1 scripts/k6_stress.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const failRate = new Rate("failed_requests");
const healthTrend = new Trend("health_ms");
const landingTrend = new Trend("landing_ms");
const booksTrend = new Trend("books_ms");
const dealsTrend = new Trend("deals_ms");
const profileTrend = new Trend("profile_ms");

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";
const JWT = __ENV.JWT_TOKEN || "";

export const options = {
  thresholds: {
    failed_requests: ["rate<0.05"],
    health_ms: ["p(95)<500"],
    landing_ms: ["p(95)<2000"],
    books_ms: ["p(95)<5000"],
    deals_ms: ["p(95)<5000"],
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<5000"],
  },

  scenarios: {
    smoke: {
      executor: "constant-vus",
      vus: 1,
      duration: "20s",
    },

    load: {
      executor: "ramping-vus",
      startVUs: 5,
      stages: [
        { duration: "20s", target: 10 },
        { duration: "1m", target: 20 },
        { duration: "20s", target: 0 },
      ],
      startTime: "5s",
    },

    stress: {
      executor: "ramping-vus",
      startVUs: 5,
      stages: [
        { duration: "30s", target: 10 },
        { duration: "30s", target: 30 },
        { duration: "30s", target: 50 },
        { duration: "30s", target: 0 },
      ],
      startTime: "5s",
    },
  },
};

/** 非認證端點 */
function testPublicEndpoints() {
  // 健康檢查 — 最輕量
  let r = http.get(`${BASE_URL}/health/`, { tags: { name: "health" } });
  healthTrend.add(r.timings.duration);
  check(r, { "health ok": (res) => res.status === 200 || res.status === 429 });
  failRate.add(r.status >= 500);
  sleep(0.3);

  // 首頁 — 有 DB 查詢（shared books）
  r = http.get(`${BASE_URL}/`, { tags: { name: "landing" } });
  landingTrend.add(r.timings.duration);
  check(r, { "landing ok": (res) => res.status === 200 });
  failRate.add(r.status >= 500);
  sleep(0.5);

  // 書目列表（大筆資料）
  r = http.get(`${BASE_URL}/books/api/official/?page=1`, {
    tags: { name: "official-books" },
  });
  booksTrend.add(r.timings.duration);
  check(r, { "official-books ok": (res) => res.status === 200 || res.status === 429 });
  failRate.add(r.status >= 500);
  sleep(0.3);

  r = http.get(`${BASE_URL}/books/api/official/?page=2`, {
    tags: { name: "official-books-p2" },
  });
  booksTrend.add(r.timings.duration);
  failRate.add(r.status >= 500);
  sleep(0.3);

  // 共享書籍列表
  r = http.get(`${BASE_URL}/books/api/shared/?page=1`, {
    tags: { name: "shared-books" },
  });
  booksTrend.add(r.timings.duration);
  check(r, { "shared-books ok": (res) => res.status === 200 || res.status === 429 });
  failRate.add(r.status >= 500);
  sleep(0.5);
}

/** 認證端點 */
function testAuthEndpoints(token) {
  const params = {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  };

  // 個人資料
  let r = http.get(`${BASE_URL}/accounts/api/me/`, {
    ...params,
    tags: { name: "profile" },
  });
  profileTrend.add(r.timings.duration);
  check(r, { "profile ok": (res) => res.status === 200 || res.status === 429 });
  failRate.add(r.status >= 500);
  sleep(0.5);

  // 我的交易
  r = http.get(`${BASE_URL}/deals/api/deals/`, {
    ...params,
    tags: { name: "deals" },
  });
  dealsTrend.add(r.timings.duration);
  check(r, { "deals ok": (res) => res.status === 200 || res.status === 404 });
  failRate.add(r.status >= 500);
  sleep(0.3);

  // 通知
  r = http.get(`${BASE_URL}/deals/api/notifications/`, {
    ...params,
    tags: { name: "notifications" },
  });
  dealsTrend.add(r.timings.duration);
  check(r, { "notifications ok": (res) => res.status === 200 || res.status === 429 });
  failRate.add(r.status >= 500);
  sleep(0.3);
}

export default function () {
  testPublicEndpoints();

  if (JWT) {
    testAuthEndpoints(JWT);
  }

  sleep(1);
}

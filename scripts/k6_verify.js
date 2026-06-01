/**
 * Exbooks 壓力測試驗證腳本 — 乾淨版，無 throttle 干擾
 *
 * 使用方式：
 *   export K6_JWT=$(docker compose exec -T web python -c "
 *     import django; django.setup()
 *     from django.contrib.auth import authenticate
 *     from rest_framework_simplejwt.tokens import AccessToken
 *     print(AccessToken.for_user(authenticate(username='user1', password='testpass123')))
 *   ")
 *   k6 run -e BASE_URL=http://127.0.0.1 -e JWT_TOKEN=$K6_JWT scripts/k6_verify.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";
const JWT = __ENV.JWT_TOKEN || "";

// 每個端點獨立的計量
const endpointTrends = {};
const endpointCounters = {};
const endpoints = [
  "health", "landing",
  "official_books_p1", "official_books_p2", "shared_books",
  "profile", "deals", "notifications",
];
endpoints.forEach((name) => {
  endpointTrends[name] = new Trend(`${name}_ms`);
  endpointCounters[name] = { total: new Counter(`${name}_total`), fail: new Counter(`${name}_fail`) };
});

const failRate = new Rate("failed_requests");

export const options = {
  thresholds: {
    failed_requests: ["rate<0.01"],
    http_req_duration: ["p(95)<3000"],
    http_req_failed: ["rate<0.01"],
  },
  scenarios: {
    verified: {
      executor: "constant-vus",
      vus: 10,
      duration: "30s",
    },
  },
};

function callEndpoint(name, url, params = {}, expectedStatuses = [200]) {
  const res = http.get(url, params);
  endpointTrends[name].add(res.timings.duration);
  endpointCounters[name].total.add(1);
  if (!expectedStatuses.includes(res.status)) {
    endpointCounters[name].fail.add(1);
    failRate.add(1);
  }
  check(res, {
    [`${name} success`]: (r) => expectedStatuses.includes(r.status),
  });
  return res;
}

export default function () {
  // 匿名端點
  callEndpoint("health", `${BASE_URL}/health/`);
  sleep(0.3);

  callEndpoint("landing", `${BASE_URL}/`);
  sleep(0.5);

  callEndpoint("official_books_p1", `${BASE_URL}/books/api/official/?page=1`);
  sleep(0.3);

  callEndpoint("official_books_p2", `${BASE_URL}/books/api/official/?page=2`);
  sleep(0.3);

  callEndpoint("shared_books", `${BASE_URL}/books/api/shared/`);
  sleep(0.5);

  // 認證端點
  if (JWT) {
    const authParams = {
      headers: { Authorization: `Bearer ${JWT}`, "Content-Type": "application/json" },
    };
    callEndpoint("profile", `${BASE_URL}/accounts/api/me/`, authParams);
    sleep(0.5);

    callEndpoint("deals", `${BASE_URL}/deals/api/deals/`, authParams, [200, 404]);
    sleep(0.3);

    callEndpoint("notifications", `${BASE_URL}/deals/api/notifications/`, authParams);
    sleep(0.5);
  }

  sleep(1);
}

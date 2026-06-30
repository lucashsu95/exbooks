#!/usr/bin/env python
"""
視覺化真實 E2E 測試產出的三層日誌，生成 evidence_dashboard.png

用法：
    python scripts/render_evidence.py --evidence-dir <pytest 生成的 evidence 目錄>
    python scripts/render_evidence.py --evidence-dir /tmp/pytest-of-user/evidence0
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# HTML 模板：儀表板頁面
# ──────────────────────────────────────────────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exbooks Observability Evidence Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Noto Sans TC', sans-serif; }
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        .log-entry { transition: all 0.2s ease; }
        .log-entry:hover { background-color: #fef3c7; }
        .trace-highlight { background-color: #dbeafe !important; }
        .anomaly-row { background-color: #fee2e2 !important; }
        .anomaly-row:hover { background-color: #fecaca !important; }
        .tier-system { border-left: 4px solid #3b82f6; }
        .tier-audit { border-left: 4px solid #8b5cf6; }
        .tier-business { border-left: 4px solid #10b981; }
        .tier-alerts { border-left: 4px solid #ef4444; }
        .json-key { color: #9333ea; }
        .json-string { color: #059669; }
        .json-number { color: #dc2626; }
        .json-bool { color: #ea580c; }
        .json-null { color: #6b7280; font-style: italic; }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Header -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                </svg>
                Exbooks 可觀測性驗證儀表板
            </h1>
            <p class="text-gray-600 mt-2">真實 E2E 測試產出的三層日誌關聯證明</p>
        </header>

        <!-- Trace ID Summary -->
        <section id="trace-summary" class="mb-8">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    追蹤鏈路摘要
                </h2>
                <div id="trace-info" class="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-sm">
                    <!-- 由 JS 填入 -->
                </div>
            </div>
        </section>

        <!-- Tier Statistics -->
        <section id="tier-stats" class="mb-8">
            <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                </svg>
                三層日誌統計
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4" id="tier-cards">
                <!-- 由 JS 填入 -->
            </div>
        </section>

        <!-- Log Viewer -->
        <section id="log-viewer">
            <div class="flex flex-col md:flex-row gap-4 mb-4">
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">過濾 Trace ID</label>
                    <select id="trace-filter" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm">
                        <option value="">全部</option>
                    </select>
                </div>
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">日誌層級</label>
                    <select id="tier-filter" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                        <option value="">全部</option>
                        <option value="system">System (技術除錯)</option>
                        <option value="audit">Audit (合規稽核)</option>
                        <option value="business">Business (業務分析)</option>
                        <option value="alerts">Alerts (異常告警)</option>
                    </select>
                </div>
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">搜尋關鍵字</label>
                    <input type="text" id="search-input" placeholder="事件類型、用戶 ID、錯誤訊息..." class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                </div>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-sm font-mono">
                        <thead class="bg-gray-50 border-b border-gray-200 sticky top-0">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">時間</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">層級</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">等級</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">訊息 / 事件</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-48">Trace ID</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-64">詳細內容 (JSON)</th>
                            </tr>
                        </thead>
                        <tbody id="log-table-body" class="divide-y divide-gray-100">
                            <!-- 由 JS 填入 -->
                        </tbody>
                    </table>
                </div>
                <div id="empty-state" class="hidden p-12 text-center text-gray-500">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <p class="mt-2">無符合條件的日誌記錄</p>
                </div>
            </div>
        </section>

        <!-- Legend -->
        <section class="mt-8">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">圖例說明</h3>
                <div class="flex flex-wrap gap-6 text-sm">
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded border-l-4 border-blue-500 bg-blue-50"></div>
                        <span>System：技術除錯日誌（請求路徑、DB 查詢、錯誤堆疊）</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded border-l-4 border-purple-500 bg-purple-50"></div>
                        <span>Audit：合規稽核（權限變更、資產轉移、敏感操作）</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded border-l-4 border-green-500 bg-green-50"></div>
                        <span>Business：業務事件（deal.created、trust_score.changed 等）</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded border-l-4 border-red-500 bg-red-50"></div>
                        <span class="text-red-700 font-medium">Alerts：異常檢測告警（紅底高亮）</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded bg-yellow-100 border border-yellow-300"></div>
                        <span>Trace 高亮：同一 trace_id 的關聯日誌（藍底）</span>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <script>
        // ──────────────────────────────────────────────────────────────────────
        // 資料載入（由 Python 注入）
        // ──────────────────────────────────────────────────────────────────────
        const RAW_LOGS = {{RAW_LOGS_JSON}};
        const TRACE_ID = "{{TRACE_ID}}";
        const TIER_STATS = {{TIER_STATS_JSON}};

        // ──────────────────────────────────────────────────────────────────────
        // 工具函數
        // ──────────────────────────────────────────────────────────────────────

        function formatJson(obj) {
            if (obj === null || obj === undefined) return '<span class="json-null">null</span>';
            if (typeof obj === 'string') return '<span class="json-string">"' + escapeHtml(obj) + '"</span>';
            if (typeof obj === 'number') return '<span class="json-number">' + obj + '</span>';
            if (typeof obj === 'boolean') return '<span class="json-bool">' + obj + '</span>';
            if (Array.isArray(obj)) return '[' + obj.map(formatJson).join(', ') + ']';
            const entries = Object.entries(obj);
            if (entries.length === 0) return '{}';
            return '{<br>' + entries.map(([k, v]) =>
                '&nbsp;&nbsp;<span class="json-key">"' + escapeHtml(k) + '"</span>: ' + formatJson(v)
            ).join(',<br>') + '<br>}';
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function formatTimestamp(ts) {
            // ISO 字串轉本地顯示
            const d = new Date(ts);
            return d.toLocaleString('zh-TW', { hour12: false });
        }

        function getTierClass(tier) {
            return {
                'system': 'tier-system',
                'audit': 'tier-audit',
                'business': 'tier-business',
                'alerts': 'tier-alerts'
            }[tier] || '';
        }

        function getTierLabel(tier) {
            return {
                'system': 'System',
                'audit': 'Audit',
                'business': 'Business',
                'alerts': 'Alerts'
            }[tier] || tier;
        }

        function getTierBadgeClass(tier) {
            return {
                'system': 'bg-blue-100 text-blue-800',
                'audit': 'bg-purple-100 text-purple-800',
                'business': 'bg-green-100 text-green-800',
                'alerts': 'bg-red-100 text-red-800'
            }[tier] || 'bg-gray-100 text-gray-800';
        }

        // ──────────────────────────────────────────────────────────────────────
        // 渲染
        // ──────────────────────────────────────────────────────────────────────

        function renderTraceInfo() {
            const container = document.getElementById('trace-info');
            container.innerHTML = `
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div class="text-xs text-blue-700 font-medium">主要 Trace ID</div>
                    <div class="font-mono text-sm text-blue-900 break-all">${escapeHtml(TRACE_ID)}</div>
                </div>
                <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div class="text-xs text-green-700 font-medium">總日誌筆數</div>
                    <div class="font-mono text-2xl text-green-900">${RAW_LOGS.length}</div>
                </div>
                <div class="bg-purple-50 border border-purple-200 rounded-lg p-4">
                    <div class="text-xs text-purple-700 font-medium">涵蓋層級</div>
                    <div class="font-mono text-sm text-purple-900">${Object.keys(TIER_STATS).join(' / ')}</div>
                </div>
            `;
        }

        function renderTierStats() {
            const container = document.getElementById('tier-cards');
            const tierColors = {
                'system': { bg: 'bg-blue-50', border: 'border-blue-200', icon: 'bg-blue-100', iconColor: 'text-blue-600', label: 'System', desc: '技術除錯' },
                'audit': { bg: 'bg-purple-50', border: 'border-purple-200', icon: 'bg-purple-100', iconColor: 'text-purple-600', label: 'Audit', desc: '合規稽核' },
                'business': { bg: 'bg-green-50', border: 'border-green-200', icon: 'bg-green-100', iconColor: 'text-green-600', label: 'Business', desc: '業務分析' },
                'alerts': { bg: 'bg-red-50', border: 'border-red-200', icon: 'bg-red-100', iconColor: 'text-red-600', label: 'Alerts', desc: '異常告警' }
            };
            container.innerHTML = Object.entries(TIER_STATS).map(([tier, count]) => {
                const c = tierColors[tier] || { bg: 'bg-gray-50', border: 'border-gray-200', icon: 'bg-gray-100', iconColor: 'text-gray-600', label: tier, desc: '' };
                return `
                    <div class="${c.bg} ${c.border} rounded-xl p-5 border">
                        <div class="flex items-center gap-3 mb-2">
                            <div class="${c.icon} ${c.iconColor} p-2 rounded-lg">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                </svg>
                            </div>
                            <div>
                                <div class="font-semibold text-gray-900">${c.label}</div>
                                <div class="text-xs text-gray-500">${c.desc}</div>
                            </div>
                        </div>
                        <div class="font-mono text-3xl font-bold text-gray-900">${count}</div>
                    </div>
                `;
            }).join('');
        }

        function populateTraceFilter() {
            const select = document.getElementById('trace-filter');
            const traceIds = [...new Set(RAW_LOGS.map(l => l.trace_id).filter(Boolean))].sort();
            traceIds.forEach(tid => {
                const opt = document.createElement('option');
                opt.value = tid;
                opt.textContent = tid;
                if (tid === TRACE_ID) opt.selected = true;
                select.appendChild(opt);
            });
        }

        function renderLogTable() {
            const tbody = document.getElementById('log-table-body');
            const traceFilter = document.getElementById('trace-filter').value;
            const tierFilter = document.getElementById('tier-filter').value;
            const searchTerm = document.getElementById('search-input').value.toLowerCase();

            const filtered = RAW_LOGS.filter(entry => {
                if (traceFilter && entry.trace_id !== traceFilter) return false;
                if (tierFilter && entry.logger !== tierFilter) return false;
                if (searchTerm) {
                    const haystack = JSON.stringify(entry).toLowerCase();
                    if (!haystack.includes(searchTerm)) return false;
                }
                return true;
            });

            if (filtered.length === 0) {
                tbody.innerHTML = '';
                document.getElementById('empty-state').classList.remove('hidden');
                return;
            }
            document.getElementById('empty-state').classList.add('hidden');

            tbody.innerHTML = filtered.map(entry => {
                const isTargetTrace = entry.trace_id === TRACE_ID;
                const isAnomaly = entry.logger === 'alerts' || entry.extra?.anomaly_type;
                const rowClass = [
                    'log-entry',
                    getTierClass(entry.logger),
                    isTargetTrace ? 'trace-highlight' : '',
                    isAnomaly ? 'anomaly-row' : ''
                ].filter(Boolean).join(' ');

                const eventType = entry.extra?.event_type || '';
                const message = entry.message || eventType || '—';

                return `
                    <tr class="${rowClass}" data-trace="${escapeHtml(entry.trace_id)}">
                        <td class="px-4 py-2 text-gray-600 whitespace-nowrap">${formatTimestamp(entry.timestamp)}</td>
                        <td class="px-4 py-2">
                            <span class="px-2 py-0.5 rounded text-xs font-medium ${getTierBadgeClass(entry.logger)}">${getTierLabel(entry.logger)}</span>
                        </td>
                        <td class="px-4 py-2 text-gray-600">${entry.level}</td>
                        <td class="px-4 py-2 text-gray-900 font-medium">${escapeHtml(message)}</td>
                        <td class="px-4 py-2 font-mono text-xs text-blue-700 break-all">${escapeHtml(entry.trace_id || '—')}</td>
                        <td class="px-4 py-2 max-w-xs">${formatJson(entry.extra || {})}</td>
                    </tr>
                `;
            }).join('');
        }

        // ──────────────────────────────────────────────────────────────────────
        // 初始化
        // ──────────────────────────────────────────────────────────────────────

        document.addEventListener('DOMContentLoaded', () => {
            renderTraceInfo();
            renderTierStats();
            populateTraceFilter();
            renderLogTable();

            // 事件監聽
            document.getElementById('trace-filter').addEventListener('change', renderLogTable);
            document.getElementById('tier-filter').addEventListener('change', renderLogTable);
            document.getElementById('search-input').addEventListener('input', renderLogTable);
        });
    </script>
</body>
</html>
"""

# ──────────────────────────────────────────────────────────────────────────────
# 核心邏輯
# ──────────────────────────────────────────────────────────────────────────────

def load_jsonl(filepath: Path) -> list[dict[str, Any]]:
    """讀取 JSONL 檔案"""
    entries = []
    if not filepath.exists():
        return entries
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def collect_logs(evidence_dir: Path) -> tuple[list[dict], dict[str, int], str]:
    """
    讀取四份日誌，合併並按時間排序。
    回傳：(所有日誌列表, 各層統計, 主要 trace_id)
    """
    tier_files = {
        "system": evidence_dir / "evidence_system.jsonl",
        "audit": evidence_dir / "evidence_audit.jsonl",
        "business": evidence_dir / "evidence_business.jsonl",
        "alerts": evidence_dir / "evidence_alerts.jsonl",
    }

    all_logs = []
    tier_stats = {}

    for tier, path in tier_files.items():
        logs = load_jsonl(path)
        tier_stats[tier] = len(logs)
        for entry in logs:
            entry["_tier"] = tier
            # 統一 logger 名稱
            entry["logger"] = tier
        all_logs.extend(logs)

    # 按時間排序
    all_logs.sort(key=lambda x: x.get("timestamp", ""))

    # 找出最常出現的 trace_id（即主要測試流程的 trace_id）
    trace_counts: dict[str, int] = {}
    for entry in all_logs:
        tid = entry.get("trace_id")
        if tid:
            trace_counts[tid] = trace_counts.get(tid, 0) + 1

    primary_trace_id = max(trace_counts, key=trace_counts.get) if trace_counts else ""

    return all_logs, tier_stats, primary_trace_id


def generate_dashboard(evidence_dir: Path, output_path: Path) -> None:
    """生成儀表板 HTML 並用 Playwright 截圖"""
    all_logs, tier_stats, primary_trace_id = collect_logs(evidence_dir)

    # 準備模板資料
    logs_json = json.dumps(all_logs, ensure_ascii=False)
    tier_stats_json = json.dumps(tier_stats, ensure_ascii=False)

    html = DASHBOARD_HTML.replace("{{RAW_LOGS_JSON}}", logs_json) \
                         .replace("{{TIER_STATS_JSON}}", tier_stats_json) \
                         .replace("{{TRACE_ID}}", primary_trace_id)

    # 寫入暫存 HTML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        html_path = Path(f.name)

    try:
        # 用 Playwright 截圖
        import asyncio
        from playwright.async_api import async_playwright

        async def screenshot():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1440, "height": 1200},
                    device_scale_factor=1.5,  # 高解析度
                )
                page = await context.new_page()
                await page.goto(f"file://{html_path.absolute()}")
                # 等待 JS 渲染完成
                await page.wait_for_selector("#log-table-body")
                await page.wait_for_timeout(500)
                # 截全頁
                await page.screenshot(path=str(output_path), full_page=True)
                await browser.close()
                print(f"✅ Dashboard screenshot saved: {output_path}")

        asyncio.run(screenshot())
    finally:
        html_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="生成 Exbooks 可觀測性證據儀表板截圖")
    parser.add_argument("--evidence-dir", required=True, type=Path, help="pytest 產生的 evidence 目錄")
    parser.add_argument("--output", default="evidence_dashboard.png", type=Path, help="輸出圖片路徑")
    args = parser.parse_args()

    evidence_dir = args.evidence_dir
    output_path = args.output

    if not evidence_dir.exists():
        print(f"❌ Evidence directory not found: {evidence_dir}", file=sys.stderr)
        sys.exit(1)

    # 檢查必要檔案
    required = ["evidence_system.jsonl", "evidence_business.jsonl", "evidence_audit.jsonl"]
    for f in required:
        if not (evidence_dir / f).exists():
            print(f"❌ Missing required log file: {f}", file=sys.stderr)
            sys.exit(1)

    print(f"📊 Reading logs from: {evidence_dir}")
    print(f"📸 Generating dashboard: {output_path}")

    generate_dashboard(evidence_dir, output_path)
    print("✅ Done!")


if __name__ == "__main__":
    main()
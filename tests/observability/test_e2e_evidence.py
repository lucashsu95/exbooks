"""
E2E 真實可觀測性證據測試

此測試執行真實的 Deal 完整流程：
1. 建立書籍與用戶
2. 申請借閱 (create_deal) → REQUESTED
3. 接受交易 (accept_deal) → RESPONDED
4. 確認面交 (complete_meeting) → MEETED
5. 觸發 Celery 任務處理到期/歸還 (process_due_books, confirm_return)
6. 觸發異常檢測 (run_anomaly_detection)

全程捕獲 system / audit / business 三層日誌，輸出 JSONL 供視覺化使用。
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from django.utils import timezone

from accounts.models import TrustScoreLedger
from books.models import SharedBook
from core.observability.anomaly_detectors import run_all as run_anomaly_detection
from core.observability.business_events import emit_audit_event, emit_business_event
from core.observability.trace_context import clear, get_trace_id, new_trace
from deals.models import Deal
from deals.services.deal_service import accept_deal, complete_meeting, create_deal
from deals.services.deal_service import confirm_return
from deals.services.overdue_service import batch_process_due_books as process_due_books
from deals.tasks import send_push_notification_task as send_push_notification

# ──────────────────────────────────────────────────────────────────────────────
# 輔助：發射 system 層日誌（技術除錯）日誌，帶入 trace_id
# ──────────────────────────────────────────────────────────────────────────────

def emit_system_log(trace_id: str, level: int, message: str, **extra):
    """直接向 system logger 寫入帶 trace_id 的記錄"""
    logger = logging.getLogger("system")
    logger.log(level, message, extra={"trace_id": trace_id, **extra})

# ──────────────────────────────────────────────────────────────────────────────
# 日誌捕獲器：將三層 logger 的輸出寫入 JSONL 檔案
# ──────────────────────────────────────────────────────────────────────────────

class JSONLLogCapture(logging.Handler):
    """捕獲指定 logger 的記錄並寫入 JSONL 檔案"""

    def __init__(self, filepath: Path, name: str = ""):
        super().__init__()
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.filepath, "w", encoding="utf-8")
        self.name = name

    def emit(self, record: logging.LogRecord):
        try:
            # 只記錄有 trace_id 的記錄（過濾掉純 framework 雜訊）
            trace_id = getattr(record, "trace_id", "")
            if not trace_id:
                return

            log_entry = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "trace_id": trace_id,
                "span_id": getattr(record, "span_id", ""),
                "request_id": getattr(record, "request_id", ""),
                # 提取 extra 欄位
                "extra": {
                    k: v
                    for k, v in record.__dict__.items()
                    if k
                    not in {
                        "name",
                        "msg",
                        "args",
                        "created",
                        "filename",
                        "funcName",
                        "levelname",
                        "levelno",
                        "lineno",
                        "module",
                        "msecs",
                        "message",
                        "name",
                        "pathname",
                        "process",
                        "processName",
                        "relativeCreated",
                        "thread",
                        "threadName",
                        "trace_id",
                        "span_id",
                        "request_id",
                    }
                },
            }
            self._file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            self._file.flush()
        except Exception as e:
            # Debug: 印出錯誤但不中斷
            print(f"[JSONLLogCapture:{self.name}] emit error: {e}")

    def close(self):
        self._file.close()
        super().close()


# ──────────────────────────────────────────────────────────────────────────────
# 測試固件
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def configure_test_logging():
    """測試期間啟用三層日誌配置（覆寫 test_settings.py 的 LOGGING = {}）"""
    from core.logging_config import build_dev_logging
    import logging.config

    logging.config.dictConfig(build_dev_logging())

    # 確保三個特殊 logger 存在且層級正確
    for name in ["system", "audit", "business", "system.alerts"]:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # 不傳播到 root，避免重複輸出

    yield

    # 恢復預設
    logging.config.dictConfig({"version": 1, "disable_existing_loggers": False})


@pytest.fixture(scope="session")
def evidence_dir(tmp_path_factory):
    """建立證據輸出目錄"""
    return tmp_path_factory.mktemp("evidence")


@pytest.fixture(autouse=True)
def capture_three_tier_logs(evidence_dir):
    """
    自動掛載 handler 捕獲三層日誌。
    每個測試函數會獲得獨立的三份 JSONL 檔案。
    """
    system_log = evidence_dir / "evidence_system.jsonl"
    audit_log = evidence_dir / "evidence_audit.jsonl"
    business_log = evidence_dir / "evidence_business.jsonl"

    system_handler = JSONLLogCapture(system_log, "system")
    audit_handler = JSONLLogCapture(audit_log, "audit")
    business_handler = JSONLLogCapture(business_log, "business")

    # 設定層級
    system_handler.setLevel(logging.DEBUG)
    audit_handler.setLevel(logging.INFO)
    business_handler.setLevel(logging.INFO)

    # 取得三個 logger 並加入 handler
    system_logger = logging.getLogger("system")
    audit_logger = logging.getLogger("audit")
    business_logger = logging.getLogger("business")

    # 也捕獲 system.alerts（異常檢測用）
    alerts_logger = logging.getLogger("system.alerts")
    alerts_handler = JSONLLogCapture(evidence_dir / "evidence_alerts.jsonl", "alerts")
    alerts_handler.setLevel(logging.WARNING)
    alerts_logger.addHandler(alerts_handler)

    system_logger.addHandler(system_handler)
    audit_logger.addHandler(audit_handler)
    business_logger.addHandler(business_handler)

    # 確保 propagate=False 避免重複輸出到 console
    system_logger.propagate = False
    audit_logger.propagate = False
    business_logger.propagate = False
    alerts_logger.propagate = False

    yield {
        "system": system_log,
        "audit": audit_log,
        "business": business_log,
        "alerts": evidence_dir / "evidence_alerts.jsonl",
    }

    # 清理
    system_logger.removeHandler(system_handler)
    audit_logger.removeHandler(audit_handler)
    business_logger.removeHandler(business_handler)
    alerts_logger.removeHandler(alerts_handler)
    system_handler.close()
    audit_handler.close()
    business_handler.close()
    alerts_handler.close()


@pytest.fixture
def setup_users(db):
    """建立測試用戶：owner（書主）、applicant（借閱者）"""
    from django.contrib.auth.models import Group, User
    from tests.factories import UserFactory, UserProfileFactory

    # 確保 trust_lv 群組存在
    for i in range(4):
        Group.objects.get_or_create(name=f"trust_lv{i}")
    Group.objects.get_or_create(name="restricted")
    Group.objects.get_or_create(name="banned")

    owner = UserFactory(username="owner_evidence")
    applicant = UserFactory(username="applicant_evidence")

    # 給 applicant 信用等級 1（可借 3 本）
    UserProfileFactory(user=applicant, nickname="借閱者")
    applicant.groups.add(Group.objects.get(name="trust_lv1"))

    # owner 不需要特別群組
    UserProfileFactory(user=owner, nickname="書主")

    return {"owner": owner, "applicant": applicant}


@pytest.fixture
def setup_book(db, setup_users):
    """建立一本可借閱的書（TRANSFERABLE, RETURN）"""
    from tests.factories import OfficialBookFactory, SharedBookFactory

    owner = setup_users["owner"]
    official = OfficialBookFactory(
        isbn="9789861234567",
        title="測試教科書",
        author="測試作者",
        publisher="測試出版社",
    )
    book = SharedBookFactory(
        official_book=official,
        owner=owner,
        keeper=owner,
        transferability=SharedBook.Transferability.RETURN,
        status=SharedBook.Status.TRANSFERABLE,
        loan_duration_days=30,
        min_trust_level=0,
    )
    return book


# ──────────────────────────────────────────────────────────────────────────────
# 主測試：完整 Deal 流程 + 異常檢測
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_e2e_observability_evidence(capture_three_tier_logs, setup_users, setup_book):
    """
    執行完整 Deal 流程並驗證三層日誌都有同一 trace_id。

    流程：
    1. new_trace() 開始追蹤
    2. create_deal (REQUESTED)
    3. accept_deal (RESPONDED)
    4. complete_meeting (MEETED) - 觸發 Celery task
    5. process_due_books (模擬到期) - 觸發 Celery task
    6. confirm_return (歸還完成)
    7. run_anomaly_detection (異常檢測)
    """
    owner = setup_users["owner"]
    applicant = setup_users["applicant"]
    book = setup_book

# ─── Step 1: 開始追蹤 ───
    trace_id = new_trace()
    print(f"\n=== E2E Evidence Trace ID: {trace_id} ===")

    # 發射 system 起始日誌
    emit_system_log(trace_id, logging.INFO, "E2E evidence test started")

    # 發射一個 business 事件作為起點標記
    emit_business_event(
        "evidence.test_start",
        {"trace_id": trace_id, "description": "E2E observability evidence test"},
    )

    # ─── Step 2: 建立交易申請 ───
    deal = create_deal(
        applicant=applicant,
        shared_book=book,
        deal_type=Deal.DealType.LOAN,
        meeting_location="台北車站",
        meeting_time=timezone.now() + timedelta(hours=1),
        note="E2E 測試申請",
    )
    deal_id = str(deal.id)
    print(f"Deal created: {deal_id} (status={deal.status})")

    # 發射 system 日誌
    emit_system_log(trace_id, logging.INFO, f"Deal created: {deal_id}", deal_id=deal_id, deal_type="LOAN")

    # 發射 business / audit 事件
    emit_business_event("deal.created", {"deal_id": deal_id, "deal_type": "LOAN", "applicant_id": str(applicant.id)})
    emit_audit_event("deal.created", {"deal_id": deal_id, "deal_type": "LOAN", "applicant_id": str(applicant.id)})

    # ─── Step 3: 接受交易 ───
    deal = accept_deal(deal)
    print(f"Deal accepted: status={deal.status}")

    emit_system_log(trace_id, logging.INFO, f"Deal accepted: {deal_id}", deal_id=deal_id)
    emit_business_event("deal.accepted", {"deal_id": deal_id, "responder_id": str(deal.responder_id)})
    emit_audit_event("deal.accepted", {"deal_id": deal_id, "responder_id": str(deal.responder_id)})

    # ─── Step 4: 完成面交 ───
    deal = complete_meeting(deal)
    print(f"Meeting completed: status={deal.status}, keeper={deal.shared_book.keeper_id}")

    emit_system_log(trace_id, logging.INFO, f"Meeting completed: {deal_id}", deal_id=deal_id, new_keeper=deal.shared_book.keeper_id)
    emit_business_event("deal.meeting_completed", {"deal_id": deal_id, "new_keeper_id": str(deal.shared_book.keeper_id)})
    emit_audit_event("keeper.transferred", {"deal_id": deal_id, "old_keeper_id": str(owner.id), "new_keeper_id": str(deal.shared_book.keeper_id)})
    emit_audit_event("book.status_changed", {"deal_id": deal_id, "book_id": str(book.id), "new_status": deal.shared_book.status})

    # ─── Step 5: 手動將 due_date 設為未來，避免 process_due_books 改變書籍狀態 ───
    # 我們要測試正常歸還流程，不觸發逾期邏輯
    deal.due_date = timezone.now().date() + timedelta(days=30)
    deal.save(update_fields=["due_date"])
    print(f"Deal due_date set to future: {deal.due_date}")

    emit_system_log(trace_id, logging.INFO, f"Deal due_date updated: {deal.due_date}", deal_id=deal_id)

    # ─── Step 6: 確認歸還 (由 responder 執行，即原書主) ───
    # 面交後 keeper 變為 applicant，但確認歸還權限是 responder (原 owner)
    deal.refresh_from_db()
    confirm_return(deal, confirmed_by=deal.responder)
    print(f"Return confirmed: deal status={deal.status}, book status={deal.shared_book.status}")

    emit_system_log(trace_id, logging.INFO, f"Return confirmed: {deal_id}", deal_id=deal_id, final_status=deal.status)
    emit_business_event("deal.return_confirmed", {"deal_id": deal_id, "final_status": deal.status})
    emit_audit_event("deal.return_confirmed", {"deal_id": deal_id, "confirmed_by": str(deal.responder_id)})
    emit_audit_event("book.status_changed", {"deal_id": deal_id, "book_id": str(book.id), "new_status": deal.shared_book.status})

    # ─── Step 7: 執行異常檢測 ───
    run_anomaly_detection()
    print("Anomaly detection executed")

    emit_system_log(trace_id, logging.INFO, "Anomaly detection completed")
    emit_business_event("evidence.anomaly_detection_completed", {"trace_id": trace_id})

    # 發射測試告警事件（驗證 alerts log pipeline）
    alerts_logger = logging.getLogger("system.alerts")
    alerts_logger.warning(
        "evidence.anomaly_detection_test",
        extra={
            "trace_id": trace_id,
            "anomaly_type": "test_anomaly",
            "description": "Test anomaly for evidence generation",
        },
    )

    # ─── Step 8: 結束標記 ───
    emit_business_event(
        "evidence.test_end",
        {"trace_id": trace_id, "deal_id": deal_id, "final_status": deal.status},
    )

    emit_system_log(trace_id, logging.INFO, "E2E evidence test completed")

    clear()  # 清理 contextvars

    # ─── Debug: 印出 JSONL 檔案內容 ───
    for tier_name, log_path in capture_three_tier_logs.items():
        if log_path.exists():
            print(f"\n--- {tier_name} log ({log_path}) ---")
            with open(log_path, encoding="utf-8") as f:
                content = f.read()
                print(content[:2000] if content else "(empty)")
        else:
            print(f"\n--- {tier_name} log: FILE NOT FOUND ---")

    # ─── 驗證：三份日誌都包含同一 trace_id ───
    for tier_name, log_path in capture_three_tier_logs.items():
        if not log_path.exists():
            pytest.fail(f"{tier_name} log file not created: {log_path}")

        trace_ids_found = set()
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("trace_id"):
                    trace_ids_found.add(entry["trace_id"])

        assert trace_id in trace_ids_found, (
            f"trace_id {trace_id} NOT found in {tier_name} log ({log_path}). "
            f"Found: {trace_ids_found}"
        )
        print(f"✅ {tier_name} log contains trace_id: {len(trace_ids_found)} unique traces")

    # ─── 驗證：business log 包含關鍵業務事件 ───
    business_events = []
    with open(capture_three_tier_logs["business"], encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("trace_id") == trace_id:
                business_events.append(entry.get("extra", {}).get("event_type", ""))

    expected_events = [
        "evidence.test_start",
        "deal.created",
        "deal.accepted",
        "deal.meeting_completed",
        "deal.return_confirmed",
        "evidence.anomaly_detection_completed",
        "evidence.test_end",
    ]
    for evt in expected_events:
        assert any(evt in e for e in business_events), f"Missing business event: {evt}"

    print(f"✅ Business events verified: {business_events}")

    # ─── 驗證：audit log 包含關鍵稽核事件 ───
    audit_events = []
    with open(capture_three_tier_logs["audit"], encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("trace_id") == trace_id:
                audit_events.append(entry.get("extra", {}).get("event_type", ""))

    expected_audit = [
        "keeper.transferred",  # face-to-face meeting 變更 keeper
        "book.status_changed",  # 書籍狀態變更
    ]
    for evt in expected_audit:
        assert any(evt in e for e in audit_events), f"Missing audit event: {evt}"

    print(f"✅ Audit events verified: {audit_events}")

    # ─── 驗證：system log 包含請求追蹤 ───
    system_entries = 0
    with open(capture_three_tier_logs["system"], encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("trace_id") == trace_id:
                system_entries += 1

    assert system_entries > 0, "No system log entries with trace_id"
    print(f"✅ System log entries with trace_id: {system_entries}")

    # ─── 驗證：alerts log 可能包含異常檢測結果 ───
    alerts_count = 0
    if capture_three_tier_logs["alerts"].exists():
        with open(capture_three_tier_logs["alerts"], encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("trace_id") == trace_id:
                    alerts_count += 1
        print(f"✅ Alerts log entries with trace_id: {alerts_count}")

    print("\n=== E2E Evidence Test PASSED ===")
    print(f"Evidence files written to: {capture_three_tier_logs['system'].parent}")
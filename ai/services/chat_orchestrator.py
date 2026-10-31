"""
AI chat orchestration — tool loop、consent 決策、follow-up、history 寫入。

介面：``ChatOrchestrator(stream)`` 直接 yield SSE 幀字串
（``event: xxx\\ndata: {...}\\n\\n``）。AI client 可注入（任意
AIClient adapter，見 ai/tests/fakes.py）。

View 層只負責：HTTP framing（StreamingHttpResponse）與授權
（LoginRequiredMixin）。

長回應：每次 LLM 呼叫前先送一幀 ``status``（讓 proxy／瀏覽器在等待模型時
仍收得到位元組），整輪超過 ``TURN_DEADLINE_SECONDS`` 就不再發下一次呼叫，
以 ``TIMEOUT_FALLBACK`` + done 收尾。單次呼叫本身受 ai-client timeout 約束。
"""

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Tuple

from .chat_service import ChatService
from .consent_labels import describe_consent
from .consent_store import ConsentStore
from .conversation_cache import ConversationCache
from .fencing import wrap_persisted, wrap_untrusted
from .tool_registry import (
    ConsentRequirement,
    ToolError,
    ToolRegistry,
    filter_args_by_signature,
)

logger = logging.getLogger(__name__)

# 一個 turn 內模型可要求 tool 的回合數；budget 用盡後再以一次
# 「無 tools」的強制收尾呼換出綜合所有結果的文字答案（而非空道歉）。
MAX_TOOL_ROUNDS = 3

# 整輪對話的時間上限（秒）：只在發下一次 LLM 呼叫前檢查。
TURN_DEADLINE_SECONDS = 90


def _sse(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps({'type': event, **payload}, ensure_ascii=False)}\n\n"


_THINKING_FRAME = _sse("status", {"state": "thinking"})


class OutcomeKind(str, Enum):
    """每個 tool_call 的決策分類；唯獨 CONSENT_PENDING 不參與回灌
    （consent 是「等使用者」，不是「等模型」）。"""

    EXECUTED = "executed"
    ERROR = "error"
    UNKNOWN_TOOL = "unknown"
    CONSENT_PENDING = "consent"


@dataclass(frozen=True)
class ToolOutcome:
    """單一 tool_call 一輪的決策＋結果（驅動幀、回灌行、持久化行）。"""

    tool: str
    kind: OutcomeKind
    detail: str

    def summary_line(self) -> str:
        if self.kind is OutcomeKind.EXECUTED:
            return f"{self.tool}: {self.detail}"
        return f"{self.tool}: [error] {self.detail}"


_GENERIC_FALLBACK = "（AI 正在思考中，請稍後再試）"
_CONSENT_FALLBACK = "我已送出確認請求，請在上方訊息按「確認」或「取消」。"
# 非預期 tool 例外對外（幀／回灌／history）的通用訊息；細節只進 log
TOOL_UNEXPECTED_ERROR = "系統暫時無法完成這項查詢，請稍後再試。"
TIMEOUT_FALLBACK = "這個問題處理得比較久，我先停在這裡。請再問一次，或把問題拆小一點試試。"


class _TurnTimeout(Exception):
    """整輪超過 deadline：不再發下一次 LLM 呼叫。"""


class ChatOrchestrator:
    """一輪 AI 對話的完整編排（bounded tool loop / consent / follow-up / history）。"""

    def __init__(
        self,
        service: ChatService | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        turn_deadline: float = TURN_DEADLINE_SECONDS,
    ):
        self._service = service
        self._clock = clock
        self._turn_deadline = turn_deadline

    def stream(self, user, message: str) -> Generator[str, None, None]:
        service = self._service or ChatService()
        started = self._clock()

        def check_deadline():
            if self._clock() - started > self._turn_deadline:
                raise _TurnTimeout()

        history = ConversationCache.get_history(user.id)
        ConversationCache.add_message(user.id, "user", message)

        # transcript = 本 turn model 到目前為止看到的（含先前 history）。
        # 持久化是逐輪增量：每輪 append 的 marker+fence 立刻落 cache
        # （持久化形式用 wrap_persisted，fence 內資料與回灌形式相同），
        # turn 結束只補 assistant 尾條。這樣 generator 在任何 yield 點被關
        # 掉（client 斷線：GeneratorExit 是 BaseException，except Exception
        # 接不到），cache 仍等於「model 目前為止看到的」——tool 已執行、
        # 幀已送出的情況下不會只剩孤兒 user 訊息（D4b：使用者不必重問）。
        transcript: List[Dict[str, str]] = history + [{"role": "user", "content": message}]
        final_content = ""
        consent_issued = False

        try:
            for round_no in range(MAX_TOOL_ROUNDS):
                check_deadline()
                yield _THINKING_FRAME
                # 統一呼叫形狀：最後一條 = current，其餘 = history
                #（round 1 與舊的第一次呼叫完全相同）。
                response = service.chat(user.id, transcript[-1]["content"], transcript[:-1])

                if not response.tool_calls:
                    final_content = response.content
                    break

                frames, outcomes, consent_issued = self._process_tool_calls(
                    user, response.tool_calls
                )

                feedable = [o for o in outcomes if o.kind is not OutcomeKind.CONSENT_PENDING]
                if feedable:
                    # 先落 cache 再 yield 幀：幀的 yield 點被斷線時，
                    # 此輪資料必須已經在 cache 裡
                    marker = {
                        "role": "assistant",
                        "content": f"[Called tools: {', '.join(o.tool for o in feedable)}]",
                    }
                    tool_summary = "\n".join(o.summary_line() for o in feedable)
                    transcript.append(marker)
                    transcript.append(
                        {"role": "user", "content": wrap_untrusted(tool_summary)}
                    )
                    ConversationCache.add_messages(
                        user.id,
                        [
                            marker,
                            {"role": "user", "content": wrap_persisted(tool_summary)},
                        ],
                    )

                for frame in frames:
                    yield frame

                if consent_issued:
                    # consent 是「等使用者」的決策：turn 到此結束，
                    # 沒有 continuation call（執行結果在用戶下一 turn 才到 model）。
                    # D4a：與 tool_calls 同輪的中途內容（如「我幫你延期好了」）
                    # 不得外洩成最終答案——使用者還沒按確認，模型先說出完成
                    # 時表述會誤解；一律用 consent fallback。
                    final_content = _CONSENT_FALLBACK
                    break

                if not feedable:
                    # 此輪沒有可學習的結果（如缺名的 tool_call）：不燒剩餘 budget。
                    # D4a 同樣適用：中途內容不是最終答案。
                    final_content = _GENERIC_FALLBACK
                    break

                if round_no == MAX_TOOL_ROUNDS - 1:
                    # bound：三輪的 tool 都執行過了；強制「無 tools」收尾——
                    # 沒有 tools 的 request 結構上不可能回 tool_calls
                    check_deadline()
                    yield _THINKING_FRAME
                    forced = service.chat(
                        user.id,
                        transcript[-1]["content"],
                        transcript[:-1],
                        use_tools=False,
                    )
                    if forced.tool_calls:
                        logger.warning(
                            "close-out response carried tool_calls; dropped",
                            extra={"count": len(forced.tool_calls)},
                        )
                    final_content = forced.content
                    break
        except _TurnTimeout:
            logger.warning(
                "chat turn deadline exceeded",
                extra={"user_id": str(user.id), "deadline": self._turn_deadline},
            )
            final_content = TIMEOUT_FALLBACK
        except Exception:
            # 保證恰好一個 content + 一個 done：意外例外落到兜底文案
            logger.exception("chat stream failed", extra={"user_id": str(user.id)})

        if not final_content:
            final_content = _CONSENT_FALLBACK if consent_issued else _GENERIC_FALLBACK

        # turn 結束只補 assistant 尾條（各輪 tool 資料已逐輪增量落 cache）
        ConversationCache.add_messages(
            user.id, [{"role": "assistant", "content": final_content}]
        )

        yield _sse("content", {"delta": final_content})
        yield _sse("done", {})

    def _process_tool_calls(
        self, user, tool_calls: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[ToolOutcome], bool]:
        """每個 tool_call 依序產一幀 + 一個 outcome（決策在此，執行帶著使用者身份）。

        回傳 (SSE 幀字串, outcomes, 是否發出 consent)。
        """
        frames: List[str] = []
        outcomes: List[ToolOutcome] = []
        consent_issued = False

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            if not tool_name:
                continue
            arguments = tool_call.get("args") or {}
            if not isinstance(arguments, dict):
                arguments = {}
            tool_def = ToolRegistry.get_tool(tool_name)
            if tool_def:
                # 所有 tool 一律依 signature 過濾：模型多給的未知 kwarg 不會
                # 讓 tool 拋 TypeError 燒掉一輪；args 裡的 user 被濾掉，
                # 不可能覆蓋呼叫方注入的真正使用者。
                arguments = filter_args_by_signature(tool_def.func, arguments)

            if tool_def and tool_def.consent == ConsentRequirement.USER_CONFIRM:
                # 需要使用者確認：此輪不執行，consent_service 稍後帶著 user 執行；
                # 過濾後的 args 存 server-side（one-shot token），
                # 存檔＝顯示＝執行，client 回傳的 args 不可信
                missing = [
                    k for k in tool_def.parameters.get("required", []) if k not in arguments
                ]
                if missing:
                    # 缺 required 參數不發 consent（該 token 會不可執行）；
                    # 以 tool_result 告知 AI 補齊重試
                    error = f"缺少必填參數：{', '.join(missing)}"
                    outcomes.append(ToolOutcome(tool_name, OutcomeKind.ERROR, error))
                    frames.append(_sse("tool_result", {"tool": tool_name, "error": error}))
                else:
                    token = ConsentStore.create(user.id, tool_name, arguments)
                    consent_issued = True
                    outcomes.append(
                        ToolOutcome(tool_name, OutcomeKind.CONSENT_PENDING, "waiting for user")
                    )
                    frames.append(
                        _sse(
                            "consent_required",
                            {
                                "tool": tool_name,
                                "args": arguments,
                                "token": token,
                                "description": describe_consent(user, tool_name, arguments),
                            },
                        )
                    )
            elif tool_def:
                try:
                    result = tool_def.func(user=user, **arguments)
                    if not isinstance(result, (str, int, float, bool, list, dict, type(None))):
                        result = str(result)
                    outcomes.append(
                        ToolOutcome(
                            tool_name,
                            OutcomeKind.EXECUTED,
                            "" if result is None else str(result),
                        )
                    )
                    frames.append(_sse("tool_result", {"tool": tool_name, "result": result}))
                except ToolError as e:
                    # 刻意的錯誤（參數／權限）：訊息是給模型自我修正的
                    error = str(e)
                    logger.info("tool rejected call", extra={"tool_name": tool_name})
                    outcomes.append(ToolOutcome(tool_name, OutcomeKind.ERROR, error))
                    frames.append(_sse("tool_result", {"tool": tool_name, "error": error}))
                except Exception:
                    # 非預期例外：str(e) 可能含內部細節，不得進幀／回灌／history
                    logger.exception("tool execution failed", extra={"tool_name": tool_name})
                    outcomes.append(
                        ToolOutcome(tool_name, OutcomeKind.ERROR, TOOL_UNEXPECTED_ERROR)
                    )
                    frames.append(
                        _sse("tool_result", {"tool": tool_name, "error": TOOL_UNEXPECTED_ERROR})
                    )
            else:
                # 未知 tool 名：回報並回灌，模型才能自我修正
                #（靜默丟掉在 loop 下會燒掉 budget 且模型不知原因）
                error = f"未知工具：{tool_name}"
                outcomes.append(
                    ToolOutcome(tool_name, OutcomeKind.UNKNOWN_TOOL, "此工具不存在")
                )
                frames.append(_sse("tool_result", {"tool": tool_name, "error": error}))

        return frames, outcomes, consent_issued

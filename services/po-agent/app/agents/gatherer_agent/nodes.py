import os, json
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.openai import OpenAI
from .state import BriefState, PRODUCT_BRIEF_TEMPLATE, EvalResult
from .prompts import SYSTEM_BRIEF_EVAL, SYSTEM_ASK_QUESTIONS, SYSTEM_GENERATE_BRIEF

load_dotenv()

langfuse = Langfuse(
    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------- helpers ----------
def _json_from_text(text: str) -> str | None:
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("` \n\t")
        if s.lower().startswith("json"):
            s = s[4:].strip()
    if s.startswith("{") and s.endswith("}"):
        return s
    start = s.find("{")
    while start != -1:
        depth = 0; in_str = False; esc = False
        for i, ch in enumerate(s[start:], start):
            if in_str:
                if esc: esc = False
                elif ch == "\\": esc = True
                elif ch == '"': in_str = False
                continue
            if ch == '"': in_str = True
            elif ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0: return s[start:i+1]
        start = s.find("{", start + 1)
    return None

def _llm(system: str, user: str, *, as_json=False) -> str:
    kwargs = dict(
        model=MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.2,
        timeout=20,
    )
    if as_json:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        r = client.chat.completions.create(**kwargs)
        return r.choices[0].message.content or ""
    except Exception as e:
        try:
            langfuse.update_current_span(status_message=f"openai_error: {e!r}")
        except Exception:
            pass
        return ""

def _ensure_initialized(state: BriefState) -> None:
    if "brief" not in state:
        state["brief"] = PRODUCT_BRIEF_TEMPLATE.copy()
    if "iteration_count" not in state:
        state["iteration_count"] = 0
    if "retry_count" not in state:
        state["retry_count"] = 0
    if "max_iterations" not in state:
        state["max_iterations"] = 5
    if "awaiting_user" not in state:
        state["awaiting_user"] = False
    if "finalized" not in state:
        state["finalized"] = False
    state.setdefault("user_messages", [])
    state.setdefault("ai_messages", [])

def _tc(state: BriefState):
    return {"trace_id": state.get("_lf_trace_id")}

# ---------- NODES ----------
def initialize(state: BriefState, trace_id: str) -> BriefState:
    # 1) Tạo trace-id 32-hex ổn định cho phiên này và lưu lại
    lf_trace_id = langfuse.create_trace_id(seed=str(trace_id))
    state["_lf_trace_id"] = lf_trace_id

    # 2) Tạo span 'initialize' theo cách MANUAL để chắc chắn hiển thị
    span = langfuse.start_span(
        name="initialize",
        trace_context={"trace_id": lf_trace_id},
        metadata={"thread_id": trace_id},
    )
    try:
        # Cập nhật metadata/identity cho TRACE hiện tại
        try:
            langfuse.update_current_trace(
                user_id=os.getenv("LF_USER_ID"),
                session_id=os.getenv("LF_SESSION_ID"),
                metadata={"thread_id": trace_id},
                input={
                    "has_brief": bool(state.get("brief")),
                    "user_msgs": len(state.get("user_messages", [])),
                    "ai_msgs": len(state.get("ai_messages", [])),
                },
            )
        except Exception:
            pass

        # Khởi tạo state
        state.setdefault("brief", PRODUCT_BRIEF_TEMPLATE.copy())
        state.setdefault("iteration_count", 0)
        state.setdefault("retry_count", 0)
        state.setdefault("max_iterations", 5)
        state.setdefault("awaiting_user", False)
        state.setdefault("finalized", False)
        state["mode"] = None
        state.pop("force_preview", None)
    finally:
        # Kết thúc span để UI render ngay
        span.end()
        # (tuỳ chọn) ép flush nhanh đợt đầu:
        # langfuse.flush()

    return state

def collect_inputs(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="collect_inputs",
        trace_context=_tc(state),
        input=state.get("last_user_input",""),
        metadata={"thread_id": trace_id},
    ) as span:
        _ensure_initialized(state)
        if state.get("last_user_input"):
            state["user_messages"].append(state["last_user_input"])
        state["awaiting_user"] = False
        state["mode"] = None
        span.update(output={"user_messages_len": len(state["user_messages"])})
        return state

def evaluate(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="evaluate",
        trace_context=_tc(state),
        input={"has_brief": bool(state.get("brief"))},
        metadata={"thread_id": trace_id},
    ) as span:
        _ensure_initialized(state)
        brief_text = json.dumps(state["brief"], ensure_ascii=False)
        out = _llm(SYSTEM_BRIEF_EVAL, f"BRIEF_JSON={brief_text}", as_json=True)
        raw = _json_from_text(out) or _llm(SYSTEM_BRIEF_EVAL, f"BRIEF_JSON={brief_text}", as_json=False)
        raw = _json_from_text(raw)
        data = json.loads(raw) if raw else {
            "gaps":["ten_san_pham","tong_quan","van_de"],
            "score":0.0,"confidence":0.0,"status":"working","message":"parse_fail"
        }
        state["eval"] = EvalResult(**data)
        state["mode"] = None
        span.update(output=data)
        return state

def clarify(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="clarify",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ) as span:
        ev = state.get("eval"); gaps = (ev.gaps if ev else []) or []
        text = "- " + "\n- ".join([f"{g.replace('_',' ')} chưa được cung cấp." for g in gaps]) if gaps else "Cần bổ sung thông tin."
        span.update(output={"clarify": text})
        state["mode"] = None
        return state

def suggest(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="suggest",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ) as span:
        ev = state.get("eval"); gaps = (ev.gaps if ev else []) or []
        context = "\n".join(state.get("user_messages", []))
        text = _llm(SYSTEM_ASK_QUESTIONS, f"Gaps={gaps}\nContext={context}\nHãy ưu tiên 3 thông tin quan trọng nhất cần bổ sung (VI).")
        if not text:
            text = "Gợi ý: bổ sung Tên sản phẩm, Tổng quan, Vấn đề cần giải."
        state["ai_messages"].append(text)
        state["mode"] = None
        span.update(output={"suggest": text})
        return state

def ask_user(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="ask_user",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ) as span:
        ev = state.get("eval"); gaps = (ev.gaps if ev else []) or []
        context = "\n".join(state.get("user_messages", []))
        q = _llm(SYSTEM_ASK_QUESTIONS, f"Gaps={gaps}\nContext={context}\nTạo tối đa 3 câu hỏi ngắn (VI).")
        if not q:
            q = "1) Tên sản phẩm?\n2) Tổng quan ngắn?\n3) Vấn đề chính?"
        state["ai_messages"].append(q)
        state["awaiting_user"] = True
        state["mode"] = "ask_user"
        span.update(output={"questions": q})
        return state

def increment_iteration(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="increment_iteration",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ) as span:
        before = state.get("iteration_count", 0)
        state["iteration_count"] = before + 1
        state["mode"] = None
        span.update(input={"iteration_before": before}, output={"iteration_after": state["iteration_count"]})
        return state

def wait_for_user(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="wait_for_user",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ):
        state["awaiting_user"] = True
        state["mode"] = "wait_for_user"
        return state

def generate(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="generate",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ) as span:
        _ensure_initialized(state)
        context = "\n".join(state.get("user_messages", []))
        schema = json.dumps(state["brief"], ensure_ascii=False)
        text = _llm(SYSTEM_GENERATE_BRIEF, f"SCHEMA={schema}\nCONTEXT={context}\nOnly JSON.", as_json=True)
        raw = _json_from_text(text)
        if raw:
            try:
                data = json.loads(raw)
                for k, v in data.items():
                    if k in state["brief"]:
                        state["brief"][k]["value"] = v["value"] if isinstance(v, dict) and "value" in v else v
            except Exception:
                state["brief"]["tong_quan"]["value"] = text
        state["mode"] = None
        span.update(output={"brief_keys": list(state["brief"].keys())})
        return state

def validate(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="validate",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ) as span:
        missing = [k for k, meta in state["brief"].items() if meta.get("required") and not meta.get("value")]
        if missing:
            ev = EvalResult(gaps=missing, score=0.5, confidence=0.5, status="working", message="Thiếu trường bắt buộc")
        else:
            ev = EvalResult(gaps=[], score=0.85, confidence=0.85, status="done", message="Đủ thông tin cơ bản")
        state["eval"] = ev
        state["mode"] = None
        span.update(output=ev.model_dump())
        return state

def retry_decision(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="retry_decision",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ) as span:
        ev = state.get("eval")
        if state.get("force_preview"):
            state["mode"] = None
            span.update(output={"retry_count": state.get("retry_count", 0), "force_preview": True})
            return state
        if not ev or ev.status == "invalid" or (ev.confidence or 0) <= 0.7:
            state["retry_count"] = state.get("retry_count", 0) + 1
        state["mode"] = None
        span.update(output={"retry_count": state.get("retry_count", 0)})
        return state

def preview(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="preview",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ):
        state["ai_messages"].append(
            "[PREVIEW] Bản nháp brief:\n" + json.dumps(state["brief"], ensure_ascii=False, indent=2)
            + "\n\nNhập: approve | edit <ghi chú> | regen"
        )
        state["awaiting_user"] = True
        state["mode"] = "preview"
        return state

def edit_mode(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="edit_mode",
        trace_context=_tc(state),
        input=state.get("last_user_input",""),
        metadata={"thread_id": trace_id},
    ):
        note = state.get("last_user_input","")
        if note:
            arr = state["brief"]["tinh_nang_mo_rong"]["value"]
            state["brief"]["tinh_nang_mo_rong"]["value"] = (arr if isinstance(arr, list) else []) + [note]
        state["mode"] = None
        return state

def force_generate(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="force_generate",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ) as span:
        state = generate(state, trace_id)
        state["ai_messages"].append("[INFO] Force-generate vì người dùng bỏ qua câu hỏi (skip).")
        state["mode"] = None
        span.update(output={"forced": True})
        return state

def finalize(state: BriefState, trace_id: str) -> BriefState:
    with langfuse.start_as_current_span(
        name="finalize",
        trace_context=_tc(state),
        metadata={"thread_id": trace_id},
    ):
        state["finalized"] = True
        state["ai_messages"].append("[FINAL] Brief đã hoàn tất ✅")
        state["mode"] = None
        try:
            langfuse.update_current_trace(output={"finalized": True})
        except Exception:
            pass
        return state

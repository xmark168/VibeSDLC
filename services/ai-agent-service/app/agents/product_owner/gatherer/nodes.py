import os, json
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .state import BriefState, EvalResult
from templates.prompts.product_owner.gatherer import (
    EVALUATE_PROMPT,
    SUGGEST_SYSTEM,
    ASK_SYSTEM,
    GENERATE_SYSTEM,
)

load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


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
        depth = 0
        in_str = False
        esc = False
        for i, ch in enumerate(s[start:], start):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
        start = s.find("{", start + 1)
    return None


def _llm(system: str, user: str, *, as_json=False) -> str:
    try:
        if as_json:
            structured = llm.with_structured_output(dict)
            res = structured.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            return json.dumps(res)
        res = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return getattr(res, "content", "") or ""
    except Exception:
        # Avoid noisy context warnings when no active span
        return ""


def _load_product_brief_template() -> dict:
    schema_path = Path(__file__).resolve().parents[4] / "templates" / "docs" / "product_brief.json"
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        template = {}
        for key, meta in props.items():
            typ = meta.get("type")
            default_value = [] if typ == "array" else ""
            template[key] = {"required": key in required, "value": default_value}
        return template
    except Exception:
        return {
            "product_name": {"required": True, "value": ""},
            "description": {"required": True, "value": ""},
            "target_audience": {"required": True, "value": []},
            "key_features": {"required": True, "value": []},
            "benefits": {"required": True, "value": []},
            "competitors": {"required": True, "value": []},
        }


def _ensure_initialized(state: BriefState) -> None:
    if not state.get("brief"):
        state["brief"] = _load_product_brief_template()
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


def initialize(state: BriefState) -> BriefState:
    # Chuẩn hóa state thô để log input nhất quán
    if "user_messages" not in state:
        state["user_messages"] = []
    if "ai_messages" not in state:
        state["ai_messages"] = []
    if not state.get("brief"):
        state["brief"] = _load_product_brief_template()
    state.setdefault("iteration_count", 0)
    state.setdefault("retry_count", 0)
    state.setdefault("max_iterations", 5)
    state.setdefault("awaiting_user", False)
    state.setdefault("finalized", False)
    state["mode"] = None
    state.pop("force_preview", None)
    return state


def collect_inputs(state: BriefState) -> BriefState:
    _ensure_initialized(state)
    if state.get("last_user_input"):
        state["user_messages"].append(state["last_user_input"])
    state["awaiting_user"] = False
    state["mode"] = None
    return state


def evaluate(state: BriefState) -> BriefState:
    _ensure_initialized(state)
    # Format messages from conversation history
    msgs = state.get("user_messages", []) or []
    formatted_messages = (
        "\n".join([f"{i+1}. User: {m}" for i, m in enumerate(msgs)]) if msgs else "Chưa có thông tin."
    )
    prompt = EVALUATE_PROMPT.format(messages=formatted_messages)
    out = _llm("", prompt, as_json=True)
    raw = _json_from_text(out) or _llm("", prompt, as_json=False)
    raw = _json_from_text(raw)
    data = (
        json.loads(raw)
        if raw
        else {
            "gaps": ["product_name", "description"],
            "score": 0.0,
            "confidence": 0.0,
            "status": "working",
            "message": "parse_fail",
        }
    )
    # Map external status to internal literals
    ext_status = data.get("status")
    if ext_status == "incomplete":
        data["status"] = "working"
    state["eval"] = EvalResult(**data)
    state["mode"] = None
    return state


def clarify(state: BriefState) -> BriefState:
    ev = state.get("eval")
    gaps = (ev.gaps if ev else []) or []
    text = (
        "- "
        + "\n- ".join([f"{g.replace('_', ' ')} chưa được cung cấp." for g in gaps])
        if gaps
        else "Cần bổ sung thông tin."
    )
    state["mode"] = None
    return state


def suggest(state: BriefState) -> BriefState:
    ev = state.get("eval")
    gaps = (ev.gaps if ev else []) or []
    context = "\n".join(state.get("user_messages", []))
    _ = _llm(SUGGEST_SYSTEM, f"Gaps={gaps}\nContext={context}")
    state["mode"] = None
    return state


def ask_user(state: BriefState) -> BriefState:
    ev = state.get("eval")
    gaps = (ev.gaps if ev else []) or []
    context = "\n".join(state.get("user_messages", []))
    q = _llm(ASK_SYSTEM, f"Gaps={gaps}\nContext={context}")
    if not q:
        q = "1) Tên sản phẩm?\n2) Tổng quan ngắn?\n3) Vấn đề chính?"
    state["ai_messages"].append(q)
    state["awaiting_user"] = True
    state["mode"] = "ask_user"
    return state


def increment_iteration(state: BriefState) -> BriefState:
    before = state.get("iteration_count", 0)
    if state.get("mode") == "ask_user":
        state["iteration_count"] = before + 1
    state["mode"] = None
    return state


def wait_for_user(state: BriefState) -> BriefState:
    state["awaiting_user"] = True
    state["mode"] = "wait_for_user"
    return state


def generate(state: BriefState) -> BriefState:
    _ensure_initialized(state)
    context = "\n".join(state.get("user_messages", []))
    schema = json.dumps(state["brief"], ensure_ascii=False)
    text = _llm(GENERATE_SYSTEM, f"SCHEMA={schema}\nCONTEXT={context}", as_json=True)
    raw = _json_from_text(text)
    parsed_ok = False
    if raw:
        try:
            data = json.loads(raw)
            for k, v in data.items():
                if k in state["brief"]:
                    state["brief"][k]["value"] = (
                        v["value"] if isinstance(v, dict) and "value" in v else v
                    )
            parsed_ok = True
        except Exception:
            parsed_ok = False

    # Fallback 1: thử non-structured nếu structured thất bại hoặc tất cả giá trị còn trống
    def _all_empty(br: dict) -> bool:
        for meta in br.values():
            val = meta.get("value") if isinstance(meta, dict) else None
            if val not in ("", [], None):
                return False
        return True

    if (not parsed_ok) or _all_empty(state["brief"]):
        text2 = _llm(GENERATE_SYSTEM, f"SCHEMA={schema}\nCONTEXT={context}", as_json=False)
        raw2 = _json_from_text(text2)
        if raw2:
            try:
                data2 = json.loads(raw2)
                for k, v in data2.items():
                    if k in state["brief"]:
                        state["brief"][k]["value"] = (
                            v["value"] if isinstance(v, dict) and "value" in v else v
                        )
                parsed_ok = True
            except Exception:
                parsed_ok = False

    # Fallback 2: nếu vẫn rỗng, điền tối thiểu từ ngữ cảnh
    if _all_empty(state["brief"]):
        # description = toàn bộ ngữ cảnh
        if "description" in state["brief"]:
            state["brief"]["description"]["value"] = context.strip()
        # product_name: heuristics từ "Tên ứng dụng:" hoặc "Tên sản phẩm:"
        ctx_lower = context.lower()
        name = ""
        for marker in ["tên ứng dụng:", "tên sản phẩm:"]:
            idx = ctx_lower.find(marker)
            if idx != -1:
                seg = context[idx + len(marker):].strip()
                # lấy tới dấu chấm hoặc xuống dòng đầu tiên
                stop_idx = len(seg)
                for ch in [".", "\n"]:
                    p = seg.find(ch)
                    if p != -1:
                        stop_idx = min(stop_idx, p)
                name = seg[:stop_idx].strip()
                break
        if name and "product_name" in state["brief"]:
            state["brief"]["product_name"]["value"] = name
        # target_audience: đoán nhanh
        if "target_audience" in state["brief"] and "sinh viên" in ctx_lower:
            state["brief"]["target_audience"]["value"] = ["Sinh viên"]
    state["mode"] = None
    return state


def validate(state: BriefState) -> BriefState:
    missing = [k for k, meta in state["brief"].items() if meta.get("required") and not meta.get("value")]
    if missing:
        ev = EvalResult(
            gaps=missing,
            score=0.5,
            confidence=0.5,
            status="working",
            message="Thiếu trường bắt buộc",
        )
    else:
        ev = EvalResult(
            gaps=[],
            score=0.85,
            confidence=0.85,
            status="done",
            message="Đủ thông tin cơ bản",
        )
    state["eval"] = ev
    state["mode"] = None
    return state


def retry_decision(state: BriefState) -> BriefState:
    ev = state.get("eval")
    if state.get("force_preview"):
        state["mode"] = None
        return state
    if not ev or ev.status == "invalid" or (ev.confidence or 0) <= 0.7:
        state["retry_count"] = state.get("retry_count", 0) + 1
    state["mode"] = None
    return state


def preview(state: BriefState) -> BriefState:
    state["ai_messages"].append(
        "[PREVIEW] Bản nháp brief:\n"
        + json.dumps(state["brief"], ensure_ascii=False, indent=2)
        + "\n\nNhập: approve | edit <ghi chú> | regen"
    )
    state["awaiting_user"] = True
    state["mode"] = "preview"
    return state


def edit_mode(state: BriefState) -> BriefState:
    note = state.get("last_user_input", "")
    if note and "key_features" in state["brief"]:
        arr = state["brief"]["key_features"]["value"]
        state["brief"]["key_features"]["value"] = (arr if isinstance(arr, list) else []) + [note]
    state["mode"] = None
    return state


def force_generate(state: BriefState) -> BriefState:
    state = generate(state)
    state["ai_messages"].append("[INFO] Force-generate vì người dùng bỏ qua câu hỏi (skip).")
    state["mode"] = None
    return state


def finalize(state: BriefState) -> BriefState:
    state["finalized"] = True
    state["ai_messages"].append("[FINAL] Brief đã hoàn tất ✅")
    state["mode"] = None
    return state



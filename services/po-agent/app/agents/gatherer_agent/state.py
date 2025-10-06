from typing import Dict, List, Literal, TypedDict
from pydantic import BaseModel, Field

PRODUCT_BRIEF_TEMPLATE = {
    "ten_san_pham": {"required": True, "value": ""},
    "tong_quan": {"required": True, "value": ""},
    "phien_ban": {"required": False, "value": "1.0"},
    "van_de": {"required": True, "value": ""},
    "giai_phap": {"required": True, "value": ""},
    "gia_tri_doc_dao": {"required": True, "value": ""},
    "doi_tuong_muc_tieu": {"required": True, "value": ""},
    "doi_thu_canh_tranh": {"required": False, "value": []},
    "muc_tieu": {"required": True, "value": ""},
    "chi_so_thanh_cong": {"required": True, "value": []},
    "tinh_nang_chinh": {"required": True, "value": []},
    "tinh_nang_mo_rong": {"required": False, "value": []},
    "ngoai_pham_vi": {"required": False, "value": []},
}

class EvalResult(BaseModel):
    gaps: List[str] = Field(default_factory=list)
    score: float = 0.0
    confidence: float = 0.0
    status: Literal["working","done","invalid"] = "working"
    message: str = ""

class BriefState(TypedDict, total=False):
    # I/O
    last_user_input: str
    user_messages: List[str]
    ai_messages: List[str]

    # working memory
    brief: Dict
    eval: EvalResult
    iteration_count: int
    max_iterations: int
    retry_count: int
    awaiting_user: bool
    finalized: bool
    force_preview: bool
    mode: str

"""Pydantic schemas for Retro Coordinator structured LLM outputs."""

from pydantic import BaseModel, Field

# TraDS ============= Simplified schemas for rules generation
class AgentReportsOutput(BaseModel):
    """Output from LLM for generating individual agent reports."""

    po_report: str = Field(
        description="Product Owner report về sprint (dạng: ✅ Đã hoàn thành + 🚧 Vấn đề gặp phải)"
    )

    dev_report: str = Field(
        description="Developer report về sprint (dạng: ✅ Đã hoàn thành + 🚧 Vấn đề gặp phải)"
    )

    tester_report: str = Field(
        description="Tester report về sprint (dạng: ✅ Đã hoàn thành + 🚧 Vấn đề gặp phải)"
    )


class ProjectRulesOutput(BaseModel):
    """Output from LLM for generating project rules."""

    overview_summary: str = Field(
        description="Brief sprint overview summary (2-3 sentences) highlighting achievements and key issues"
    )

    what_went_well: str = Field(
        description="Bullet points of what went well in the sprint"
    )

    blockers_summary: str = Field(
        description="Categorized summary of blockers by type (PO/Dev/Tester)"
    )

    po_rules: str = Field(
        description="Actionable rules/guidelines for Product Owner for next sprint (bullet points)"
    )

    dev_rules: str = Field(
        description="Actionable rules/guidelines for Developers for next sprint (bullet points)"
    )

    tester_rules: str = Field(
        description="Actionable rules/guidelines for Testers for next sprint (bullet points)"
    )
# ==============================


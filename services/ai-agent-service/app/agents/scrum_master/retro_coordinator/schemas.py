"""Pydantic schemas for Retro Coordinator structured LLM outputs."""

from pydantic import BaseModel, Field
from typing import List


class ImprovementIdeaOutput(BaseModel):
    """Single improvement idea with specific details."""
    
    title: str = Field(
        description="Specific, actionable title (not generic like 'Improve communication')"
    )
    description: str = Field(
        description="Detailed description of the improvement and why it matters"
    )
    related_issue_ids: List[str] = Field(
        description="IDs of related issues from categorized_issues"
    )
    expected_benefit: str = Field(
        description="Specific, measurable benefit (e.g., 'Reduce deployment time by 30%')"
    )
    implementation_steps: List[str] = Field(
        description="3-5 concrete steps to implement this improvement"
    )
    success_metrics: List[str] = Field(
        description="How to measure success (e.g., 'Zero blocker tickets for 2 sprints')"
    )
    effort_estimate: str = Field(
        description="Effort estimate: 'low', 'medium', or 'high'"
    )
    priority: str = Field(
        description="Priority based on impact/effort ratio: 'high', 'medium', or 'low'"
    )
    risks: List[str] = Field(
        description="Potential risks and mitigation strategies"
    )


class GenerateIdeasOutput(BaseModel):
    """Output from generate_ideas node with prioritized improvement ideas."""
    
    ideas: List[ImprovementIdeaOutput] = Field(
        description="Top 3-5 improvement ideas prioritized by impact/effort ratio"
    )
    rationale: str = Field(
        description="Brief explanation of why these ideas were selected and prioritized"
    )


class ActionItemOutput(BaseModel):
    """Single action item following SMART criteria."""
    
    title: str = Field(
        description="Specific, actionable title describing what needs to be done"
    )
    description: str = Field(
        description="Detailed description including what, why, and how"
    )
    owner: str = Field(
        description="Specific role responsible: 'Developer Team', 'Tester Team', or 'Scrum Master'"
    )
    due_date: str = Field(
        description="Specific date or milestone (e.g., 'Sprint 5 Day 3', 'End of Week 2')"
    )
    priority: str = Field(
        description="Priority based on urgency and impact: 'high', 'medium', or 'low'"
    )
    related_improvement_id: str = Field(
        description="ID of the related improvement idea (e.g., 'IDEA-001')"
    )
    acceptance_criteria: List[str] = Field(
        description="Clear criteria to verify when this action is complete"
    )
    dependencies: List[str] = Field(
        description="Other action IDs or prerequisites that must be completed first"
    )


class DefineActionsOutput(BaseModel):
    """Output from define_actions node with SMART action items."""
    
    actions: List[ActionItemOutput] = Field(
        description="Top 3-5 action items with clear ownership and timeline"
    )
    implementation_plan: str = Field(
        description="Overall plan for executing these actions in the next sprint"
    )


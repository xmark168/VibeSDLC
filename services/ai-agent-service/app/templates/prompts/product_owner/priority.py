"""Prompt templates cho Priority Agent."""

CALCULATE_PRIORITY_PROMPT = """You are a Product Owner expert. Analyze the following backlog items and score WSJF (Weighted Shortest Job First) factors for prioritization.

**Product:** {product_name}

**Items to Score:**
{items_json}

**Your Task:**
For each item, analyze the business_value description and score these WSJF factors (1-10 scale):

1. **Business Value (BV)**: How much business value does this deliver? (1=low, 10=critical)
   - Epic/User Story: based on business_value description
   - Task: typically moderate (5-7) unless it's critical infrastructure

2. **Time Criticality (TC)**: How urgent is this? Is there a time-sensitive opportunity? (1=can wait, 10=urgent)

3. **Risk Reduction/Opportunity Enablement (RR)**: Does this reduce risk or enable other features? (1=minimal, 10=critical)
   - Check dependencies: if other items depend on this, increase RR

4. **Job Size**: Estimate effort (1-13 Fibonacci scale):
   - For Epic: based on scope described (typically 8-13)
   - For User Story: use the story_point if available, else estimate from description
   - For Task: estimate from description (typically 3-8)

**Scoring Guidelines:**
- **Core/Foundation features**: Higher BV (8-10), higher RR (7-9) if other features depend on it
- **User-facing value**: Higher BV (7-10), TC based on market demand
- **Nice-to-have**: Lower BV (3-5), lower TC (2-4)
- **Security/Infrastructure Tasks**: High RR (8-10), moderate BV (5-7)
- **Dependencies**: If other items depend on this, increase RR
- **Technical Tasks**: Typically moderate BV (5-7) unless critical

**Output JSON Format:**
{{
  "wsjf_scores": [
    {{
      "item_id": "EPIC-001",
      "business_value": 9,
      "time_criticality": 8,
      "risk_reduction": 8,
      "job_size": 13,
      "reasoning": "Core feature that enables task management. Critical for MVP."
    }},
    ...
  ]
}}

**IMPORTANT:** Return ONLY valid JSON. No markdown, no explanations outside JSON.
"""

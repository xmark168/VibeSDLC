"""
Planning Tools

Tools để support planning process: task parsing, estimation, validation.
"""

import json
import re
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool


@tool
def task_parser_tool(
    task_description: str,
    parsing_mode: str = "comprehensive"
) -> str:
    """
    Parse task description để extract requirements và acceptance criteria.
    
    Args:
        task_description: Raw task description
        parsing_mode: Mode of parsing ('basic', 'comprehensive')
        
    Returns:
        JSON string với parsed task information
    """
    try:
        result = {
            "original_description": task_description,
            "parsing_mode": parsing_mode
        }
        
        # Extract basic information
        result["task_type"] = determine_task_type(task_description)
        result["priority"] = extract_priority(task_description)
        result["complexity_indicators"] = find_complexity_indicators(task_description)
        
        if parsing_mode == "comprehensive":
            # Extract requirements
            result["functional_requirements"] = extract_functional_requirements(task_description)
            result["acceptance_criteria"] = extract_acceptance_criteria(task_description)
            result["business_rules"] = extract_business_rules(task_description)
            result["technical_specs"] = extract_technical_specs(task_description)
            result["constraints"] = extract_constraints(task_description)
            result["assumptions"] = extract_assumptions(task_description)
        
        # Extract entities and actions
        result["entities"] = extract_entities(task_description)
        result["actions"] = extract_actions(task_description)
        result["user_roles"] = extract_user_roles(task_description)
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Task parsing failed: {str(e)}",
            "original_description": task_description
        }, indent=2)


@tool
def effort_estimation_tool(
    task_info: Dict[str, Any],
    estimation_method: str = "story_points"
) -> str:
    """
    Estimate effort cho task based on complexity và requirements.
    
    Args:
        task_info: Task information từ task_parser_tool
        estimation_method: Method for estimation ('story_points', 'hours', 'both')
        
    Returns:
        JSON string với effort estimation
    """
    try:
        # Base estimation factors
        base_hours = 2.0
        complexity_multiplier = 1.0
        
        # Analyze complexity factors
        complexity_score = calculate_complexity_score(task_info)
        
        # Adjust based on task type
        task_type = task_info.get("task_type", "feature")
        type_multipliers = {
            "feature": 1.0,
            "bug_fix": 0.7,
            "refactor": 1.2,
            "infrastructure": 1.5,
            "integration": 1.3,
            "ui_change": 0.8,
            "api_change": 1.1,
            "database_change": 1.4
        }
        
        complexity_multiplier = type_multipliers.get(task_type, 1.0)
        
        # Calculate base effort
        estimated_hours = base_hours * complexity_multiplier * (complexity_score / 5.0)
        
        # Adjust for specific indicators
        indicators = task_info.get("complexity_indicators", [])
        for indicator in indicators:
            if "database" in indicator.lower():
                estimated_hours *= 1.3
            elif "api" in indicator.lower():
                estimated_hours *= 1.2
            elif "integration" in indicator.lower():
                estimated_hours *= 1.4
            elif "ui" in indicator.lower() or "frontend" in indicator.lower():
                estimated_hours *= 0.9
        
        # Convert to story points (Fibonacci sequence)
        story_points = hours_to_story_points(estimated_hours)
        
        # Calculate confidence level
        confidence = calculate_estimation_confidence(task_info)
        
        result = {
            "task_type": task_type,
            "complexity_score": complexity_score,
            "estimated_hours": round(estimated_hours, 1),
            "story_points": story_points,
            "confidence_level": confidence,
            "estimation_breakdown": {
                "base_hours": base_hours,
                "complexity_multiplier": complexity_multiplier,
                "type_adjustment": type_multipliers.get(task_type, 1.0),
                "indicator_adjustments": len(indicators)
            }
        }
        
        if estimation_method == "hours":
            result = {k: v for k, v in result.items() if "story_points" not in k}
        elif estimation_method == "story_points":
            result = {k: v for k, v in result.items() if "hours" not in k}
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Effort estimation failed: {str(e)}",
            "estimated_hours": 4.0,
            "story_points": 3
        }, indent=2)


@tool
def risk_assessment_tool(
    task_info: Dict[str, Any],
    codebase_context: str = ""
) -> str:
    """
    Assess risks associated với task implementation.
    
    Args:
        task_info: Task information
        codebase_context: Context about existing codebase
        
    Returns:
        JSON string với risk assessment
    """
    try:
        risks = []
        
        # Technical risks
        technical_risks = assess_technical_risks(task_info, codebase_context)
        risks.extend(technical_risks)
        
        # Business risks
        business_risks = assess_business_risks(task_info)
        risks.extend(business_risks)
        
        # Timeline risks
        timeline_risks = assess_timeline_risks(task_info)
        risks.extend(timeline_risks)
        
        # Dependency risks
        dependency_risks = assess_dependency_risks(task_info)
        risks.extend(dependency_risks)
        
        # Calculate overall risk level
        overall_risk = calculate_overall_risk(risks)
        
        # Generate mitigation strategies
        mitigation_strategies = generate_mitigation_strategies(risks)
        
        result = {
            "risks": risks,
            "overall_risk_level": overall_risk,
            "total_risks": len(risks),
            "risk_distribution": {
                "high": len([r for r in risks if r["impact"] == "high"]),
                "medium": len([r for r in risks if r["impact"] == "medium"]),
                "low": len([r for r in risks if r["impact"] == "low"])
            },
            "mitigation_strategies": mitigation_strategies
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Risk assessment failed: {str(e)}",
            "risks": [],
            "overall_risk_level": "medium"
        }, indent=2)


def determine_task_type(description: str) -> str:
    """Determine task type từ description."""
    description_lower = description.lower()
    
    if any(word in description_lower for word in ["bug", "fix", "error", "issue"]):
        return "bug_fix"
    elif any(word in description_lower for word in ["refactor", "cleanup", "optimize"]):
        return "refactor"
    elif any(word in description_lower for word in ["database", "migration", "schema"]):
        return "database_change"
    elif any(word in description_lower for word in ["api", "endpoint", "service"]):
        return "api_change"
    elif any(word in description_lower for word in ["ui", "frontend", "interface", "design"]):
        return "ui_change"
    elif any(word in description_lower for word in ["integrate", "integration", "connect"]):
        return "integration"
    elif any(word in description_lower for word in ["infrastructure", "deploy", "config"]):
        return "infrastructure"
    else:
        return "feature"


def extract_priority(description: str) -> str:
    """Extract priority từ description."""
    description_lower = description.lower()
    
    if any(word in description_lower for word in ["urgent", "critical", "high priority"]):
        return "high"
    elif any(word in description_lower for word in ["low priority", "nice to have"]):
        return "low"
    else:
        return "medium"


def find_complexity_indicators(description: str) -> List[str]:
    """Find complexity indicators trong description."""
    indicators = []
    description_lower = description.lower()
    
    complexity_patterns = {
        "database": ["database", "db", "migration", "schema", "sql"],
        "api": ["api", "endpoint", "service", "rest", "graphql"],
        "integration": ["integrate", "third-party", "external", "webhook"],
        "ui": ["ui", "frontend", "interface", "component", "design"],
        "authentication": ["auth", "login", "permission", "security"],
        "performance": ["performance", "optimize", "cache", "speed"],
        "testing": ["test", "testing", "coverage", "validation"]
    }
    
    for category, patterns in complexity_patterns.items():
        if any(pattern in description_lower for pattern in patterns):
            indicators.append(category)
    
    return indicators


def extract_functional_requirements(description: str) -> List[str]:
    """Extract functional requirements."""
    requirements = []
    
    # Look for "should", "must", "need to" patterns
    patterns = [
        r"should\s+([^.]+)",
        r"must\s+([^.]+)",
        r"need\s+to\s+([^.]+)",
        r"will\s+([^.]+)",
        r"can\s+([^.]+)"
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        requirements.extend([match.strip() for match in matches])
    
    return requirements[:5]  # Limit to 5 most relevant


def extract_acceptance_criteria(description: str) -> List[str]:
    """Extract acceptance criteria."""
    criteria = []
    
    # Look for criteria patterns
    lines = description.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith(('- ', '* ', '• ')):
            criteria.append(line[2:].strip())
        elif re.match(r'^\d+\.', line):
            criteria.append(re.sub(r'^\d+\.\s*', '', line))
    
    return criteria


def extract_business_rules(description: str) -> List[str]:
    """Extract business rules."""
    rules = []
    
    # Look for business rule patterns
    rule_patterns = [
        r"rule:\s*([^.]+)",
        r"constraint:\s*([^.]+)",
        r"requirement:\s*([^.]+)"
    ]
    
    for pattern in rule_patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        rules.extend([match.strip() for match in matches])
    
    return rules


def extract_technical_specs(description: str) -> List[str]:
    """Extract technical specifications."""
    specs = []
    
    # Look for technical terms
    tech_patterns = [
        r"using\s+([^.]+)",
        r"implement\s+([^.]+)",
        r"technology:\s*([^.]+)"
    ]
    
    for pattern in tech_patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        specs.extend([match.strip() for match in matches])
    
    return specs


def extract_constraints(description: str) -> List[str]:
    """Extract constraints."""
    constraints = []
    
    constraint_keywords = ["cannot", "must not", "should not", "limitation", "constraint"]
    
    sentences = description.split('.')
    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in constraint_keywords):
            constraints.append(sentence.strip())
    
    return constraints


def extract_assumptions(description: str) -> List[str]:
    """Extract assumptions."""
    assumptions = []
    
    assumption_patterns = [
        r"assume\s+([^.]+)",
        r"assuming\s+([^.]+)",
        r"assumption:\s*([^.]+)"
    ]
    
    for pattern in assumption_patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        assumptions.extend([match.strip() for match in matches])
    
    return assumptions


def extract_entities(description: str) -> List[str]:
    """Extract business entities."""
    # Simple entity extraction based on capitalized words
    entities = []
    words = description.split()
    
    for word in words:
        if word[0].isupper() and len(word) > 2 and word.isalpha():
            entities.append(word)
    
    return list(set(entities))[:10]  # Unique entities, limit 10


def extract_actions(description: str) -> List[str]:
    """Extract actions/verbs."""
    action_words = ["create", "update", "delete", "add", "remove", "modify", "implement", "build", "develop"]
    
    actions = []
    description_lower = description.lower()
    
    for action in action_words:
        if action in description_lower:
            actions.append(action)
    
    return actions


def extract_user_roles(description: str) -> List[str]:
    """Extract user roles."""
    role_patterns = [
        r"as\s+a\s+([^,]+)",
        r"user\s+([^,]+)",
        r"role:\s*([^.]+)"
    ]
    
    roles = []
    for pattern in role_patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        roles.extend([match.strip() for match in matches])
    
    return roles


def calculate_complexity_score(task_info: Dict[str, Any]) -> int:
    """Calculate complexity score 1-10."""
    score = 3  # Base score
    
    # Adjust based on indicators
    indicators = task_info.get("complexity_indicators", [])
    score += len(indicators)
    
    # Adjust based on requirements
    requirements = task_info.get("functional_requirements", [])
    score += min(len(requirements), 3)
    
    # Adjust based on task type
    task_type = task_info.get("task_type", "feature")
    type_scores = {
        "bug_fix": 2,
        "ui_change": 3,
        "feature": 4,
        "api_change": 5,
        "integration": 6,
        "database_change": 7,
        "infrastructure": 8,
        "refactor": 6
    }
    
    score = max(score, type_scores.get(task_type, 4))
    
    return min(score, 10)


def hours_to_story_points(hours: float) -> int:
    """Convert hours to Fibonacci story points."""
    if hours <= 1:
        return 1
    elif hours <= 2:
        return 2
    elif hours <= 4:
        return 3
    elif hours <= 8:
        return 5
    elif hours <= 16:
        return 8
    elif hours <= 24:
        return 13
    else:
        return 21


def calculate_estimation_confidence(task_info: Dict[str, Any]) -> str:
    """Calculate confidence level for estimation."""
    confidence_score = 0.7  # Base confidence
    
    # Adjust based on available information
    if task_info.get("functional_requirements"):
        confidence_score += 0.1
    if task_info.get("acceptance_criteria"):
        confidence_score += 0.1
    if task_info.get("technical_specs"):
        confidence_score += 0.1
    
    # Reduce confidence for complex tasks
    complexity = task_info.get("complexity_score", 5)
    if complexity > 7:
        confidence_score -= 0.2
    elif complexity > 5:
        confidence_score -= 0.1
    
    if confidence_score >= 0.8:
        return "high"
    elif confidence_score >= 0.6:
        return "medium"
    else:
        return "low"


def assess_technical_risks(task_info: Dict[str, Any], codebase_context: str) -> List[Dict[str, Any]]:
    """Assess technical risks."""
    risks = []
    
    complexity = task_info.get("complexity_score", 5)
    if complexity > 7:
        risks.append({
            "type": "technical",
            "description": "High complexity may lead to implementation challenges",
            "impact": "high",
            "probability": "medium"
        })
    
    indicators = task_info.get("complexity_indicators", [])
    if "database" in indicators:
        risks.append({
            "type": "technical",
            "description": "Database changes may cause data integrity issues",
            "impact": "high",
            "probability": "low"
        })
    
    if "integration" in indicators:
        risks.append({
            "type": "technical",
            "description": "Third-party integration may be unreliable",
            "impact": "medium",
            "probability": "medium"
        })
    
    return risks


def assess_business_risks(task_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Assess business risks."""
    risks = []
    
    priority = task_info.get("priority", "medium")
    if priority == "high":
        risks.append({
            "type": "business",
            "description": "High priority task failure may impact business goals",
            "impact": "high",
            "probability": "low"
        })
    
    return risks


def assess_timeline_risks(task_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Assess timeline risks."""
    risks = []
    
    estimated_hours = task_info.get("estimated_hours", 4)
    if estimated_hours > 16:
        risks.append({
            "type": "timeline",
            "description": "Large task may exceed estimated timeline",
            "impact": "medium",
            "probability": "medium"
        })
    
    return risks


def assess_dependency_risks(task_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Assess dependency risks."""
    risks = []
    
    indicators = task_info.get("complexity_indicators", [])
    if "integration" in indicators:
        risks.append({
            "type": "dependency",
            "description": "External dependencies may cause delays",
            "impact": "medium",
            "probability": "medium"
        })
    
    return risks


def calculate_overall_risk(risks: List[Dict[str, Any]]) -> str:
    """Calculate overall risk level."""
    if not risks:
        return "low"
    
    high_risks = [r for r in risks if r["impact"] == "high"]
    if high_risks:
        return "high"
    
    medium_risks = [r for r in risks if r["impact"] == "medium"]
    if len(medium_risks) > 2:
        return "high"
    elif medium_risks:
        return "medium"
    
    return "low"


def generate_mitigation_strategies(risks: List[Dict[str, Any]]) -> List[str]:
    """Generate mitigation strategies for risks."""
    strategies = []
    
    for risk in risks:
        if risk["type"] == "technical":
            strategies.append("Conduct thorough technical review and testing")
        elif risk["type"] == "business":
            strategies.append("Maintain regular stakeholder communication")
        elif risk["type"] == "timeline":
            strategies.append("Break down into smaller tasks and track progress")
        elif risk["type"] == "dependency":
            strategies.append("Identify alternative solutions and fallback plans")
    
    return list(set(strategies))  # Remove duplicates

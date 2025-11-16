"""Rule Service for managing project rules and knowledge base.

This service provides methods to:
1. Retrieve relevant rules for a project based on tags
2. Save new rules extracted from blockers
3. Track rule effectiveness
4. Archive low-performing rules
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4


class ProjectRule:
    """In-memory representation of a project rule.
    
    Note: This is a simplified version for POC. In production, this should
    use SQLModel and connect to the database via SQLAlchemy session.
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        project_id: str = "project-001",
        rule_type: str = "blocker_prevention",
        title: str = "",
        description: str = "",
        tags: Optional[list[str]] = None,
        category: str = "technical",
        severity: str = "medium",
        source_blocker_id: Optional[str] = None,
        source_type: str = "daily_blocker",
        created_by: str = "scrum_master",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        applied_count: int = 0,
        success_count: int = 0,
        effectiveness_score: float = 0.0,
        is_active: bool = True,
        archived_at: Optional[datetime] = None
    ):
        self.id = id or str(uuid4())
        self.project_id = project_id
        self.rule_type = rule_type
        self.title = title
        self.description = description
        self.tags = tags or []
        self.category = category
        self.severity = severity
        self.source_blocker_id = source_blocker_id
        self.source_type = source_type
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.applied_count = applied_count
        self.success_count = success_count
        self.effectiveness_score = effectiveness_score
        self.is_active = is_active
        self.archived_at = archived_at
    
    def model_dump(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "rule_type": self.rule_type,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "severity": self.severity,
            "source_blocker_id": self.source_blocker_id,
            "source_type": self.source_type,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "applied_count": self.applied_count,
            "success_count": self.success_count,
            "effectiveness_score": self.effectiveness_score,
            "is_active": self.is_active,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None
        }


class RuleService:
    """Service for retrieving and managing project rules.
    
    Note: This is a simplified in-memory implementation for POC.
    In production, this should use SQLAlchemy session to query the database.
    """
    
    # In-memory storage for POC (simulates database)
    _rules_storage: dict[str, list[ProjectRule]] = {}
    
    @classmethod
    def save_rule(cls, rule: ProjectRule) -> ProjectRule:
        """Save a new rule to storage.
        
        Args:
            rule: ProjectRule instance to save
            
        Returns:
            Saved ProjectRule instance
        """
        project_id = rule.project_id
        
        if project_id not in cls._rules_storage:
            cls._rules_storage[project_id] = []
        
        cls._rules_storage[project_id].append(rule)
        
        print(f"   💾 Saved rule: {rule.title} (ID: {rule.id})")
        
        return rule
    
    @classmethod
    def get_project_rules(
        cls,
        project_id: str,
        tags: Optional[list[str]] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10
    ) -> list[ProjectRule]:
        """Retrieve relevant rules for a project.
        
        Args:
            project_id: Project ID
            tags: Filter by tags (OR logic - any tag matches)
            category: Filter by category
            severity: Filter by severity
            limit: Max number of rules to return
            
        Returns:
            List of matching ProjectRule objects, ordered by effectiveness
        """
        # Get all rules for project
        all_rules = cls._rules_storage.get(project_id, [])
        
        # Filter by active status
        filtered_rules = [r for r in all_rules if r.is_active]
        
        # Filter by tags (if any tag matches)
        if tags:
            filtered_rules = [
                r for r in filtered_rules
                if any(tag in r.tags for tag in tags)
            ]
        
        # Filter by category
        if category:
            filtered_rules = [r for r in filtered_rules if r.category == category]
        
        # Filter by severity
        if severity:
            filtered_rules = [r for r in filtered_rules if r.severity == severity]
        
        # Sort by effectiveness score (descending), then by created_at (newest first)
        filtered_rules.sort(
            key=lambda r: (r.effectiveness_score, r.created_at),
            reverse=True
        )
        
        # Limit results
        return filtered_rules[:limit]
    
    @classmethod
    def increment_rule_usage(
        cls,
        project_id: str,
        rule_id: str,
        success: bool = True
    ) -> Optional[ProjectRule]:
        """Track rule application and update effectiveness score.
        
        Args:
            project_id: Project ID
            rule_id: Rule ID
            success: Whether applying the rule prevented a blocker
            
        Returns:
            Updated ProjectRule or None if not found
        """
        all_rules = cls._rules_storage.get(project_id, [])
        
        for rule in all_rules:
            if rule.id == rule_id:
                rule.applied_count += 1
                if success:
                    rule.success_count += 1
                
                # Update effectiveness score
                if rule.applied_count > 0:
                    rule.effectiveness_score = rule.success_count / rule.applied_count
                
                rule.updated_at = datetime.now()
                
                print(f"   📊 Updated rule usage: {rule.title}")
                print(f"      Applied: {rule.applied_count} | Success: {rule.success_count} | Score: {rule.effectiveness_score:.2f}")
                
                return rule
        
        return None
    
    @classmethod
    def archive_rule(cls, project_id: str, rule_id: str) -> Optional[ProjectRule]:
        """Archive a rule (mark as inactive).
        
        Args:
            project_id: Project ID
            rule_id: Rule ID
            
        Returns:
            Archived ProjectRule or None if not found
        """
        all_rules = cls._rules_storage.get(project_id, [])
        
        for rule in all_rules:
            if rule.id == rule_id:
                rule.is_active = False
                rule.archived_at = datetime.now()
                rule.updated_at = datetime.now()
                
                print(f"   🗄️  Archived rule: {rule.title}")
                
                return rule
        
        return None
    
    @classmethod
    def get_all_rules(cls, project_id: str) -> list[ProjectRule]:
        """Get all rules for a project (including archived).
        
        Args:
            project_id: Project ID
            
        Returns:
            List of all ProjectRule objects
        """
        return cls._rules_storage.get(project_id, [])
    
    @classmethod
    def clear_storage(cls):
        """Clear all rules from storage (for testing)."""
        cls._rules_storage.clear()


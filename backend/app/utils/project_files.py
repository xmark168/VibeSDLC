"""Project Files Manager - Inspired by MetaGPT's file-based approach.

Manages project files like PRD, user stories, and interview transcripts.
All files are stored in the project workspace for version control and team collaboration.

File Structure:
    projects/{project_id}/
    ├── docs/
    │   ├── prd.md              # Product Requirements Document (human-readable)
    │   ├── prd.json            # PRD structured data
    │   ├── user-stories.md     # All user stories in one file
    │   └── interviews/
    │       └── {session_id}.md # Interview transcripts
    └── src/
        └── ... (source code)
"""

from pathlib import Path
from typing import Optional
import json
import aiofiles
from datetime import datetime, timezone


class ProjectFiles:
    """Manage project files (PRD, stories, interviews)"""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.docs_path = self.project_path / "docs"
        self.prd_path = self.docs_path / "prd.md"
        self.prd_json_path = self.docs_path / "prd.json"
        self.user_stories_path = self.docs_path / "user-stories.md"
        self.interviews_path = self.docs_path / "interviews"
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.docs_path.mkdir(parents=True, exist_ok=True)
        self.interviews_path.mkdir(parents=True, exist_ok=True)
    
    async def save_prd(self, prd_data: dict) -> Path:
        """Save PRD to both JSON and Markdown.
        
        Args:
            prd_data: Dictionary containing PRD content
            
        Returns:
            Path to the saved markdown file
        """
        # Add metadata
        prd_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Save JSON (structured data)
        async with aiofiles.open(self.prd_json_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(prd_data, indent=2, ensure_ascii=False))
        
        # Save Markdown (human-readable)
        md_content = self._prd_to_markdown(prd_data)
        async with aiofiles.open(self.prd_path, 'w', encoding='utf-8') as f:
            await f.write(md_content)
        
        return self.prd_path
    
    async def load_prd(self) -> Optional[dict]:
        """Load existing PRD from JSON file.
        
        Returns:
            PRD data dictionary or None if not found
        """
        if not self.prd_json_path.exists():
            return None
        
        try:
            async with aiofiles.open(self.prd_json_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception:
            return None
    
    async def save_user_stories(self, stories_data: list[dict]) -> Path:
        """Save all user stories to a single markdown file.
        
        Args:
            stories_data: List of story dictionaries
            
        Returns:
            Path to the saved user stories file
        """
        md_content = self._stories_to_markdown(stories_data)
        
        async with aiofiles.open(self.user_stories_path, 'w', encoding='utf-8') as f:
            await f.write(md_content)
        
        return self.user_stories_path
    
    async def append_user_story(self, story_data: dict) -> Path:
        """Append a single user story to the user-stories.md file.
        
        Args:
            story_data: Story dictionary
            
        Returns:
            Path to the updated user stories file
        """
        # Load existing stories first
        existing_stories = await self.load_user_stories()
        existing_stories.append(story_data)
        
        return await self.save_user_stories(existing_stories)
    
    async def load_user_stories(self) -> list[dict]:
        """Load all user stories from file.
        
        Returns:
            List of story dictionaries (empty list if file doesn't exist)
        """
        if not self.user_stories_path.exists():
            return []
        
        # For now, return empty list - would need to parse markdown
        # In practice, stories should be loaded from database, not parsed from file
        return []
    
    async def save_interview(self, session_id: str, transcript: str) -> Path:
        """Save interview transcript to markdown file.
        
        Args:
            session_id: Interview session identifier
            transcript: Interview transcript content
            
        Returns:
            Path to the saved interview file
        """
        interview_file = self.interviews_path / f"{session_id}.md"
        
        async with aiofiles.open(interview_file, 'w', encoding='utf-8') as f:
            await f.write(transcript)
        
        return interview_file
    
    def _prd_to_markdown(self, prd_data: dict) -> str:
        """Convert PRD JSON to Markdown format.
        
        Args:
            prd_data: PRD data dictionary
            
        Returns:
            Markdown formatted string
        """
        md = f"""# Product Requirements Document

## Project: {prd_data.get('project_name', 'Untitled Project')}

**Version:** {prd_data.get('version', '1.0')}  
**Last Updated:** {prd_data.get('updated_at', '')}  
**Author:** Business Analyst

---

## 1. Overview

{prd_data.get('overview', '_No overview provided._')}

---

## 2. Goals & Objectives

{self._list_to_md(prd_data.get('goals', []))}

---

## 3. Target Users

{self._list_to_md(prd_data.get('target_users', []))}

---

## 4. Features

{self._features_to_md(prd_data.get('features', []))}

---

## 5. User Stories Summary

{self._stories_summary_to_md(prd_data.get('user_stories', []))}

---

## 6. Acceptance Criteria

{self._list_to_md(prd_data.get('acceptance_criteria', []))}

---

## 7. Technical Constraints

{self._list_to_md(prd_data.get('constraints', []))}

---

## 8. Success Metrics

{self._list_to_md(prd_data.get('success_metrics', []))}

---

## 9. Next Steps

{self._list_to_md(prd_data.get('next_steps', []))}

---

*This document was generated by the Business Analyst agent.*
"""
        return md
    
    def _stories_to_markdown(self, stories_data: list[dict]) -> str:
        """Convert all user stories to markdown format.
        
        Args:
            stories_data: List of story data dictionaries
            
        Returns:
            Markdown formatted string with all stories
        """
        if not stories_data:
            return """# User Stories

*No user stories yet. Stories will appear here as they are created.*
"""
        
        md = f"""# User Stories

**Total Stories:** {len(stories_data)}  
**Last Updated:** {stories_data[0].get('updated_at', 'N/A') if stories_data else 'N/A'}

---

"""
        
        for i, story in enumerate(stories_data, 1):
            md += f"""## {i}. {story.get('title', 'Untitled Story')}

**ID:** `{story.get('id', 'N/A')}`  
**Status:** {story.get('status', 'TODO')}  
**Priority:** {story.get('priority', 'Medium')}  
**Story Points:** {story.get('story_points', 'TBD')}

### User Story

{story.get('description', '_No description provided._')}

### Acceptance Criteria

{story.get('acceptance_criteria', '_No acceptance criteria defined._')}

### Tags

{', '.join(story.get('tags', []) or ['_No tags_'])}

### Notes

{story.get('notes', '_No additional notes._')}

---

"""
        
        md += "\n*Generated by Business Analyst agent*\n"
        return md
    
    def _list_to_md(self, items: list) -> str:
        """Convert list to markdown bullet points."""
        if not items:
            return "_None specified._"
        return "\n".join(f"- {item}" for item in items)
    
    def _features_to_md(self, features: list) -> str:
        """Convert features list to markdown sections."""
        if not features:
            return "_No features defined._"
        
        md = ""
        for i, feature in enumerate(features, 1):
            name = feature.get('name', 'Unnamed Feature') if isinstance(feature, dict) else str(feature)
            desc = feature.get('description', '') if isinstance(feature, dict) else ''
            
            md += f"### {i}. {name}\n\n"
            if desc:
                md += f"{desc}\n\n"
        
        return md
    
    def _stories_summary_to_md(self, stories: list) -> str:
        """Convert stories list to markdown table."""
        if not stories:
            return "_No user stories yet. Will be extracted after PRD approval._"
        
        md = "| ID | Title | Priority | Status |\n"
        md += "|---|---|---|---|\n"
        
        for story in stories:
            if isinstance(story, dict):
                story_id = story.get('id', 'N/A')
                title = story.get('title', 'Untitled')
                priority = story.get('priority', 'Medium')
                status = story.get('status', 'TODO')
                md += f"| {story_id} | {title} | {priority} | {status} |\n"
        
        return md

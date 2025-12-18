"""Project Files Manager - Inspired by MetaGPT's file-based approach.
"""

from pathlib import Path
from typing import Optional
import aiofiles
import shutil
from datetime import datetime, timezone


class ProjectFiles:
    """Manage project files (PRD, stories)"""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.docs_path = self.project_path / "docs"
        self.prd_path = self.docs_path / "prd.md"
        self.user_stories_path = self.docs_path / "user-stories.md"
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.docs_path.mkdir(parents=True, exist_ok=True)
    
    async def archive_docs(self) -> bool:
        """Move existing docs to archive folder."""
        # Check if there are any files to archive
        files_to_archive = []
        if self.prd_path.exists():
            files_to_archive.append(self.prd_path)
        if self.user_stories_path.exists():
            files_to_archive.append(self.user_stories_path)
        
        if not files_to_archive:
            return True  # Nothing to archive
        
        # Create timestamped folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_folder = self.docs_path / "archive" / timestamp
        archive_folder.mkdir(parents=True, exist_ok=True)
        
        archived_files = []
        
        # Move prd.md
        if self.prd_path.exists():
            dest = archive_folder / "prd.md"
            shutil.move(str(self.prd_path), str(dest))
            archived_files.append("prd.md")
        
        # Move user-stories.md
        if self.user_stories_path.exists():
            dest = archive_folder / "user-stories.md"
            shutil.move(str(self.user_stories_path), str(dest))
            archived_files.append("user-stories.md")
        
        if archived_files:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[ProjectFiles] Archived to archive/{timestamp}/: {', '.join(archived_files)}")
        
        return True
    
    async def save_prd(self, prd_data: dict) -> Path:
        """Save PRD to Markdown file (for human reading).
        
        Note: PRD data is stored in Artifact table for programmatic access.
        
        Args:
            prd_data: Dictionary containing PRD content
            
        Returns:
            Path to the saved markdown file
        """
        # Add metadata
        prd_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Save Markdown only (data is in Artifact table)
        md_content = self._prd_to_markdown(prd_data)
        async with aiofiles.open(self.prd_path, 'w', encoding='utf-8') as f:
            await f.write(md_content)
        
        return self.prd_path
    
    async def save_user_stories(self, epics_data: list[dict] = None, stories_data: list[dict] = None) -> Path:
        """Save epics and user stories to a single markdown file.
        
        Args:
            epics_data: List of epic dictionaries (each containing stories)
            stories_data: Flat list of story dictionaries (for backward compatibility)
            
        Returns:
            Path to the saved user stories file
        """
        # Handle backward compatibility
        if epics_data is None:
            epics_data = []
        if stories_data is None:
            stories_data = []
            
        md_content = self._epics_to_markdown(epics_data, stories_data)
        
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

## 2. Objectives

{self._list_to_md(prd_data.get('objectives', []))}

---

## 3. Target Users

{self._list_to_md(prd_data.get('target_users', []))}

---

## 4. Features

{self._features_to_md(prd_data.get('features', []))}

---

## 5. Technical Constraints

{self._list_to_md(prd_data.get('constraints', []))}

---

## 6. Success Metrics

{self._list_to_md(prd_data.get('success_metrics', []))}

---

## 7. Risks

{self._list_to_md(prd_data.get('risks', []))}
"""
        return md
    
    def _epics_to_markdown(self, epics_data: list[dict], stories_data: list[dict] = None) -> str:
        """Convert epics and user stories to markdown format.
        
        Args:
            epics_data: List of epic data dictionaries (each containing stories)
            stories_data: Flat list for backward compatibility
            
        Returns:
            Markdown formatted string with all epics and stories
        """
        if not epics_data and not stories_data:
            return """# Epics & User Stories

*No epics or user stories yet. They will appear here after PRD approval.*
"""
        
        # Calculate totals
        total_epics = len(epics_data)
        total_stories = sum(len(epic.get('stories', [])) for epic in epics_data)
        
        md = f"""# Epics & User Stories

**Total Epics:** {total_epics}  
**Total Stories:** {total_stories}  
**Last Updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

---

"""
        
        for epic_idx, epic in enumerate(epics_data, 1):
            epic_id = epic.get('id', f'EPIC-{epic_idx:03d}')
            epic_title = epic.get('title', epic.get('name', 'Untitled Epic'))
            epic_desc = epic.get('description', '')
            epic_domain = epic.get('domain', 'General')
            stories = epic.get('stories', [])
            
            md += f"""# Epic: {epic_title}

**ID:** `{epic_id}`  
**Domain:** {epic_domain}  
**Stories:** {len(stories)}

{epic_desc}

---

"""
            
            for story_idx, story in enumerate(stories, 1):
                story_id = story.get('id', f'US-{epic_idx:02d}{story_idx:02d}')
                story_title = story.get('title', 'Untitled Story')
                story_desc = story.get('description', '')
                
                md += f"""## {story_title}

**ID:** `{story_id}`  
**Epic:** `{epic_id}`

### Description
{story_desc}

### Requirements
"""
                
                # Format requirements (for developers)
                req_list = story.get('requirements', [])
                if isinstance(req_list, list) and req_list:
                    for req in req_list:
                        md += f"- {req}\n"
                else:
                    md += "_No requirements defined._\n"
                
                md += "\n### Acceptance Criteria\n"
                
                # Format acceptance criteria (for QA)
                ac_list = story.get('acceptance_criteria', [])
                if isinstance(ac_list, list) and ac_list:
                    for ac in ac_list:
                        md += f"- {ac}\n"
                else:
                    md += "_No acceptance criteria defined._\n"
                
                # Format dependencies
                deps = story.get('dependencies', [])
                if isinstance(deps, list) and deps:
                    md += "\n### Dependencies\n"
                    md += "Stories that must be completed first:\n"
                    for dep in deps:
                        md += f"- `{dep}`\n"
                
                md += "\n---\n\n"

        return md
    
    def _stories_to_markdown(self, stories_data: list[dict]) -> str:
        """Convert flat list of user stories to markdown format (legacy support).
        
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
            if isinstance(feature, dict):
                name = feature.get('name', 'Unnamed Feature')
                desc = feature.get('description', '')
                priority = feature.get('priority', 'medium')
                requirements = feature.get('requirements', [])
                
                priority_label = "🔴 High" if priority == "high" else "🟡 Medium" if priority == "medium" else "🟢 Low"
                
                md += f"### {i}. {name}\n\n"
                md += f"**Priority:** {priority_label}\n\n"
                if desc:
                    md += f"{desc}\n\n"
                if requirements:
                    md += "**Requirements:**\n"
                    for req in requirements:
                        md += f"- {req}\n"
                    md += "\n"
            else:
                md += f"### {i}. {feature}\n\n"
        
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

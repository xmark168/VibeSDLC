"""
Incremental Code Modification System

Implements structured incremental modifications using OLD_CODE/NEW_CODE pairs
with uniqueness validation and surgical precision.
"""

import re

from pydantic import BaseModel, Field, validator


class CodeModification(BaseModel):
    """Represents a single incremental code modification."""

    file_path: str
    old_code: str
    new_code: str
    description: str
    line_start: int | None = None
    line_end: int | None = None

    @validator("old_code")
    def validate_old_code(cls, v):
        """Validate old_code is not empty and has meaningful content."""
        if not v or not v.strip():
            raise ValueError("old_code cannot be empty")
        return v

    @validator("new_code")
    def validate_new_code(cls, v):
        """Validate new_code (can be empty for deletions)."""
        return v

    @validator("description")
    def validate_description(cls, v):
        """Validate description is meaningful."""
        if not v or len(v.strip()) < 5:
            raise ValueError("description must be at least 5 characters")
        return v


class IncrementalModificationResult(BaseModel):
    """Result of applying incremental modifications."""

    success: bool
    modifications_applied: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    final_content: str = ""


class IncrementalModificationValidator:
    """Validates and applies incremental code modifications."""

    def __init__(self, file_content: str):
        """Initialize with file content."""
        self.original_content = file_content
        self.lines = file_content.splitlines()

    def validate_modification(self, modification: CodeModification) -> tuple[bool, str]:
        """
        Validate a single modification for uniqueness and correctness.

        Returns:
            (is_valid, error_message)
        """
        old_code = modification.old_code.strip()

        # Check if old_code exists in file
        if old_code not in self.original_content:
            return False, f"OLD_CODE not found in file: {old_code[:50]}..."

        # Check uniqueness - old_code should appear exactly once
        count = self.original_content.count(old_code)
        if count == 0:
            return False, f"OLD_CODE not found: {old_code[:50]}..."
        elif count > 1:
            return (
                False,
                f"OLD_CODE appears {count} times, need more context: {old_code[:50]}...",
            )

        # Check if old_code spans multiple lines correctly
        if "\n" in old_code:
            # Verify line boundaries are correct
            old_lines = old_code.split("\n")
            found_start = -1

            for i in range(len(self.lines) - len(old_lines) + 1):
                match = True
                for j, old_line in enumerate(old_lines):
                    if i + j >= len(self.lines) or self.lines[i + j] != old_line:
                        match = False
                        break
                if match:
                    found_start = i
                    break

            if found_start == -1:
                return False, "OLD_CODE line boundaries don't match file structure"

        return True, ""

    def apply_modification(
        self, modification: CodeModification
    ) -> tuple[bool, str, str]:
        """
        Apply a single modification to the content.

        Returns:
            (success, new_content, error_message)
        """
        # Validate first
        is_valid, error = self.validate_modification(modification)
        if not is_valid:
            return False, self.original_content, error

        # Apply the modification
        try:
            new_content = self.original_content.replace(
                modification.old_code,
                modification.new_code,
                1,  # Replace only first occurrence
            )
            return True, new_content, ""
        except Exception as e:
            return (
                False,
                self.original_content,
                f"Error applying modification: {str(e)}",
            )

    def apply_multiple_modifications(
        self, modifications: list[CodeModification]
    ) -> IncrementalModificationResult:
        """
        Apply multiple modifications in sequence.

        Args:
            modifications: List of modifications to apply

        Returns:
            IncrementalModificationResult with success status and details
        """
        result = IncrementalModificationResult(
            success=True, modifications_applied=0, final_content=self.original_content
        )

        current_content = self.original_content

        for i, modification in enumerate(modifications):
            # Update validator with current content
            validator = IncrementalModificationValidator(current_content)

            # Apply modification
            success, new_content, error = validator.apply_modification(modification)

            if success:
                current_content = new_content
                result.modifications_applied += 1
                result.warnings.append(f"✅ Applied: {modification.description}")
            else:
                result.errors.append(f"❌ Failed modification {i + 1}: {error}")
                result.success = False
                # Continue with other modifications

        result.final_content = current_content
        return result


def parse_structured_modifications(llm_output: str) -> list[CodeModification]:
    """
    Parse LLM output into structured CodeModification objects.

    Expected format:
    MODIFICATION #1:
    FILE: path/to/file.py
    DESCRIPTION: Brief explanation

    OLD_CODE:
    ```python
    old code here
    ```

    NEW_CODE:
    ```python
    new code here
    ```

    Args:
        llm_output: Raw LLM output string

    Returns:
        List of CodeModification objects
    """
    modifications = []

    # Split by MODIFICATION markers
    modification_blocks = re.split(r"MODIFICATION #\d+:", llm_output)

    for block in modification_blocks[1:]:  # Skip first empty block
        try:
            # Extract file path
            file_match = re.search(r"FILE:\s*(.+)", block)
            if not file_match:
                continue
            file_path = file_match.group(1).strip()

            # Extract description
            desc_match = re.search(r"DESCRIPTION:\s*(.+)", block)
            if not desc_match:
                continue
            description = desc_match.group(1).strip()

            # Extract OLD_CODE
            old_code_match = re.search(
                r"OLD_CODE:\s*```\w*\n(.*?)\n```", block, re.DOTALL
            )
            if not old_code_match:
                continue
            old_code = old_code_match.group(1)

            # Extract NEW_CODE
            new_code_match = re.search(
                r"NEW_CODE:\s*```\w*\n(.*?)\n```", block, re.DOTALL
            )
            if not new_code_match:
                continue
            new_code = new_code_match.group(1)

            # Create modification
            modification = CodeModification(
                file_path=file_path,
                old_code=old_code,
                new_code=new_code,
                description=description,
            )
            modifications.append(modification)

        except Exception:
            # Skip malformed blocks
            continue

    return modifications


def validate_modifications_batch(
    file_content: str, modifications: list[CodeModification]
) -> tuple[bool, list[str]]:
    """
    Validate a batch of modifications for conflicts and correctness.

    Args:
        file_content: Original file content
        modifications: List of modifications to validate

    Returns:
        (all_valid, error_messages)
    """
    errors = []
    validator = IncrementalModificationValidator(file_content)

    # Check each modification individually
    for i, mod in enumerate(modifications):
        is_valid, error = validator.validate_modification(mod)
        if not is_valid:
            errors.append(f"Modification {i + 1}: {error}")

    # Check for overlapping modifications
    old_codes = [mod.old_code for mod in modifications]
    for i, old_code_1 in enumerate(old_codes):
        for j, old_code_2 in enumerate(old_codes[i + 1 :], i + 1):
            if old_code_1 in old_code_2 or old_code_2 in old_code_1:
                errors.append(f"Modifications {i + 1} and {j + 1} overlap")

    return len(errors) == 0, errors

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

        # Debug logging for troubleshooting
        print(f"DEBUG: Validating modification for file: {modification.file_path}")
        print(f"DEBUG: OLD_CODE raw: {repr(old_code[:200])}...")
        print(f"DEBUG: File content length: {len(self.original_content)}")
        print(f"DEBUG: File content hash: {hash(self.original_content)}")

        # Check if old_code exists in file
        if old_code not in self.original_content:
            # Enhanced error message with file content preview
            file_preview = self._get_file_content_preview()
            return False, (
                f"❌ OLD_CODE not found in target file:\n"
                f"🔍 Looking for: {repr(old_code[:100])}...\n"
                f"📄 File content preview:\n{file_preview}\n"
                f"💡 Hint: Check if you're modifying the correct file or if the code has changed"
            )

        # Check uniqueness - old_code should appear exactly once
        count = self.original_content.count(old_code)
        if count == 0:
            return False, f"OLD_CODE not found: {old_code[:50]}..."
        elif count > 1:
            # Enhanced error with line numbers where duplicates appear
            duplicate_locations = self._find_code_locations(old_code)
            return (
                False,
                f"❌ OLD_CODE appears {count} times, need more context:\n"
                f"🔍 Code: {repr(old_code[:50])}...\n"
                f"📍 Found at lines: {duplicate_locations}\n"
                f"💡 Hint: Add more surrounding context to make OLD_CODE unique",
            )

        # Check if old_code spans multiple lines correctly
        if "\n" in old_code:
            # Verify line boundaries are correct
            old_lines = old_code.split("\n")
            found_start = -1

            # First try exact match
            for i in range(len(self.lines) - len(old_lines) + 1):
                match = True
                for j, old_line in enumerate(old_lines):
                    if i + j >= len(self.lines) or self.lines[i + j] != old_line:
                        match = False
                        break
                if match:
                    found_start = i
                    break

            # If exact match fails, try fuzzy match for minor indentation differences
            if found_start == -1:
                found_start = self._try_fuzzy_line_match(old_lines)

            if found_start == -1:
                # Enhanced error with detailed line boundary analysis and OLD_CODE debug info
                line_analysis = self._analyze_line_boundaries(old_lines)
                old_code_debug = self._debug_old_code_content(old_code)
                return False, (
                    f"❌ OLD_CODE line boundaries don't match file structure:\n"
                    f"🔍 Expected lines: {len(old_lines)}\n"
                    f"📄 Line analysis:\n{line_analysis}\n"
                    f"🐛 OLD_CODE debug info:\n{old_code_debug}\n"
                    f"💡 Hint: Check for whitespace differences, indentation, or line ending issues"
                )

        return True, ""

    def _get_file_content_preview(self, max_lines: int = 10) -> str:
        """Get a preview of file content for error messages."""
        if len(self.lines) <= max_lines:
            # Show entire file if it's small
            preview_lines = [f"{i + 1:3}: {line}" for i, line in enumerate(self.lines)]
        else:
            # Show first few lines and last few lines
            first_lines = [
                f"{i + 1:3}: {line}"
                for i, line in enumerate(self.lines[: max_lines // 2])
            ]
            last_lines = [
                f"{i + 1:3}: {line}"
                for i, line in enumerate(
                    self.lines[-max_lines // 2 :], len(self.lines) - max_lines // 2
                )
            ]
            preview_lines = first_lines + ["..."] + last_lines

        return "\n".join(preview_lines)

    def _find_code_locations(self, code: str) -> list[int]:
        """Find line numbers where code appears in the file."""
        locations = []
        lines_to_search = code.split("\n")

        for i in range(len(self.lines) - len(lines_to_search) + 1):
            match = True
            for j, search_line in enumerate(lines_to_search):
                if (
                    i + j >= len(self.lines)
                    or search_line.strip() not in self.lines[i + j]
                ):
                    match = False
                    break
            if match:
                locations.append(i + 1)  # 1-based line numbers

        return locations

    def _try_fuzzy_line_match(self, old_lines: list[str]) -> int:
        """
        Try fuzzy matching for line boundaries with minor indentation differences.

        Returns:
            Starting line index if found, -1 if not found
        """
        for i in range(len(self.lines) - len(old_lines) + 1):
            match = True

            for j, old_line in enumerate(old_lines):
                file_line_idx = i + j
                if file_line_idx >= len(self.lines):
                    match = False
                    break

                file_line = self.lines[file_line_idx]

                # Try exact match first
                if file_line == old_line:
                    continue

                # Try content match (ignoring leading/trailing whitespace)
                if file_line.strip() == old_line.strip():
                    # Check if it's just a leading whitespace difference
                    file_content = file_line.strip()
                    old_content = old_line.strip()

                    if (
                        file_content == old_content and file_content
                    ):  # Non-empty content match
                        continue

                # Try empty line match
                if not file_line.strip() and not old_line.strip():
                    continue

                # No match found for this line
                match = False
                break

            if match:
                return i

        return -1

    def _debug_old_code_content(self, old_code: str) -> str:
        """Generate debug information about OLD_CODE content."""
        debug_info = []
        debug_info.append(f"Raw OLD_CODE: {repr(old_code)}")
        debug_info.append(f"Length: {len(old_code)} characters")

        # Check for special characters
        has_crlf = "\r\n" in old_code
        has_lf = "\n" in old_code
        has_tab = "\t" in old_code

        debug_info.append(f"Line endings: CRLF={has_crlf}, LF={has_lf}")
        debug_info.append(f"Contains tabs: {has_tab}")

        # Show first and last 50 chars
        if len(old_code) > 100:
            debug_info.append(f"First 50 chars: {repr(old_code[:50])}")
            debug_info.append(f"Last 50 chars: {repr(old_code[-50:])}")

        return "\n".join(debug_info)

    def _analyze_line_boundaries(self, expected_lines: list[str]) -> str:
        """Analyze why line boundaries don't match."""
        analysis = []
        analysis.append(f"Expected {len(expected_lines)} lines:")

        for i, expected_line in enumerate(expected_lines):
            analysis.append(f"  Line {i + 1}: {repr(expected_line)}")

        analysis.append("\nActual file lines (first 10):")
        for i, actual_line in enumerate(self.lines[:10]):
            analysis.append(f"  Line {i + 1}: {repr(actual_line)}")

        # Try to find partial matches
        analysis.append("\nPartial match analysis:")
        for i, expected_line in enumerate(expected_lines):
            found_similar = []
            for j, actual_line in enumerate(self.lines):
                if (
                    expected_line.strip() in actual_line
                    or actual_line.strip() in expected_line
                ):
                    found_similar.append(f"Line {j + 1}")

            if found_similar:
                analysis.append(
                    f"  Expected line {i + 1} similar to: {', '.join(found_similar)}"
                )
            else:
                analysis.append(f"  Expected line {i + 1}: No similar lines found")

        return "\n".join(analysis)

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
            # ✅ Check for potential duplicates BEFORE applying
            duplicate_check = self._check_for_duplicates(
                current_content, modification.new_code
            )
            if not duplicate_check["safe"]:
                result.errors.append(
                    f"⚠️ Modification {i + 1} may create duplicate: {duplicate_check['reason']}"
                )
                result.warnings.append(
                    "💡 Hint: Check if functionality already exists in file"
                )
                result.success = False
                continue  # Skip this modification

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

    def _check_for_duplicates(self, current_content: str, new_code: str) -> dict:
        """
        Check if NEW_CODE would create duplicate routes, functions, or exports.

        Args:
            current_content: Current file content
            new_code: New code to be added

        Returns:
            Dict with 'safe' (bool) and 'reason' (str)
        """
        import re

        # Pattern for route definitions: router.post('/path'), app.get('/path'), etc.
        route_patterns = [
            r"router\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]",
            r"app\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]",
            r"@(Get|Post|Put|Delete|Patch)\(['\"]([^'\"]+)['\"]",  # NestJS decorators
        ]

        for pattern in route_patterns:
            # Find routes in new code
            new_routes = re.findall(pattern, new_code)
            # Find routes in current content
            existing_routes = re.findall(pattern, current_content)

            for route_info in new_routes:
                # Extract method and path (handle different capture group structures)
                if len(route_info) >= 2:
                    method = route_info[0].upper()
                    path = route_info[1]

                    # Check if this route already exists
                    for existing_route in existing_routes:
                        existing_method = existing_route[0].upper()
                        existing_path = existing_route[1]

                        if method == existing_method and path == existing_path:
                            return {
                                "safe": False,
                                "reason": f"Route {method} {path} already exists in file",
                            }

        # Pattern for function definitions: def function_name(), function function_name()
        function_patterns = [
            r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",  # Python
            r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",  # JavaScript
            r"const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>",  # Arrow functions
            r"export\s+(?:async\s+)?function\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # Exports
        ]

        for pattern in function_patterns:
            new_functions = re.findall(pattern, new_code)
            existing_functions = re.findall(pattern, current_content)

            for func_name in new_functions:
                if func_name in existing_functions:
                    return {
                        "safe": False,
                        "reason": f"Function '{func_name}' already exists in file",
                    }

        # All checks passed
        return {"safe": True, "reason": "No duplicates detected"}


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

    # Debug logging
    print(
        f"DEBUG: validate_modifications_batch called with {len(modifications)} modifications"
    )
    print(f"DEBUG: File content length: {len(file_content)} chars")
    print(f"DEBUG: File content preview: {repr(file_content[:100])}...")

    # Check each modification individually
    for i, mod in enumerate(modifications):
        print(f"DEBUG: Validating modification {i + 1}")
        print(f"DEBUG: OLD_CODE length: {len(mod.old_code)} chars")
        print(f"DEBUG: OLD_CODE preview: {repr(mod.old_code[:100])}...")

        is_valid, error = validator.validate_modification(mod)
        if not is_valid:
            print(f"DEBUG: Modification {i + 1} failed: {error}")
            errors.append(f"Modification {i + 1}: {error}")
        else:
            print(f"DEBUG: Modification {i + 1} passed")

    # Check for overlapping modifications with improved logic
    old_codes = [mod.old_code for mod in modifications]
    for i, old_code_1 in enumerate(old_codes):
        for j, old_code_2 in enumerate(old_codes[i + 1 :], i + 1):
            # Check for actual overlapping ranges in file content, not just substring containment
            overlap_detected = _check_modification_overlap(
                file_content, old_code_1, old_code_2
            )
            if overlap_detected:
                errors.append(
                    f"Modifications {i + 1} and {j + 1} overlap in file content"
                )

    return len(errors) == 0, errors


def _check_modification_overlap(
    file_content: str, old_code_1: str, old_code_2: str
) -> bool:
    """
    Check if two OLD_CODE patterns actually overlap in the file content.

    This is more sophisticated than simple substring checking - it looks at
    actual positions in the file to determine if modifications would conflict.

    Args:
        file_content: The original file content
        old_code_1: First OLD_CODE pattern
        old_code_2: Second OLD_CODE pattern

    Returns:
        True if modifications would overlap, False otherwise
    """
    # Find all positions where each OLD_CODE appears
    positions_1 = _find_all_positions(file_content, old_code_1)
    positions_2 = _find_all_positions(file_content, old_code_2)

    # If either pattern doesn't exist, no overlap possible
    if not positions_1 or not positions_2:
        return False

    # Check if any ranges overlap
    for start_1, end_1 in positions_1:
        for start_2, end_2 in positions_2:
            # Check for range overlap: ranges overlap if one starts before the other ends
            if start_1 < end_2 and start_2 < end_1:
                return True

    return False


def _find_all_positions(content: str, pattern: str) -> list[tuple[int, int]]:
    """
    Find all positions where a pattern appears in content.

    Returns:
        List of (start_pos, end_pos) tuples
    """
    positions = []
    start = 0

    while True:
        pos = content.find(pattern, start)
        if pos == -1:
            break
        positions.append((pos, pos + len(pattern)))
        start = pos + 1

    return positions

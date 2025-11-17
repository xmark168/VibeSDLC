"""ActionNode for structured output with validation and review.

This module provides ActionNode pattern from MetaGPT, enabling:
- Structured output with Pydantic validation
- Automatic retry on validation failures
- Built-in review and quality scoring
- Output schema enforcement
"""

import json
import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.base.action import Action

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ActionOutput(BaseModel):
    """Standard output format for ActionNode.

    Wraps the actual output with metadata about validation and review.
    """

    content: str
    instruct_content: Optional[Dict[str, Any]] = None  # Structured output
    is_valid: bool = True
    validation_errors: List[str] = []
    review_score: Optional[float] = None
    review_feedback: Optional[str] = None


class ActionNode(Generic[T]):
    """Node for executing actions with structured output validation.

    Inspired by MetaGPT's ActionNode, this provides:
    - Schema-based output validation
    - Automatic retry on failures
    - Built-in review mechanisms
    - Quality scoring

    Example:
        ```python
        from pydantic import BaseModel

        class StoryOutput(BaseModel):
            title: str
            description: str
            acceptance_criteria: str

        node = ActionNode(
            key="create_story",
            expected_type=StoryOutput,
            instruction="Create a user story",
            example={"title": "...", "description": "...", "acceptance_criteria": "..."}
        )

        result = await node.execute(context={"requirement": "..."})
        if result.is_valid:
            story_data = result.instruct_content
        ```
    """

    def __init__(
        self,
        key: str,
        expected_type: Type[T],
        instruction: str,
        example: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        enable_review: bool = False,
        review_threshold: float = 0.7,
    ):
        """Initialize ActionNode.

        Args:
            key: Unique identifier for this node
            expected_type: Pydantic model class for output validation
            instruction: Instruction for LLM on what to generate
            example: Example output to guide LLM
            max_retries: Maximum retry attempts on validation failure
            enable_review: Whether to enable quality review
            review_threshold: Minimum score to pass review (0.0-1.0)
        """
        self.key = key
        self.expected_type = expected_type
        self.instruction = instruction
        self.example = example
        self.max_retries = max_retries
        self.enable_review = enable_review
        self.review_threshold = review_threshold

    def _build_prompt(
        self,
        context: Dict[str, Any],
        retry_count: int = 0,
        validation_errors: Optional[List[str]] = None,
    ) -> str:
        """Build prompt for LLM.

        Args:
            context: Context data for generation
            retry_count: Current retry attempt number
            validation_errors: Validation errors from previous attempt

        Returns:
            Formatted prompt string
        """
        # Get schema from Pydantic model
        schema = self.expected_type.model_json_schema()

        prompt_parts = [
            f"Task: {self.instruction}",
            "",
            "Context:",
        ]

        # Add context
        for k, v in context.items():
            prompt_parts.append(f"  {k}: {v}")

        prompt_parts.extend([
            "",
            "Output Requirements:",
            f"  Return a JSON object matching this schema:",
            f"  {json.dumps(schema, indent=2)}",
        ])

        # Add example if provided
        if self.example:
            prompt_parts.extend([
                "",
                "Example Output:",
                f"  {json.dumps(self.example, indent=2)}",
            ])

        # Add retry guidance if this is a retry
        if retry_count > 0 and validation_errors:
            prompt_parts.extend([
                "",
                f"⚠️ RETRY #{retry_count}",
                "Previous attempt had validation errors:",
            ])
            for error in validation_errors:
                prompt_parts.append(f"  - {error}")
            prompt_parts.append("Please fix these issues and try again.")

        prompt_parts.extend([
            "",
            "Return ONLY the JSON object, no other text.",
        ])

        return "\n".join(prompt_parts)

    def _validate_output(self, output_str: str) -> tuple[bool, Optional[T], List[str]]:
        """Validate output against expected schema.

        Args:
            output_str: Raw output string from LLM

        Returns:
            Tuple of (is_valid, parsed_object, errors)
        """
        errors = []

        try:
            # Extract JSON from output
            json_data = self._extract_json(output_str)

            if not json_data:
                errors.append("No valid JSON found in output")
                return (False, None, errors)

            # Validate against Pydantic model
            validated_obj = self.expected_type.model_validate(json_data)
            return (True, validated_obj, [])

        except ValidationError as e:
            errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            return (False, None, errors)

        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            return (False, None, errors)

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON object from text.

        Args:
            text: Text containing JSON

        Returns:
            Parsed JSON dict or None
        """
        import re

        # Try to find JSON object
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try parsing entire text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        return None

    async def _review_output(
        self,
        output: T,
        review_action: Action,
    ) -> tuple[float, str]:
        """Review output quality using LLM.

        Args:
            output: Validated output object
            review_action: Action to perform review

        Returns:
            Tuple of (score, feedback)
        """
        review_prompt = f"""
Review the following output for quality and completeness:

Instruction: {self.instruction}

Output:
{output.model_dump_json(indent=2)}

Rate the output on a scale of 0.0 to 1.0 based on:
- Completeness (all required fields filled)
- Quality (appropriate level of detail)
- Correctness (makes sense for the instruction)

Respond in this format:
Score: <0.0-1.0>
Feedback: <brief feedback>
"""

        try:
            result = await review_action.run(review_prompt)
            result_text = str(result)

            # Parse score
            score_match = re.search(r'Score:\s*([\d.]+)', result_text)
            score = float(score_match.group(1)) if score_match else 0.5

            # Parse feedback
            feedback_match = re.search(r'Feedback:\s*(.+)', result_text, re.DOTALL)
            feedback = feedback_match.group(1).strip() if feedback_match else "No feedback"

            return (score, feedback)

        except Exception as e:
            logger.error(f"Review failed: {e}")
            return (0.5, f"Review error: {str(e)}")

    async def execute(
        self,
        llm_action: Action,
        context: Dict[str, Any],
        review_action: Optional[Action] = None,
    ) -> ActionOutput:
        """Execute the action node with retries and validation.

        Args:
            llm_action: Action to generate output
            context: Context for generation
            review_action: Optional action for review

        Returns:
            ActionOutput with validation results
        """
        last_errors = []

        for retry in range(self.max_retries):
            try:
                # Build prompt
                prompt = self._build_prompt(
                    context=context,
                    retry_count=retry,
                    validation_errors=last_errors if retry > 0 else None,
                )

                # Get LLM output
                result = await llm_action.run(prompt)
                output_str = str(result)

                # Validate output
                is_valid, validated_obj, errors = self._validate_output(output_str)

                if is_valid and validated_obj:
                    # Success! Optionally review
                    review_score = None
                    review_feedback = None

                    if self.enable_review and review_action:
                        review_score, review_feedback = await self._review_output(
                            validated_obj, review_action
                        )

                        # Check if review passes threshold
                        if review_score < self.review_threshold:
                            logger.warning(
                                f"Output review score {review_score} below threshold "
                                f"{self.review_threshold}"
                            )
                            # Could trigger retry here if desired
                            # For now, we still return the result

                    return ActionOutput(
                        content=output_str,
                        instruct_content=validated_obj.model_dump(),
                        is_valid=True,
                        validation_errors=[],
                        review_score=review_score,
                        review_feedback=review_feedback,
                    )

                else:
                    # Validation failed
                    last_errors = errors
                    logger.warning(
                        f"Validation failed on attempt {retry + 1}/{self.max_retries}: "
                        f"{errors}"
                    )

            except Exception as e:
                logger.error(f"Execution error on attempt {retry + 1}: {e}")
                last_errors = [f"Execution error: {str(e)}"]

        # All retries exhausted
        return ActionOutput(
            content="",
            instruct_content=None,
            is_valid=False,
            validation_errors=last_errors,
        )

    async def fill(
        self,
        llm_action: Action,
        context: Dict[str, Any],
        review_action: Optional[Action] = None,
        mode: str = "auto",
    ) -> Dict[str, Any]:
        """Fill the action node (shorthand for execute).

        Args:
            llm_action: Action to generate output
            context: Context for generation
            review_action: Optional review action
            mode: Execution mode (auto, single, etc.)

        Returns:
            Output dictionary or empty dict on failure
        """
        result = await self.execute(llm_action, context, review_action)

        if result.is_valid and result.instruct_content:
            return result.instruct_content
        else:
            logger.error(f"ActionNode fill failed: {result.validation_errors}")
            return {}


# Utility function for creating simple action nodes
def create_action_node(
    key: str,
    instruction: str,
    output_schema: Type[T],
    example: Optional[Dict[str, Any]] = None,
) -> ActionNode[T]:
    """Create an ActionNode with common defaults.

    Args:
        key: Node identifier
        instruction: What to generate
        output_schema: Pydantic model for validation
        example: Optional example output

    Returns:
        Configured ActionNode
    """
    return ActionNode(
        key=key,
        expected_type=output_schema,
        instruction=instruction,
        example=example,
        max_retries=3,
        enable_review=False,
    )

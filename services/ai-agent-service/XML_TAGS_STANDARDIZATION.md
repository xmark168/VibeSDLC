# XML Tags Standardization - Prompt Templates

## 📋 Overview

This document describes the standardization of XML-style tags across all prompt templates in `app/agents/developer/implementor/utils/prompts.py`.

**Purpose:** Use consistent XML-style tags to structure prompt content, making it easier for LLMs to parse and follow different sections of instructions.

**Benefits:**
- **Better LLM Comprehension:** XML tags provide clear boundaries for different instruction sections
- **Improved Maintainability:** Easier to identify and update specific sections
- **Consistent Structure:** All prompts follow the same organizational pattern
- **Enhanced Parsing:** LLMs can better distinguish between rules, examples, and output requirements

## 🏷️ Standard XML Tags

### Core Tags (Used Across All Prompts)

#### `<critical_rules>...</critical_rules>`
**Purpose:** Wrap the most important rules that MUST be followed

**Usage:**
- Language requirements (e.g., .js = JavaScript ONLY)
- Breaking change warnings
- Mandatory constraints

**Example:**
```xml
<critical_rules>
CRITICAL LANGUAGE REQUIREMENTS:
- For tech_stack "nodejs": Generate JavaScript/TypeScript code ONLY
- NEVER mix languages - use only the language that matches the tech stack
</critical_rules>
```

#### `<best_practices>...</best_practices>`
**Purpose:** Wrap coding best practices and guidelines

**Usage:**
- Framework-specific patterns
- Security best practices
- Performance optimization tips
- Testing patterns

**Example:**
```xml
<best_practices>
BACKEND BEST PRACTICES:

1. API DESIGN PATTERNS:
   - Follow REST conventions
   - Use appropriate HTTP status codes
   
2. DATABASE OPERATIONS:
   - Use ORM best practices
   - Implement proper migrations
</best_practices>
```

#### `<output_format>...</output_format>`
**Purpose:** Specify the exact format of the expected output

**Usage:**
- Code formatting requirements
- What to include/exclude
- File structure expectations

**Example:**
```xml
<output_format>
IMPORTANT OUTPUT FORMAT:
- Return ONLY the complete file content
- Do NOT include explanations or markdown formatting
- Do NOT wrap code in code blocks
- Start directly with the code
</output_format>
```

### Specialized Tags (Context-Specific)

#### `<api_contract>...</api_contract>`
**Purpose:** Wrap API contract consistency rules (Backend File Creation)

**Usage:**
- Dependency coordination rules
- Method naming consistency
- Return type consistency
- Validation requirements

**Example:**
```xml
<api_contract>
🔗 API CONTRACT CONSISTENCY (CRITICAL - HIGHEST PRIORITY):

1. DEPENDENCY COORDINATION:
   - Use EXACT method names from dependency classes
   - Match EXACT return types from dependency methods
</api_contract>
```

#### `<examples>...</examples>`
**Purpose:** Wrap few-shot examples showing correct vs incorrect usage

**Usage:**
- Concrete code examples
- Common mistakes to avoid
- Best practice demonstrations

**Example:**
```xml
<examples>
📚 EXAMPLE: Correct Dependency Usage

Given dependency file `authService.js`:
```javascript
class AuthService {
  async loginUser(email, password) { ... }
}
```

✅ CORRECT: const { user, token } = await authService.loginUser(email, password);
❌ WRONG: const user = await authService.validateUser({ email, password });
</examples>
```

#### `<verification_checklist>...</verification_checklist>`
**Purpose:** Provide a checklist for LLM to verify output (Modification Prompts)

**Usage:**
- Pre-submission checks
- Quality assurance steps
- Completeness verification

**Example:**
```xml
<verification_checklist>
Before submitting your output, verify:

✅ Does the output contain ALL existing imports?
✅ Does the output contain ALL existing functions?
✅ Is the code syntactically valid?
</verification_checklist>
```

#### `<backend_specific_guidelines>...</backend_specific_guidelines>`
**Purpose:** Backend-specific modification guidelines

**Usage:**
- API consistency rules
- Database safety requirements
- Framework patterns

#### `<frontend_specific_guidelines>...</frontend_specific_guidelines>`
**Purpose:** Frontend-specific modification guidelines

**Usage:**
- Component interface preservation
- State management patterns
- UI/UX consistency

#### `<critical_requirements>...</critical_requirements>`
**Purpose:** Critical requirements for code modifications

**Usage:**
- Uniqueness requirements
- Exactness requirements
- Context requirements

## 📊 Standardization Summary

### Prompts Updated

| Prompt Template | Tags Added | Status |
|----------------|------------|--------|
| `BACKEND_FILE_CREATION_PROMPT` | `<critical_rules>`, `<api_contract>`, `<examples>`, `<best_practices>`, `<output_format>` | ✅ Complete |
| `FRONTEND_FILE_CREATION_PROMPT` | `<critical_rules>`, `<best_practices>`, `<output_format>` | ✅ Complete |
| `GENERIC_FILE_CREATION_PROMPT` | `<critical_rules>`, `<best_practices>`, `<output_format>` | ✅ Complete |
| `BACKEND_FILE_MODIFICATION_PROMPT` | Already had tags | ✅ Already Complete |
| `FRONTEND_FILE_MODIFICATION_PROMPT` | Already had tags | ✅ Already Complete |
| `GENERIC_FILE_MODIFICATION_PROMPT` | `<best_practices>`, `<output_format>`, `<critical_requirements>` | ✅ Complete |

### Tag Usage Statistics

```
<critical_rules>: 4 prompts
<api_contract>: 1 prompt (BACKEND_FILE_CREATION_PROMPT)
<examples>: 1 prompt (BACKEND_FILE_CREATION_PROMPT)
<best_practices>: 4 prompts
<output_format>: 6 prompts
<verification_checklist>: 1 prompt (BACKEND_FILE_MODIFICATION_PROMPT)
<backend_specific_guidelines>: 1 prompt
<frontend_specific_guidelines>: 1 prompt
<critical_requirements>: 2 prompts
```

## ✅ Verification

Run the test script to verify XML tags standardization:

```bash
cd services/ai-agent-service
python test_xml_tags_standardization.py
```

**Expected Output:**
```
✅ PASS: BACKEND_FILE_CREATION_PROMPT
✅ PASS: FRONTEND_FILE_CREATION_PROMPT
✅ PASS: GENERIC_FILE_CREATION_PROMPT
✅ PASS: BACKEND_FILE_MODIFICATION_PROMPT
✅ PASS: GENERIC_FILE_MODIFICATION_PROMPT
✅ PASS: XML Tag Consistency

Total: 6/6 tests passed

🎉 All tests passed! XML tags are properly standardized across all prompts.
```

## 🎯 Benefits Observed

### Before Standardization
```
CRITICAL LANGUAGE REQUIREMENTS:
- For tech_stack "nodejs": Generate JavaScript/TypeScript code ONLY

BACKEND BEST PRACTICES:
1. API DESIGN PATTERNS:
   - Follow REST conventions
```

**Issues:**
- No clear boundaries between sections
- LLM might miss critical rules
- Harder to parse programmatically

### After Standardization
```xml
<critical_rules>
CRITICAL LANGUAGE REQUIREMENTS:
- For tech_stack "nodejs": Generate JavaScript/TypeScript code ONLY
</critical_rules>

<best_practices>
BACKEND BEST PRACTICES:
1. API DESIGN PATTERNS:
   - Follow REST conventions
</best_practices>
```

**Benefits:**
- ✅ Clear section boundaries
- ✅ LLM can easily identify critical vs optional content
- ✅ Easier to extract and validate sections programmatically
- ✅ Consistent structure across all prompts

## 🔧 Maintenance Guidelines

### Adding New Tags

When adding new XML tags:

1. **Choose descriptive names:** Use snake_case (e.g., `critical_rules`, `api_contract`)
2. **Always close tags:** Every `<tag>` must have a matching `</tag>`
3. **Nest properly:** Don't overlap tags
4. **Update tests:** Add new tags to `test_xml_tags_standardization.py`

### Modifying Existing Sections

When modifying content within XML tags:

1. **Preserve tag structure:** Don't remove or rename tags without updating all prompts
2. **Maintain consistency:** If changing a tag in one prompt, consider updating others
3. **Test after changes:** Run `test_xml_tags_standardization.py` to verify tags are balanced

### Best Practices

- **Use tags for structure, not styling:** Tags should organize content, not format it
- **Keep tag names semantic:** Names should describe the content's purpose
- **Don't over-tag:** Only use tags for major sections, not every paragraph
- **Document new tags:** Update this file when introducing new tag types

## 📝 Related Files

- `app/agents/developer/implementor/utils/prompts.py` - Prompt templates with XML tags
- `test_xml_tags_standardization.py` - Verification tests
- `XML_TAGS_STANDARDIZATION.md` - This documentation
- `DEPENDENCY_CONTEXT_FIX.md` - Related improvement documentation

## 🚀 Future Improvements

Potential enhancements:

1. **Programmatic Tag Extraction:** Build utilities to extract specific sections by tag
2. **Dynamic Prompt Assembly:** Compose prompts by combining tagged sections
3. **Tag-Based Validation:** Validate LLM output against specific tag requirements
4. **Multi-Language Support:** Add language-specific tags for different tech stacks


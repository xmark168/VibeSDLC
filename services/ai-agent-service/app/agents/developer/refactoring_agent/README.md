# Refactoring Agent

## 📋 Tổng Quan

Refactoring Agent là sub-agent thứ 6 trong Developer Agent workflow, chịu trách nhiệm phân tích code để tìm code smells, technical debt, và đề xuất các refactoring opportunities nhằm cải thiện maintainability.

## 🎯 Trách Nhiệm Chính

1. **Detect Code Smells** - Phát hiện 12 loại code smells
2. **Identify Technical Debt** - Xác định technical debt và ước lượng effort
3. **Generate Refactoring Plans** - Tạo kế hoạch refactoring chi tiết
4. **Calculate Maintainability Index** - Tính toán MI theo công thức chuẩn
5. **Prioritize Improvements** - Ưu tiên các cải tiến (Quick Wins, Priority, Long-term)
6. **Quality Check** - Đảm bảo output đạt chất lượng

## 📊 12 Loại Code Smells

| # | Code Smell | Threshold | Refactoring Type |
|---|------------|-----------|------------------|
| 1 | **Long Method** | > 50 lines | Extract Method |
| 2 | **Large Class** | > 300 lines | Extract Class |
| 3 | **Duplicate Code** | >= 6 lines | Extract Method |
| 4 | **Long Parameter List** | > 5 params | Introduce Parameter Object |
| 5 | **Feature Envy** | - | Move Method |
| 6 | **Data Clumps** | - | Extract Class |
| 7 | **Primitive Obsession** | - | Introduce Value Object |
| 8 | **Switch Statements** | - | Replace with Polymorphism |
| 9 | **Lazy Class** | - | Inline Class |
| 10 | **Speculative Generality** | - | Remove Dead Code |
| 11 | **Dead Code** | - | Remove |
| 12 | **Excessive Comments** | - | Refactor Code |

## 🔄 Workflow (7 Bước)

```
1. Parse & Analyze Code Structure
   ├─ Parse AST
   ├─ Extract classes, methods, functions
   └─ Calculate initial metrics

2. Detect Code Smells (12 types)
   ├─ Long Method, Large Class
   ├─ Duplicate Code, Long Parameter List
   └─ Feature Envy, Data Clumps, etc.

3. Identify Technical Debt
   ├─ Debt from code smells
   ├─ Debt from missing tests
   └─ Debt from missing documentation

4. Generate Refactoring Plans
   ├─ Create plan for each smell
   ├─ Define steps
   ├─ Estimate effort
   └─ Assess risk

5. Calculate Maintainability Index
   └─ MI = 171 - 5.2*ln(HV) - 0.23*CC - 16.2*ln(LOC)

6. Prioritize Improvements
   ├─ Quick Wins (low effort, high impact)
   ├─ Priority Refactorings (medium effort)
   └─ Long-term Improvements (high effort)

7. Quality Check & Output
   ├─ Validate MI >= 65
   ├─ Check critical debt addressed
   └─ Calculate code quality score
```

## 📈 Metrics & Thresholds

### Configuration
```python
RefactoringAgentConfig(
    max_method_lines=50,        # Long Method threshold
    max_class_lines=300,        # Large Class threshold
    max_parameters=5,           # Long Parameter List threshold
    max_complexity=10,          # Cyclomatic Complexity threshold
    
    small_effort_hours=2.0,     # Quick wins
    medium_effort_hours=8.0,    # Priority refactorings
    large_effort_hours=24.0     # Long-term improvements
)
```

### Quality Metrics

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| **Maintainability Index** | 85-100 | 65-85 | 0-65 |
| **Code Quality Score** | 80-100 | 60-80 | 0-60 |
| **Code Smells** | 0-3 | 4-10 | 11+ |
| **Technical Debt (hours)** | 0-10 | 11-40 | 41+ |

## 🎯 Priority Matrix

```
                High Impact
                    ↑
                    |
    Quick Wins      |    Priority
    (Do First)      |    (Do Next)
                    |
←───────────────────┼───────────────────→
    Low Effort      |    High Effort
                    |
    Nice to Have    |    Long-term
    (Backlog)       |    (Plan)
                    |
                    ↓
                Low Impact
```

## 💻 Usage Example

```python
from app.agents.developer.refactoring_agent import RefactoringAgent

# Initialize
agent = RefactoringAgent(config={
    "smell_detection_enabled": True,
    "auto_refactor": False
})

# Analyze code
result = await agent.analyze_code(
    code=payment_processor_code,
    file_path="payment_processor.py",
    context={"requirements": [...]}
)

# Output
print(f"Code Smells: {len(result.code_smells)}")
print(f"Technical Debt: {result.total_debt_hours} hours")
print(f"Maintainability Index: {result.maintainability_index}")
print(f"Code Quality Score: {result.code_quality_score}")

# Quick wins
for win in result.quick_wins:
    print(f"✅ Quick Win: {win}")

# Priority refactorings
for priority in result.priority_refactorings:
    print(f"🎯 Priority: {priority}")
```

## 📊 Output Example

```python
RefactoringResult(
    code_smells=[
        CodeSmell(
            smell_type="LONG_METHOD",
            severity="medium",
            file_path="payment_processor.py",
            line_start=45,
            line_end=110,
            description="Method 'process_payment' has 65 lines",
            suggested_refactoring="EXTRACT_METHOD",
            effort_estimate="small"
        )
    ],
    refactoring_plans=[
        RefactoringPlan(
            refactoring_type="EXTRACT_METHOD",
            description="Refactor LONG_METHOD at lines 45-110",
            steps=[
                "1. Identify logical blocks",
                "2. Create new methods",
                "3. Add parameters",
                "4. Replace with calls",
                "5. Add docstrings",
                "6. Run tests"
            ],
            estimated_effort_hours=2.0,
            risk_level="low",
            benefits=["Improved readability", "Better testability"]
        )
    ],
    technical_debt=[
        TechnicalDebt(
            debt_type="code_smell",
            severity="medium",
            estimated_fix_time=2.0,
            business_impact="Difficult to maintain"
        )
    ],
    total_debt_hours=12.5,
    code_quality_score=78.5,
    maintainability_index=75.0,
    quick_wins=["Extract validation logic"],
    priority_refactorings=["Extract PaymentValidator class"],
    long_term_improvements=["Refactor to Strategy pattern"]
)
```

## 🔄 Feedback Loops

### 1. Low Maintainability Index Loop
- **Trigger:** MI < 65
- **Action:** Retry from Step 2
- **Max Retries:** 2

### 2. Critical Debt Not Addressed Loop
- **Trigger:** Critical debt exists but no priority plans
- **Action:** Retry from Step 4
- **Max Retries:** 1

### 3. Too Many Code Smells Loop
- **Trigger:** > 10 code smells
- **Action:** Escalate to Code Implementer if debt > 40 hours

## 📚 Documentation

- **Detailed Flow**: See [FLOW.md](./FLOW.md) for complete workflow documentation
- **Models**: See [__init__.py](./__init__.py) for Pydantic models
- **Config**: See [../config.py](../config.py) for configuration options

## 🔗 Integration

### Input từ Quality Assurer
```python
{
    "code_files": {...},
    "quality_report": {...},
    "context": {...}
}
```

### Output cho Dependency Manager
```python
RefactoringResult(
    code_smells=[...],
    refactoring_plans=[...],
    technical_debt=[...],
    maintainability_index=75.0,
    quick_wins=[...],
    priority_refactorings=[...],
    long_term_improvements=[...]
)
```

## 💡 Best Practices

### ✅ DO:
- Always detect all 12 code smell types
- Prioritize based on impact, effort, and risk
- Provide detailed refactoring steps
- Calculate accurate effort estimates
- Track technical debt over time
- Focus on quick wins first

### ❌ DON'T:
- Don't refactor without clear benefits
- Don't ignore high-severity smells
- Don't create plans without steps
- Don't underestimate effort
- Don't refactor without tests
- Don't skip maintainability calculation

## 📖 References

- **Refactoring Catalog**: https://refactoring.guru/refactoring/catalog
- **Code Smells**: https://refactoring.guru/refactoring/smells
- **Maintainability Index**: https://docs.microsoft.com/en-us/visualstudio/code-quality/code-metrics-values

---

**Status:** 📝 Ready for Implementation
**Last Updated:** 2025-01-15


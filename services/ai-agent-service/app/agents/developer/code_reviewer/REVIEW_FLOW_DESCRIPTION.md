# Code Reviewer Agent - Review Flow Chi Tiết

## Tổng Quan
Code Reviewer là sub-agent thứ 4 trong Developer Agent workflow, nhận code và test suite từ Test Generator và thực hiện comprehensive code review để đảm bảo code quality, security, và architecture trước khi chuyển cho Quality Assurer.

---

## 🎯 **Input từ Test Generator**

### **Code Package nhận được**:
- **Production-Ready Code**: Code đã được implement và optimize
- **Complete Test Suite**: Unit tests và integration tests
- **Test Coverage Report**: Báo cáo coverage chi tiết
- **Test Quality Report**: Báo cáo chất lượng tests
- **Test Execution Results**: Kết quả chạy tests
- **Test Documentation**: Documentation đầy đủ cho tests

---

## 🔍 **Code Review Flow Chi Tiết - 5 Giai Đoạn Chính**

### **Giai Đoạn 1: Code Structure và Architecture Review**

#### **Bước 1.1: Architecture Analysis (Phân Tích Kiến Trúc)**
**Mục đích**: Đánh giá kiến trúc tổng thể và design decisions

**Quá trình**:
- **Layered Architecture Review**: Kiểm tra separation of concerns giữa các layers
- **Design Pattern Analysis**: Đánh giá việc sử dụng design patterns
- **Dependency Analysis**: Kiểm tra dependency injection và coupling
- **Module Organization**: Đánh giá cách organize modules và packages
- **Interface Design**: Kiểm tra interface design và abstractions

**Trường hợp PASS**:
- Architecture clean và well-structured
- Design patterns được sử dụng appropriately
- Dependencies properly managed và loose coupling
- Modules organized logically
- Interfaces well-designed và consistent

**Trường hợp FAIL**:
- Architecture có vấn đề về separation of concerns
- Design patterns được sử dụng incorrectly hoặc unnecessary
- Tight coupling giữa components
- Modules không organized logically
- Interfaces poorly designed hoặc inconsistent

#### **Bước 1.2: Code Organization Review**
**Mục đích**: Đánh giá cách organize code và file structure

**Quá trình**:
- **File Structure Analysis**: Kiểm tra file và folder organization
- **Naming Convention Review**: Kiểm tra naming conventions
- **Import/Export Analysis**: Kiểm tra import statements và dependencies
- **Code Duplication Check**: Tìm code duplication
- **Dead Code Detection**: Tìm unused code

**Trường hợp PASS**:
- File structure logical và consistent
- Naming conventions followed properly
- Imports clean và organized
- Minimal code duplication
- No dead code detected

**Trường hợp FAIL**:
- File structure confusing hoặc inconsistent
- Naming conventions không followed
- Imports messy hoặc circular dependencies
- Significant code duplication found
- Dead code detected

---

### **Giai Đoạn 2: Logic và Business Rules Review**

#### **Bước 2.1: Business Logic Analysis**
**Mục đích**: Đánh giá business logic implementation

**Quá trình**:
- **Business Rule Implementation**: Kiểm tra business rules được implement correctly
- **Logic Flow Analysis**: Phân tích logic flows và decision points
- **Edge Case Handling**: Kiểm tra handling của edge cases
- **Error Handling Logic**: Đánh giá error handling strategies
- **Data Validation Logic**: Kiểm tra data validation logic

**Trường hợp PASS**:
- Business rules implemented correctly và completely
- Logic flows clear và consistent
- Edge cases handled properly
- Error handling comprehensive và appropriate
- Data validation thorough và consistent

**Trường hợp FAIL**:
- Business rules implemented incorrectly hoặc incomplete
- Logic flows confusing hoặc inconsistent
- Edge cases không handled properly
- Error handling inadequate hoặc missing
- Data validation insufficient hoặc inconsistent

#### **Bước 2.2: Algorithm và Performance Logic Review**
**Mục đích**: Đánh giá algorithms và performance logic

**Quá trình**:
- **Algorithm Efficiency**: Kiểm tra efficiency của algorithms
- **Time Complexity Analysis**: Phân tích time complexity
- **Space Complexity Analysis**: Phân tích space complexity
- **Performance Bottlenecks**: Tìm performance bottlenecks
- **Scalability Considerations**: Đánh giá scalability

**Trường hợp PASS**:
- Algorithms efficient và appropriate
- Time complexity acceptable cho use cases
- Space complexity optimized
- No significant performance bottlenecks
- Code designed for scalability

**Trường hợp FAIL**:
- Algorithms inefficient hoặc inappropriate
- Time complexity quá cao cho use cases
- Space complexity không optimized
- Performance bottlenecks detected
- Code không designed for scalability

---

### **Giai Đoạn 3: Security Review**

#### **Bước 3.1: Security Vulnerability Analysis**
**Mục đích**: Tìm security vulnerabilities và risks

**Quá trình**:
- **Input Validation Security**: Kiểm tra input validation security
- **Authentication & Authorization**: Đánh giá auth mechanisms
- **Data Protection**: Kiểm tra data protection và encryption
- **SQL Injection Prevention**: Kiểm tra SQL injection prevention
- **XSS Prevention**: Kiểm tra XSS prevention
- **CSRF Protection**: Kiểm tra CSRF protection

**Trường hợp PASS**:
- Input validation comprehensive và secure
- Authentication & authorization properly implemented
- Data protection adequate
- SQL injection prevention in place
- XSS prevention implemented
- CSRF protection in place

**Trường hợp FAIL**:
- Input validation insufficient hoặc missing
- Authentication & authorization issues
- Data protection inadequate
- SQL injection vulnerabilities found
- XSS vulnerabilities found
- CSRF vulnerabilities found

#### **Bước 3.2: Security Best Practices Review**
**Mục đích**: Kiểm tra security best practices

**Quá trình**:
- **Password Security**: Kiểm tra password handling
- **Session Management**: Đánh giá session management
- **Error Information Disclosure**: Kiểm tra error information disclosure
- **Logging Security**: Kiểm tra logging security practices
- **API Security**: Đánh giá API security

**Trường hợp PASS**:
- Password security best practices followed
- Session management secure
- Error information không disclosed inappropriately
- Logging security practices followed
- API security properly implemented

**Trường hợp FAIL**:
- Password security issues found
- Session management vulnerabilities
- Error information disclosed inappropriately
- Logging security issues
- API security vulnerabilities

---

### **Giai Đoạn 4: Code Quality và Maintainability Review**

#### **Bước 4.1: Code Quality Assessment**
**Mục đích**: Đánh giá overall code quality

**Quá trình**:
- **Code Readability**: Kiểm tra code readability
- **Code Consistency**: Đánh giá code consistency
- **Documentation Quality**: Kiểm tra documentation quality
- **Code Style Compliance**: Kiểm tra coding standards compliance
- **Complexity Analysis**: Phân tích code complexity

**Trường hợp PASS**:
- Code highly readable và well-structured
- Code consistent throughout
- Documentation comprehensive và clear
- Coding standards fully complied
- Code complexity manageable

**Trường hợp FAIL**:
- Code difficult to read hoặc poorly structured
- Code inconsistent
- Documentation inadequate hoặc unclear
- Coding standards not followed
- Code complexity too high

#### **Bước 4.2: Maintainability Review**
**Mục đích**: Đánh giá code maintainability

**Quá trình**:
- **Modularity Assessment**: Kiểm tra code modularity
- **Extensibility Analysis**: Đánh giá extensibility
- **Testability Review**: Kiểm tra code testability
- **Refactoring Opportunities**: Tìm refactoring opportunities
- **Technical Debt Assessment**: Đánh giá technical debt

**Trường hợp PASS**:
- Code highly modular và well-organized
- Code easily extensible
- Code highly testable
- Minimal refactoring needed
- Low technical debt

**Trường hợp FAIL**:
- Code poorly modular
- Code difficult to extend
- Code difficult to test
- Significant refactoring needed
- High technical debt

---

### **Giai Đoạn 5: Integration và Test Review**

#### **Bước 5.1: Integration Review**
**Mục đích**: Đánh giá integration aspects

**Quá trình**:
- **API Design Review**: Kiểm tra API design và consistency
- **Database Integration**: Đánh giá database integration
- **External Service Integration**: Kiểm tra external service integration
- **Error Handling Integration**: Đánh giá error handling trong integrations
- **Performance Integration**: Kiểm tra performance trong integrations

**Trường hợp PASS**:
- API design consistent và well-documented
- Database integration proper
- External service integration robust
- Error handling comprehensive trong integrations
- Performance acceptable trong integrations

**Trường hợp FAIL**:
- API design inconsistent hoặc poorly documented
- Database integration issues
- External service integration fragile
- Error handling inadequate trong integrations
- Performance issues trong integrations

#### **Bước 5.2: Test Coverage và Quality Review**
**Mục đích**: Đánh giá test suite quality

**Quá trình**:
- **Test Coverage Analysis**: Phân tích test coverage
- **Test Quality Assessment**: Đánh giá test quality
- **Test Scenarios Review**: Kiểm tra test scenarios completeness
- **Mock Quality Review**: Đánh giá mock quality
- **Test Documentation Review**: Kiểm tra test documentation

**Trường hợp PASS**:
- Test coverage comprehensive (≥80%)
- Test quality high
- Test scenarios complete
- Mocks realistic và well-designed
- Test documentation clear

**Trường hợp FAIL**:
- Test coverage insufficient (<80%)
- Test quality low
- Test scenarios incomplete
- Mocks unrealistic hoặc poorly designed
- Test documentation inadequate

---

## 🔄 **Feedback Loops Chi Tiết cho Trường Hợp FAIL**

### **Feedback Loop 1: Architecture Issues → Code Implementer**
**Trigger**: Architecture analysis FAIL
**Severity**: Critical
**Action**:
- **Send back to Code Implementer** với detailed architecture feedback
- **Specific Issues**: Poor separation of concerns, incorrect design patterns, tight coupling
- **Required Changes**: Restructure architecture, refactor design patterns, improve modularity
- **Timeline**: 2-3 days để fix architecture issues
- **Re-review**: Full architecture review sau khi fix

### **Feedback Loop 2: Business Logic Issues → Code Implementer**
**Trigger**: Business logic analysis FAIL
**Severity**: High
**Action**:
- **Send back to Code Implementer** với business logic feedback
- **Specific Issues**: Incorrect business rules, missing edge cases, poor error handling
- **Required Changes**: Fix business logic, add missing edge cases, improve error handling
- **Timeline**: 1-2 days để fix business logic
- **Re-review**: Business logic review sau khi fix

### **Feedback Loop 3: Security Issues → Code Implementer**
**Trigger**: Security review FAIL
**Severity**: Critical
**Action**:
- **Send back to Code Implementer** với security feedback
- **Specific Issues**: Security vulnerabilities, missing security measures
- **Required Changes**: Fix security issues, implement missing security measures
- **Timeline**: 1-3 days để fix security issues
- **Re-review**: Full security review sau khi fix

### **Feedback Loop 4: Code Quality Issues → Code Implementer**
**Trigger**: Code quality assessment FAIL
**Severity**: Medium
**Action**:
- **Send back to Code Implementer** với code quality feedback
- **Specific Issues**: Poor readability, inconsistency, documentation issues
- **Required Changes**: Improve code readability, fix inconsistencies, add documentation
- **Timeline**: 1 day để fix code quality issues
- **Re-review**: Code quality review sau khi fix

### **Feedback Loop 5: Test Issues → Test Generator**
**Trigger**: Test review FAIL
**Severity**: Medium
**Action**:
- **Send back to Test Generator** với test feedback
- **Specific Issues**: Low coverage, poor test quality, missing scenarios
- **Required Changes**: Improve test coverage, enhance test quality, add missing scenarios
- **Timeline**: 1-2 days để improve tests
- **Re-review**: Test review sau khi improve

### **Feedback Loop 6: Integration Issues → Code Implementer**
**Trigger**: Integration review FAIL
**Severity**: High
**Action**:
- **Send back to Code Implementer** với integration feedback
- **Specific Issues**: API design issues, integration problems, performance issues
- **Required Changes**: Fix API design, improve integrations, optimize performance
- **Timeline**: 2-3 days để fix integration issues
- **Re-review**: Integration review sau khi fix

---

## 📊 **Review Scoring System**

### **Scoring Criteria**:
- **Architecture Score**: 0-100 (Weight: 25%)
- **Logic Score**: 0-100 (Weight: 20%)
- **Security Score**: 0-100 (Weight: 25%)
- **Quality Score**: 0-100 (Weight: 15%)
- **Integration Score**: 0-100 (Weight: 15%)

### **Overall Score Calculation**:
```
Overall Score = (Architecture × 0.25) + (Logic × 0.20) + (Security × 0.25) + (Quality × 0.15) + (Integration × 0.15)
```

### **Pass/Fail Thresholds**:
- **PASS**: Overall Score ≥ 80 AND each category ≥ 70
- **FAIL**: Overall Score < 80 OR any category < 70

---

## 🎯 **Decision Points và Actions**

### **Decision Point 1: Overall Score Check**
**Trigger**: Sau khi complete tất cả reviews
**Condition**: Overall Score ≥ 80 AND all categories ≥ 70
**Action**: 
- **PASS**: Chuyển cho Quality Assurer
- **FAIL**: Trigger appropriate feedback loop

### **Decision Point 2: Critical Issues Check**
**Trigger**: Sau khi detect critical issues
**Condition**: Security < 70 OR Architecture < 70
**Action**:
- **CRITICAL**: Immediate feedback loop với high priority
- **NON-CRITICAL**: Standard feedback loop

### **Decision Point 3: Multiple Issues Check**
**Trigger**: Khi có multiple categories fail
**Condition**: 3+ categories < 70
**Action**:
- **MULTIPLE**: Send back to Code Implementer với comprehensive feedback
- **SINGLE**: Send back với specific category feedback

---

## 📤 **Code Reviewer Output**

### **Main Deliverables**:
1. **Comprehensive Review Report**: Detailed review với scores và feedback
2. **Security Assessment**: Security vulnerabilities và recommendations
3. **Architecture Analysis**: Architecture issues và improvement suggestions
4. **Quality Metrics**: Detailed quality metrics và scores
5. **Action Items**: Specific action items để fix issues

### **Quality Metrics**:
1. **Overall Review Score**: Weighted average của all categories
2. **Category Scores**: Individual scores cho từng category
3. **Issue Count**: Number of issues found trong mỗi category
4. **Severity Distribution**: Distribution of issue severities
5. **Recommendation Count**: Number of recommendations provided

### **Next Phase Input**:
- **Approved Code Package**: Code đã pass review (nếu PASS)
- **Review Report**: Comprehensive review report
- **Security Clearance**: Security assessment results
- **Quality Certification**: Quality certification với scores
- **Action Items**: Action items để address remaining issues

---

## 🎯 **Kết Luận**

Code Reviewer thông qua 5 giai đoạn comprehensive review:

1. **Architecture Review**: Đánh giá kiến trúc và design decisions
2. **Logic Review**: Đánh giá business logic và algorithms
3. **Security Review**: Tìm security vulnerabilities và risks
4. **Quality Review**: Đánh giá code quality và maintainability
5. **Integration Review**: Đánh giá integration và test quality

Với 6 feedback loops chi tiết để handle các trường hợp fail:
- **Architecture Issues** → Code Implementer (Critical)
- **Business Logic Issues** → Code Implementer (High)
- **Security Issues** → Code Implementer (Critical)
- **Code Quality Issues** → Code Implementer (Medium)
- **Test Issues** → Test Generator (Medium)
- **Integration Issues** → Code Implementer (High)

Scoring system với weighted categories và clear pass/fail thresholds đảm bảo chỉ code chất lượng cao mới được approve để chuyển cho Quality Assurer.

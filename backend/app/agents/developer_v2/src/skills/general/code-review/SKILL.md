---
name: code-review
description: Review code for quality, security, performance, and best practices
triggers:
  - review
  - check
  - audit
  - quality
  - security
  - performance
  - best practice
  - improve
  - refactor
version: "1.0"
author: VibeSDLC
---

# Code Review Skill

## When to Use
- Reviewing code changes before commit
- Auditing existing code for issues
- Identifying security vulnerabilities
- Suggesting performance improvements
- Ensuring coding standards

## Review Checklist

### 1. Correctness
- [ ] Does the code do what it's supposed to do?
- [ ] Are edge cases handled?
- [ ] Is error handling appropriate?
- [ ] Are there any logical errors?

### 2. Security
- [ ] No hardcoded secrets/credentials
- [ ] Input validation present
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] Authentication/authorization checks
- [ ] Sensitive data not logged

### 3. Performance
- [ ] No unnecessary loops/iterations
- [ ] Database queries optimized (N+1 problem)
- [ ] Proper indexing for queries
- [ ] Memory-efficient data structures
- [ ] Caching where appropriate

### 4. Code Quality
- [ ] Clear, descriptive names
- [ ] Single responsibility principle
- [ ] No code duplication (DRY)
- [ ] Appropriate comments (why, not what)
- [ ] Consistent formatting

### 5. TypeScript/JavaScript Specific
- [ ] Proper typing (no `any` unless necessary)
- [ ] Null/undefined handling
- [ ] Async/await properly used
- [ ] Imports organized

## Security Patterns

### Input Validation
```typescript
// Bad: No validation
async function createUser(data: any) {
  await prisma.user.create({ data });
}

// Good: Zod validation
import { z } from 'zod';

const userSchema = z.object({
  email: z.string().email(),
  name: z.string().min(2).max(100),
});

async function createUser(data: unknown) {
  const validated = userSchema.parse(data);
  await prisma.user.create({ data: validated });
}
```

### SQL Injection Prevention
```typescript
// Bad: String concatenation
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// Good: Parameterized query (Prisma handles this)
const user = await prisma.user.findUnique({ where: { id: userId } });

// Good: Raw query with parameters
const users = await prisma.$queryRaw`SELECT * FROM users WHERE id = ${userId}`;
```

### XSS Prevention
```tsx
// Bad: dangerouslySetInnerHTML without sanitization
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// Good: Use text content (auto-escaped)
<div>{userInput}</div>

// Good: Sanitize if HTML needed
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />
```

## Performance Patterns

### N+1 Query Problem
```typescript
// Bad: N+1 queries
const users = await prisma.user.findMany();
for (const user of users) {
  const posts = await prisma.post.findMany({ where: { authorId: user.id } });
}

// Good: Include related data
const users = await prisma.user.findMany({
  include: { posts: true },
});
```

### Unnecessary Re-renders (React)
```tsx
// Bad: New object/array on every render
function Component() {
  return <Child style={{ color: 'red' }} items={[1, 2, 3]} />;
}

// Good: Memoize or define outside
const style = { color: 'red' };
const items = [1, 2, 3];

function Component() {
  return <Child style={style} items={items} />;
}

// Good: useMemo for computed values
function Component({ data }) {
  const processed = useMemo(() => expensiveProcess(data), [data]);
  return <Child data={processed} />;
}
```

### Database Indexing
```prisma
// schema.prisma - Add indexes for frequently queried fields
model Post {
  id        String   @id @default(cuid())
  title     String
  authorId  String
  createdAt DateTime @default(now())
  
  @@index([authorId])
  @@index([createdAt])
}
```

## Code Quality Patterns

### Single Responsibility
```typescript
// Bad: Function does too much
async function handleUserSubmit(formData: FormData) {
  // Validates
  // Creates user
  // Sends email
  // Updates analytics
  // Logs event
}

// Good: Separated concerns
async function handleUserSubmit(formData: FormData) {
  const data = validateUserData(formData);
  const user = await createUser(data);
  await sendWelcomeEmail(user);
  trackUserSignup(user);
}
```

### Meaningful Names
```typescript
// Bad
const d = new Date();
const u = users.filter(x => x.a);

// Good
const currentDate = new Date();
const activeUsers = users.filter(user => user.isActive);
```

## Review Response Template

```markdown
## Code Review: [Feature/File Name]

### Summary
Brief overview of changes and overall assessment.

### Issues Found
1. **[Severity: High/Medium/Low]** Description
   - Location: `file.ts:line`
   - Suggestion: How to fix

### Suggestions
- Performance: ...
- Code quality: ...
- Security: ...

### Approved: Yes/No (with conditions)
```

# AI Agent Guidelines for Node.js Backend Development

---

## Tech Stack

- Runtime: Node.js 18+
- Framework: Express.js 4.x
- Database: MongoDB + Mongoose ODM
- Auth: JWT (jsonwebtoken + bcryptjs)
- Validation: Joi
- Testing: Jest + Supertest

---

## Architecture Flow

```
Routes → Controllers → Services → Repositories → Models
```

MANDATORY: Always follow this layered architecture. Each layer depends on the previous one.

---

## Folder Structure

```
src/
├── config/           # App and database configuration
├── constants/        # Application constants (roles, status codes)
├── controllers/      # Request handlers (thin layer)
├── db/
│   ├── migrations/   # Database migration scripts
│   └── seeds/        # Database seed data
├── dtos/             # Data Transfer Objects (response formatting)
├── middleware/       # Express middlewares (auth, validation, errors)
├── models/           # Mongoose schemas (PascalCase)
├── repositories/     # Data access layer
├── routes/           # API endpoints
├── services/         # Business logic
├── tests/            # Test files
└── utils/            # Utility functions (logger, validators, helpers)
```

---

## Implementation Rules

### Rule 1: Implementation Order

MANDATORY SEQUENCE: Models → Repositories → Services → Controllers → Routes → Tests

### Rule 2: Separation of Concerns

**Controllers**: Parse request, call services, format response. NO business logic.
**Services**: Business rules, orchestrate repositories. NO request handling.
**Repositories**: Database operations only. NO business logic.

### Rule 3: Naming Conventions

- camelCase: `userController.js`, `authService.js`, `userRepository.js`
- PascalCase: `User.js`, `Product.js` (models only)
- kebab-case: `auth-controller.test.js` (tests only)

## Setup commands
- Install deps: `npm install`
- Start dev server: `npm dev`
- Run tests: `npm test`

## Implementation Checklist

1. Create Model with validation
2. Create Repository with data access
3. Create Service with business logic
4. Create DTO for response
5. Create Controller (thin layer)
6. Create Routes with validation
7. Write tests
8. Add JSDoc comments

## Best Practices

### DO:
- Follow layered architecture strictly
- Use async/await
- Validate all inputs
- Use .lean() for read queries
- Export singletons for services/repos
- Handle errors with AppError
- Write tests

### DONT:
- Mix business logic in controllers
- Query database in controllers
- Skip validation
- Expose sensitive data
- Use console.log (use logger)
- Skip error handling
- Hardcode values
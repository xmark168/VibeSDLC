# AGENTS.md - Express.js Basic Boilerplate

**AI Agent Guidelines for Express.js + MongoDB Development**

---

## 🎯 Tech Stack

- **Runtime**: Node.js 18+
- **Framework**: Express.js 4.x
- **Database**: MongoDB + Mongoose ODM
- **Auth**: JWT (jsonwebtoken + bcryptjs)
- **Validation**: Joi + express-validator
- **Testing**: Jest + Supertest

---

## 🏗️ CRITICAL: Layered Architecture

**MANDATORY FLOW**: Routes → Controllers → Services → Repositories → Models

```
┌─────────────────────────────────────────────────┐
│  Routes (API Endpoints)                         │
│  - Define URL paths                             │
│  - Map to controller methods                    │
│  - Apply middleware (auth, validation)          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Controllers (Request Handlers)                 │
│  - Parse request data (params, query, body)     │
│  - Call service layer                           │
│  - Format response                              │
│  - Pass errors to next()                        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Services (Business Logic)                      │
│  - Implement business rules                     │
│  - Orchestrate repositories                     │
│  - Handle transactions                          │
│  - Throw AppError for failures                  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Repositories (Data Access)                     │
│  - Abstract database operations                 │
│  - Query builders                               │
│  - Use .lean() for performance                  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Models (Database Schemas)                      │
│  - Mongoose schemas                             │
│  - Validation rules                             │
│  - Indexes                                      │
└─────────────────────────────────────────────────┘
```

---

## 📁 Folder Structure

```
src/
├── config/                # Configuration files
├── constants/             # Application constants
├── controllers/           # Request handlers (THIN - no business logic)
├── db/
│   ├── migrations/        # Database migration files
│   └── seeds/             # Database seed files
├── dtos/                  # Data Transfer Objects
├── middleware/            # Express middlewares
├── models/                # Mongoose models (PascalCase)
├── repositories/          # Data access layer
├── routes/                # API routes
├── services/              # Business logic
├── tests/                 # Test files
└── utils/                 # Utility functions
```

---

## 🎯 CRITICAL IMPLEMENTATION RULES

### Rule #1: ALWAYS Follow Implementation Order

**MANDATORY SEQUENCE**: Models → Repositories → Services → Controllers → Routes

1. **Model** - Define database schema first
2. **Repository** - Create data access layer
3. **Service** - Implement business logic
4. **Controller** - Handle requests/responses
5. **Routes** - Define API endpoints
6. **Tests** - Validate functionality

**WHY**: Each layer depends on the previous one. Breaking this order causes errors.

### Rule #2: NEVER Mix Concerns

**Controllers**:
- ✅ Parse request data
- ✅ Call service methods
- ✅ Format responses
- ❌ NEVER put business logic in controllers
- ❌ NEVER query database in controllers
- ❌ NO validation logic

**Services**:
- ✅ Business rules
- ✅ Orchestrate repositories
- ✅ Throw AppError
- ❌ NO request/response handling
- ❌ NO direct database queries

**Repositories**:
- ✅ Database operations
- ✅ Query builders
- ❌ NO business logic
- ❌ NO error responses

### Rule #3: File Naming Conventions

- **camelCase**: `userController.js`, `authService.js`, `userRepository.js`
- **PascalCase**: `User.js`, `Product.js` (models only)
- **kebab-case**: `user-controller.test.js` (tests only)

---

## 📐 Code Patterns

### Pattern #1: Model (Mongoose Schema)

```javascript
// src/models/User.js
const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  name: {
    type: String,
    required: [true, 'Name is required'],
    trim: true,
  },
  email: {
    type: String,
    required: [true, 'Email is required'],
    unique: true,
    lowercase: true,
  },
  password: {
    type: String,
    required: [true, 'Password is required'],
    select: false, // Don't return by default
  },
}, { timestamps: true });

// Indexes
userSchema.index({ email: 1 });

module.exports = mongoose.model('User', userSchema);
```

### Pattern #2: Repository (Data Access)

```javascript
// src/repositories/userRepository.js
const User = require('../models/User');
const { AppError } = require('../utils/errors');

class UserRepository {
  async findByEmail(email) {
    return await User.findOne({ email }).lean();
  }
  
  async create(userData) {
    const user = new User(userData);
    await user.save();
    return user.toObject();
  }
  
  async findById(userId) {
    return await User.findById(userId).select('-password').lean();
  }
}

module.exports = new UserRepository();
```

### Pattern #3: Service (Business Logic)

```javascript
// src/services/authService.js
const userRepository = require('../repositories/userRepository');
const { AppError } = require('../utils/errors');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

class AuthService {
  async registerUser(userData) {
    // Check if user exists
    const existingUser = await userRepository.findByEmail(userData.email);
    if (existingUser) {
      throw new AppError('User already exists', 409);
    }
    
    // Hash password
    userData.password = await bcrypt.hash(userData.password, 12);
    
    // Create user
    const newUser = await userRepository.create(userData);
    
    // Generate token
    const token = jwt.sign({ id: newUser._id }, process.env.JWT_SECRET, {
      expiresIn: '1h',
    });
    
    return { user: newUser, token };
  }
}

module.exports = new AuthService();
```

### Pattern #4: Controller (Request Handler)

```javascript
// src/controllers/authController.js
const authService = require('../services/authService');

exports.registerUser = async (req, res, next) => {
  try {
    const userData = req.body;
    const result = await authService.registerUser(userData);
    
    return res.status(201).json({
      success: true,
      data: result,
      message: 'User registered successfully',
    });
  } catch (error) {
    next(error);
  }
};
```

### Pattern #5: Routes (API Endpoints)

```javascript
// src/routes/auth.js
const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const { validateRequest } = require('../middleware/validate');
const { userValidation } = require('../utils/validators');

/**
 * @route   POST /api/v1/auth/register
 * @desc    Register new user
 * @access  Public
 */
router.post(
  '/register',
  validateRequest(userValidation.createUser),
  authController.registerUser
);

module.exports = router;
```

---

## ❌ Error Handling

### Custom Error Class

```javascript
// src/utils/errors.js
class AppError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
  }
}

module.exports = { AppError };
```

### Throwing Errors

```javascript
// In services
if (!user) {
  throw new AppError('User not found', 404);
}

if (existingUser) {
  throw new AppError('Email already in use', 409);
}
```

---

## 🧪 Testing Pattern

```javascript
// src/tests/integration/auth.test.js
const request = require('supertest');
const app = require('../../app');

describe('POST /api/v1/auth/register', () => {
  it('should register new user', async () => {
    const response = await request(app)
      .post('/api/v1/auth/register')
      .send({
        name: 'John Doe',
        email: 'john@example.com',
        password: 'password123',
      })
      .expect(201);
    
    expect(response.body.success).toBe(true);
    expect(response.body.data).toHaveProperty('token');
  });
});
```

---

## 🤖 AI Agent Checklist

When implementing a new feature:

- [ ] **Step 1**: Create Model with validation
- [ ] **Step 2**: Create Repository with CRUD methods
- [ ] **Step 3**: Create Service with business logic
- [ ] **Step 4**: Create Controller (thin, no business logic)
- [ ] **Step 5**: Create Routes with middleware
- [ ] **Step 6**: Add validation schemas
- [ ] **Step 7**: Write integration tests
- [ ] **Step 8**: Add JSDoc comments

---

## ✅ DO's

1. **Follow layered architecture** - Models → Repos → Services → Controllers → Routes
2. **Use async/await** - Never use callbacks
3. **Validate all inputs** - Use Joi schemas
4. **Handle errors properly** - Throw AppError, pass to next()
5. **Export singletons** - Services and repositories
6. **Use .lean()** - For read-only queries
7. **Add indexes** - For frequently queried fields

## ❌ DON'Ts

1. **Don't mix business logic in controllers** - Keep controllers thin
2. **Don't query database in controllers** - Use repositories
3. **Don't use console.log** - Use logger
4. **Don't skip validation** - Validate all inputs
5. **Don't expose passwords** - Use select: false
6. **Don't use var** - Use const/let
7. **Don't skip tests** - Test critical paths

---

**Version**: 2.0.0 (Optimized)  
**Lines**: ~300 (reduced from 1930)  
**Last Updated**: 2025-01-22


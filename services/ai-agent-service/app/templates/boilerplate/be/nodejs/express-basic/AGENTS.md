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

---

## Core Patterns

### Model

```javascript
// src/models/User.js
const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  name: { type: String, required: true, trim: true },
  email: { type: String, required: true, unique: true, lowercase: true },
  password: { type: String, required: true, select: false },
  role: { type: String, enum: ['user', 'admin'], default: 'user' },
}, { timestamps: true });

userSchema.index({ email: 1 });

module.exports = mongoose.model('User', userSchema);
```

### Repository

```javascript
// src/repositories/userRepository.js
const User = require('../models/User');

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

### Service

```javascript
// src/services/authService.js
const userRepository = require('../repositories/userRepository');
const { AppError } = require('../utils/errors');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

class AuthService {
  async registerUser(userData) {
    const existingUser = await userRepository.findByEmail(userData.email);
    if (existingUser) {
      throw new AppError('User already exists', 409);
    }
    
    userData.password = await bcrypt.hash(userData.password, 12);
    const newUser = await userRepository.create(userData);
    
    const token = jwt.sign({ id: newUser._id }, process.env.JWT_SECRET, {
      expiresIn: '1h',
    });
    
    return { user: newUser, token };
  }
}

module.exports = new AuthService();
```

### Controller

```javascript
// src/controllers/authController.js
const authService = require('../services/authService');

exports.registerUser = async (req, res, next) => {
  try {
    const result = await authService.registerUser(req.body);
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

### Routes

```javascript
// src/routes/auth.js
const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const { validateRequest } = require('../middleware/validate');
const { authValidation } = require('../utils/validators');

router.post('/register', validateRequest(authValidation.register), authController.registerUser);

module.exports = router;
```

---

## Configuration

```javascript
// src/config/database.js
const mongoose = require('mongoose');

const connectDB = async () => {
  await mongoose.connect(process.env.MONGO_URI);
  console.log('MongoDB Connected');
};

module.exports = connectDB;
```

```javascript
// src/config/app.js
module.exports = {
  port: process.env.PORT || 3000,
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: '1h',
  },
};
```

---

## Middleware

```javascript
// src/middleware/auth.js
const jwt = require('jsonwebtoken');
const { AppError } = require('../utils/errors');

exports.protect = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) throw new AppError('Not authorized', 401);
    
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    next(error);
  }
};
```

```javascript
// src/middleware/validate.js
exports.validateRequest = (schema) => {
  return (req, res, next) => {
    const { error } = schema.validate(req.body, { abortEarly: false });
    if (error) {
      return next(new AppError(error.details.map(d => d.message).join(', '), 400));
    }
    next();
  };
};
```

```javascript
// src/middleware/errorHandler.js
const errorHandler = (err, req, res, next) => {
  const statusCode = err.statusCode || 500;
  const message = err.message || 'Server Error';
  
  res.status(statusCode).json({
    success: false,
    error: message,
  });
};

module.exports = errorHandler;
```

---

## DTO Pattern

```javascript
// src/dtos/userDto.js
class UserDto {
  constructor(user) {
    this.id = user._id;
    this.name = user.name;
    this.email = user.email;
    this.role = user.role;
  }
  
  static fromModel(user) {
    return new UserDto(user);
  }
}

module.exports = UserDto;
```

---

## Database Operations

```javascript
// src/db/migrations/20250126_add_role.js
module.exports = {
  async up() {
    await User.updateMany({ role: { $exists: false } }, { $set: { role: 'user' } });
  },
  async down() {
    await User.updateMany({}, { $unset: { role: '' } });
  },
};
```

```javascript
// src/db/seeds/userSeeder.js
const User = require('../../models/User');
const bcrypt = require('bcryptjs');

module.exports = {
  async seed() {
    await User.deleteMany({});
    await User.create({
      name: 'Admin',
      email: 'admin@example.com',
      password: await bcrypt.hash('admin123', 12),
      role: 'admin',
    });
  },
};
```

---

## Utilities

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

```javascript
// src/utils/validators.js
const Joi = require('joi');

exports.authValidation = {
  register: Joi.object({
    name: Joi.string().min(2).required(),
    email: Joi.string().email().required(),
    password: Joi.string().min(8).required(),
  }),
};
```

```javascript
// src/utils/logger.js
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.Console(),
  ],
});

module.exports = logger;
```

---

## Constants

```javascript
// src/constants/roles.js
module.exports = {
  ADMIN: 'admin',
  USER: 'user',
};
```

```javascript
// src/constants/httpStatus.js
module.exports = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  NOT_FOUND: 404,
};
```

---

## Testing

```javascript
// src/tests/auth.test.js
const request = require('supertest');
const app = require('../app');

describe('POST /api/auth/register', () => {
  it('should register new user', async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({ name: 'John', email: 'john@test.com', password: 'password123' })
      .expect(201);
    
    expect(res.body.success).toBe(true);
    expect(res.body.data).toHaveProperty('token');
  });
});
```

---

## Implementation Checklist

1. Create Model with validation
2. Create Repository with data access
3. Create Service with business logic
4. Create DTO for response
5. Create Controller (thin layer)
6. Create Routes with validation
7. Write tests
8. Add JSDoc comments

---

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

---
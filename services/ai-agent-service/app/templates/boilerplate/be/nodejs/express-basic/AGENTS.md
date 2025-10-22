# AGENTS.md - Express.js Basic Boilerplate

This document provides comprehensive guidance for AI agents working with this Express.js Basic application template.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Coding Conventions](#coding-conventions)
- [Common Patterns](#common-patterns)
- [Feature Development](#feature-development)
- [Testing Guidelines](#testing-guidelines)
- [Environment Configuration](#environment-configuration)
- [Security Practices](#security-practices)
- [Error Handling](#error-handling)

---

## 🎯 Project Overview

**Tech Stack:**
- **Runtime**: Node.js 18+
- **Framework**: Express.js 4.x
- **Database**: MongoDB with Mongoose ODM
- **Caching**: Redis
- **Authentication**: JWT (jsonwebtoken + bcryptjs)
- **Validation**: Joi + express-validator
- **Logging**: Winston
- **Testing**: Jest + Supertest
- **Code Quality**: ESLint + Prettier + Husky

**Architecture Pattern**: Layered Architecture (Routes → Controllers → Services → Repositories → Models)

**API Style**: RESTful API with JSON responses

**Port**: Default 3000 (configurable via `PORT` env var)

---

## 🏗️ Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────┐
│  Routes (API Endpoints)                         │
│  - Define URL paths                             │
│  - Map to controller methods                    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Controllers (Request Handlers)                 │
│  - Parse request data                           │
│  - Validate input (DTOs)                        │
│  - Call service layer                           │
│  - Format response                              │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Services (Business Logic)                      │
│  - Implement business rules                     │
│  - Orchestrate multiple repositories            │
│  - Handle transactions                          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Repositories (Data Access)                     │
│  - Abstract database operations                 │
│  - Query builders                               │
│  - Data transformation                          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Models (Database Schemas)                      │
│  - Mongoose schemas                             │
│  - Model methods                                │
│  - Virtuals and indexes                         │
└─────────────────────────────────────────────────┘
```

---

## 📁 Folder Structure

```
express-basic/
├── src/
│   ├── app.js                 # Main application entry point
│   ├── config/                # Configuration files
│   │   ├── index.js           # Centralized config with env vars
│   │   └── database.js        # MongoDB connection setup
│   ├── constants/             # Application constants
│   │   └── index.js           # Shared constants (status codes, etc.)
│   ├── controllers/           # Request handlers
│   │   ├── authController.js  # Authentication endpoints
│   │   └── userController.js  # User management endpoints
│   ├── db/                    # Database utilities
│   │   └── seed.js            # Database seeding scripts
│   ├── dtos/                  # Data Transfer Objects
│   │   └── userDto.js         # Request/Response DTOs
│   ├── middlewares/           # Express middlewares
│   │   ├── auth.js            # JWT authentication middleware
│   │   ├── errorHandler.js    # Global error handler
│   │   └── validate.js        # Request validation middleware
│   ├── models/                # Mongoose models
│   │   └── User.js            # User model/schema
│   ├── repositories/          # Data access layer
│   │   └── userRepository.js  # User database operations
│   ├── routes/                # API routes
│   │   ├── auth.js            # Auth routes (/api/v1/auth)
│   │   ├── users.js           # User routes (/api/v1/users)
│   │   └── health.js          # Health check routes
│   ├── services/              # Business logic
│   │   ├── authService.js     # Authentication logic
│   │   └── userService.js     # User business logic
│   ├── tests/                 # Test files
│   │   ├── unit/              # Unit tests
│   │   └── integration/       # Integration tests
│   └── utils/                 # Utility functions
│       ├── logger.js          # Winston logger setup
│       ├── validators.js      # Joi validation schemas
│       └── helpers.js         # Helper functions
├── .env.example               # Environment variables template
├── package.json               # Dependencies and scripts
├── .eslintrc.js               # ESLint configuration
├── .prettierrc                # Prettier configuration
└── jest.config.js             # Jest configuration
```

---

## 📐 Coding Conventions

### 1. Naming Conventions

#### Files
- **camelCase** for JavaScript files: `userController.js`, `authService.js`
- **PascalCase** for model files: `User.js`, `Product.js`
- **kebab-case** for test files: `user-controller.test.js`

#### Variables & Functions
```javascript
// camelCase for variables and functions
const userName = 'John';
function getUserById(id) { }

// PascalCase for classes and constructors
class UserService { }

// UPPER_SNAKE_CASE for constants
const MAX_LOGIN_ATTEMPTS = 5;
const API_BASE_URL = 'https://api.example.com';
```

#### Async Functions
- Always use `async/await` over `.then()/.catch()`
- Prefix async functions with descriptive verbs

```javascript
// ✅ Good
async function fetchUserData(userId) { }
async function createNewUser(userData) { }

// ❌ Avoid
async function user(id) { }
function getData() { return promise; }
```

### 2. Code Style

#### Semicolons
- **Always use semicolons** (enforced by ESLint)

#### Quotes
- **Single quotes** for strings
- **Template literals** for string interpolation

```javascript
// ✅ Good
const name = 'John';
const greeting = `Hello, ${name}!`;

// ❌ Avoid
const name = "John";
const greeting = 'Hello, ' + name + '!';
```

#### Arrow Functions
- Use arrow functions for callbacks
- Use regular functions for methods that need `this`

```javascript
// ✅ Good - callbacks
users.map(user => user.name);
setTimeout(() => console.log('Done'), 1000);

// ✅ Good - class methods
class UserService {
  async findUser(id) {
    return this.repository.findById(id);
  }
}
```

### 3. Module Exports

```javascript
// ✅ Good - Named exports for utilities
module.exports = {
  validateEmail,
  sanitizeInput,
};

// ✅ Good - Default export for single responsibility
module.exports = UserService;

// ✅ Good - Mixed (prefer this)
class UserService { }
module.exports = UserService;
```

---

## 🎨 Common Patterns

### 1. Route Definition

**Pattern**: Define routes in `src/routes/`, map to controller methods

```javascript
// src/routes/users.js
const express = require('express');
const router = express.Router();
const userController = require('../controllers/userController');
const { protect } = require('../middleware/auth');
const { validateRequest } = require('../middleware/validate');
const { userValidation } = require('../utils/validators');

/**
 * @route   GET /api/v1/users
 * @desc    Get all users (paginated)
 * @access  Private (requires authentication)
 */
router.get(
  '/',
  protect,
  userController.getAllUsers
);

/**
 * @route   GET /api/v1/users/:id
 * @desc    Get user by ID
 * @access  Private
 */
router.get(
  '/:id',
  protect,
  userController.getUserById
);

/**
 * @route   POST /api/v1/users
 * @desc    Create new user
 * @access  Public
 */
router.post(
  '/',
  validateRequest(userValidation.createUser),
  userController.createUser
);

/**
 * @route   PUT /api/v1/users/:id
 * @desc    Update user
 * @access  Private
 */
router.put(
  '/:id',
  protect,
  validateRequest(userValidation.updateUser),
  userController.updateUser
);

/**
 * @route   DELETE /api/v1/users/:id
 * @desc    Delete user
 * @access  Private (Admin only)
 */
router.delete(
  '/:id',
  protect,
  userController.deleteUser
);

module.exports = router;
```

**Register in app.js:**
```javascript
const userRoutes = require('./routes/users');
app.use('/api/v1/users', userRoutes);
```

---

### 2. Controller Pattern

**Pattern**: Parse request → Call service → Format response

```javascript
// src/controllers/userController.js
const userService = require('../services/userService');
const { successResponse, errorResponse } = require('../utils/response');

/**
 * @desc    Get all users with pagination
 * @route   GET /api/v1/users
 * @access  Private
 */
exports.getAllUsers = async (req, res, next) => {
  try {
    // 1. Parse query parameters
    const { page = 1, limit = 10, search, sort } = req.query;
    
    // 2. Call service layer
    const result = await userService.getAllUsers({
      page: parseInt(page, 10),
      limit: parseInt(limit, 10),
      search,
      sort,
    });
    
    // 3. Format success response
    return successResponse(res, {
      data: result.users,
      pagination: {
        page: result.page,
        limit: result.limit,
        total: result.total,
        pages: result.pages,
      },
      message: 'Users retrieved successfully',
    });
  } catch (error) {
    // 4. Pass errors to error handler middleware
    next(error);
  }
};

/**
 * @desc    Get user by ID
 * @route   GET /api/v1/users/:id
 * @access  Private
 */
exports.getUserById = async (req, res, next) => {
  try {
    const { id } = req.params;
    
    const user = await userService.getUserById(id);
    
    if (!user) {
      return errorResponse(res, 'User not found', 404);
    }
    
    return successResponse(res, {
      data: user,
      message: 'User retrieved successfully',
    });
  } catch (error) {
    next(error);
  }
};

/**
 * @desc    Create new user
 * @route   POST /api/v1/users
 * @access  Public
 */
exports.createUser = async (req, res, next) => {
  try {
    const userData = req.body;
    
    const newUser = await userService.createUser(userData);
    
    return successResponse(res, {
      data: newUser,
      message: 'User created successfully',
    }, 201);
  } catch (error) {
    next(error);
  }
};

/**
 * @desc    Update user
 * @route   PUT /api/v1/users/:id
 * @access  Private
 */
exports.updateUser = async (req, res, next) => {
  try {
    const { id } = req.params;
    const updateData = req.body;
    
    const updatedUser = await userService.updateUser(id, updateData);
    
    if (!updatedUser) {
      return errorResponse(res, 'User not found', 404);
    }
    
    return successResponse(res, {
      data: updatedUser,
      message: 'User updated successfully',
    });
  } catch (error) {
    next(error);
  }
};

/**
 * @desc    Delete user
 * @route   DELETE /api/v1/users/:id
 * @access  Private
 */
exports.deleteUser = async (req, res, next) => {
  try {
    const { id } = req.params;
    
    const deletedUser = await userService.deleteUser(id);
    
    if (!deletedUser) {
      return errorResponse(res, 'User not found', 404);
    }
    
    return successResponse(res, {
      message: 'User deleted successfully',
    });
  } catch (error) {
    next(error);
  }
};
```

**Key Points:**
- ✅ Each controller method handles ONE endpoint
- ✅ Parse request data (params, query, body)
- ✅ Call service layer for business logic
- ✅ Format consistent JSON responses
- ✅ Pass errors to `next()` middleware
- ✅ Add JSDoc comments for documentation

---

### 3. Service Pattern

**Pattern**: Business logic + orchestration

```javascript
// src/services/userService.js
const userRepository = require('../repositories/userRepository');
const { AppError } = require('../utils/errors');
const logger = require('../utils/logger');
const bcrypt = require('bcryptjs');

class UserService {
  /**
   * Get all users with pagination and search
   */
  async getAllUsers({ page, limit, search, sort }) {
    try {
      const query = {};
      
      // Build search query
      if (search) {
        query.$or = [
          { name: { $regex: search, $options: 'i' } },
          { email: { $regex: search, $options: 'i' } },
        ];
      }
      
      // Calculate pagination
      const skip = (page - 1) * limit;
      
      // Fetch data
      const [users, total] = await Promise.all([
        userRepository.findAll(query, { skip, limit, sort }),
        userRepository.count(query),
      ]);
      
      return {
        users,
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      };
    } catch (error) {
      logger.error('Error in getAllUsers:', error);
      throw new AppError('Failed to fetch users', 500);
    }
  }
  
  /**
   * Get user by ID
   */
  async getUserById(userId) {
    try {
      const user = await userRepository.findById(userId);
      
      if (!user) {
        throw new AppError('User not found', 404);
      }
      
      return user;
    } catch (error) {
      logger.error(`Error in getUserById (${userId}):`, error);
      throw error;
    }
  }
  
  /**
   * Create new user
   */
  async createUser(userData) {
    try {
      // Check if user already exists
      const existingUser = await userRepository.findByEmail(userData.email);
      
      if (existingUser) {
        throw new AppError('User with this email already exists', 409);
      }
      
      // Hash password
      if (userData.password) {
        userData.password = await bcrypt.hash(userData.password, 12);
      }
      
      // Create user
      const newUser = await userRepository.create(userData);
      
      // Remove password from response
      newUser.password = undefined;
      
      logger.info(`User created: ${newUser.email}`);
      
      return newUser;
    } catch (error) {
      logger.error('Error in createUser:', error);
      throw error;
    }
  }
  
  /**
   * Update user
   */
  async updateUser(userId, updateData) {
    try {
      // Get existing user
      const user = await userRepository.findById(userId);
      
      if (!user) {
        throw new AppError('User not found', 404);
      }
      
      // Check email uniqueness if changing
      if (updateData.email && updateData.email !== user.email) {
        const emailExists = await userRepository.findByEmail(updateData.email);
        if (emailExists) {
          throw new AppError('Email already in use', 409);
        }
      }
      
      // Hash password if updating
      if (updateData.password) {
        updateData.password = await bcrypt.hash(updateData.password, 12);
      }
      
      // Update user
      const updatedUser = await userRepository.update(userId, updateData);
      
      // Remove password from response
      updatedUser.password = undefined;
      
      logger.info(`User updated: ${userId}`);
      
      return updatedUser;
    } catch (error) {
      logger.error(`Error in updateUser (${userId}):`, error);
      throw error;
    }
  }
  
  /**
   * Delete user
   */
  async deleteUser(userId) {
    try {
      const user = await userRepository.findById(userId);
      
      if (!user) {
        throw new AppError('User not found', 404);
      }
      
      await userRepository.delete(userId);
      
      logger.info(`User deleted: ${userId}`);
      
      return user;
    } catch (error) {
      logger.error(`Error in deleteUser (${userId}):`, error);
      throw error;
    }
  }
}

module.exports = new UserService();
```

**Key Points:**
- ✅ Implement business rules (validation, authorization)
- ✅ Orchestrate multiple repository calls
- ✅ Handle transactions if needed
- ✅ Throw meaningful errors (`AppError`)
- ✅ Log important events
- ✅ Export singleton instance

---

### 4. Repository Pattern

**Pattern**: Abstract database operations

```javascript
// src/repositories/userRepository.js
const User = require('../models/User');
const { AppError } = require('../utils/errors');

class UserRepository {
  /**
   * Find all users with options
   */
  async findAll(query = {}, options = {}) {
    try {
      const { skip = 0, limit = 10, sort = '-createdAt' } = options;
      
      return await User.find(query)
        .select('-password')
        .skip(skip)
        .limit(limit)
        .sort(sort)
        .lean();
    } catch (error) {
      throw new AppError('Database query failed', 500);
    }
  }
  
  /**
   * Find user by ID
   */
  async findById(userId) {
    try {
      return await User.findById(userId).select('-password').lean();
    } catch (error) {
      throw new AppError('Database query failed', 500);
    }
  }
  
  /**
   * Find user by email
   */
  async findByEmail(email) {
    try {
      return await User.findOne({ email }).lean();
    } catch (error) {
      throw new AppError('Database query failed', 500);
    }
  }
  
  /**
   * Create new user
   */
  async create(userData) {
    try {
      const user = new User(userData);
      await user.save();
      return user.toObject();
    } catch (error) {
      if (error.code === 11000) {
        throw new AppError('Duplicate key error', 409);
      }
      throw new AppError('Failed to create user', 500);
    }
  }
  
  /**
   * Update user
   */
  async update(userId, updateData) {
    try {
      const user = await User.findByIdAndUpdate(
        userId,
        { $set: updateData },
        { new: true, runValidators: true }
      ).select('-password');
      
      return user ? user.toObject() : null;
    } catch (error) {
      throw new AppError('Failed to update user', 500);
    }
  }
  
  /**
   * Delete user
   */
  async delete(userId) {
    try {
      return await User.findByIdAndDelete(userId);
    } catch (error) {
      throw new AppError('Failed to delete user', 500);
    }
  }
  
  /**
   * Count documents
   */
  async count(query = {}) {
    try {
      return await User.countDocuments(query);
    } catch (error) {
      throw new AppError('Database query failed', 500);
    }
  }
}

module.exports = new UserRepository();
```

**Key Points:**
- ✅ One class per model
- ✅ Abstract Mongoose operations
- ✅ Use `.lean()` for performance
- ✅ Handle database errors
- ✅ Export singleton instance

---

### 5. Model Pattern

**Pattern**: Mongoose schema with validation

```javascript
// src/models/User.js
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: [true, 'Name is required'],
      trim: true,
      minlength: [2, 'Name must be at least 2 characters'],
      maxlength: [50, 'Name cannot exceed 50 characters'],
    },
    email: {
      type: String,
      required: [true, 'Email is required'],
      unique: true,
      lowercase: true,
      trim: true,
      match: [
        /^\w+([.-]?\w+)*@\w+([.-]?\w+)*(\.\w{2,3})+$/,
        'Please provide a valid email',
      ],
    },
    password: {
      type: String,
      required: [true, 'Password is required'],
      minlength: [6, 'Password must be at least 6 characters'],
      select: false, // Don't return password by default
    },
    role: {
      type: String,
      enum: ['user', 'admin', 'moderator'],
      default: 'user',
    },
    isActive: {
      type: Boolean,
      default: true,
    },
    lastLoginAt: {
      type: Date,
    },
    avatar: {
      type: String,
    },
    phoneNumber: {
      type: String,
      trim: true,
    },
    address: {
      street: String,
      city: String,
      country: String,
      zipCode: String,
    },
  },
  {
    timestamps: true, // Adds createdAt and updatedAt
    toJSON: { virtuals: true },
    toObject: { virtuals: true },
  }
);

// Indexes for performance
userSchema.index({ email: 1 });
userSchema.index({ createdAt: -1 });
userSchema.index({ name: 'text', email: 'text' }); // Text search

// Virtual field example
userSchema.virtual('fullAddress').get(function() {
  if (!this.address) return null;
  return `${this.address.street}, ${this.address.city}, ${this.address.country}`;
});

// Instance method: Compare password
userSchema.methods.comparePassword = async function(candidatePassword) {
  return await bcrypt.compare(candidatePassword, this.password);
};

// Instance method: Update last login
userSchema.methods.updateLastLogin = async function() {
  this.lastLoginAt = Date.now();
  await this.save();
};

// Static method: Find active users
userSchema.statics.findActiveUsers = function() {
  return this.find({ isActive: true });
};

// Pre-save middleware: Hash password
userSchema.pre('save', async function(next) {
  // Only hash if password is modified
  if (!this.isModified('password')) return next();
  
  // Hash password
  this.password = await bcrypt.hash(this.password, 12);
  next();
});

// Pre-save middleware: Update timestamp
userSchema.pre('save', function(next) {
  if (!this.isNew) {
    this.updatedAt = Date.now();
  }
  next();
});

const User = mongoose.model('User', userSchema);

module.exports = User;
```

**Key Points:**
- ✅ Define schema with validation rules
- ✅ Use appropriate data types
- ✅ Add indexes for frequently queried fields
- ✅ Use `select: false` for sensitive fields
- ✅ Add instance methods for model-specific logic
- ✅ Add static methods for query helpers
- ✅ Use pre/post hooks for side effects
- ✅ Enable timestamps (`createdAt`, `updatedAt`)

---

## 🚀 Feature Development

### Adding a New Feature (Example: Products)

#### Step 1: Create Model

```javascript
// src/models/Product.js
const mongoose = require('mongoose');

const productSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: true,
      trim: true,
    },
    description: {
      type: String,
      required: true,
    },
    price: {
      type: Number,
      required: true,
      min: 0,
    },
    category: {
      type: String,
      enum: ['electronics', 'clothing', 'food', 'other'],
      required: true,
    },
    stock: {
      type: Number,
      default: 0,
      min: 0,
    },
    images: [String],
    isActive: {
      type: Boolean,
      default: true,
    },
    createdBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
  },
  { timestamps: true }
);

productSchema.index({ name: 'text', description: 'text' });
productSchema.index({ category: 1, price: 1 });

module.exports = mongoose.model('Product', productSchema);
```

#### Step 2: Create Repository

```javascript
// src/repositories/productRepository.js
const Product = require('../models/Product');
const { AppError } = require('../utils/errors');

class ProductRepository {
  async findAll(query = {}, options = {}) {
    const { skip = 0, limit = 10, sort = '-createdAt' } = options;
    return await Product.find(query)
      .skip(skip)
      .limit(limit)
      .sort(sort)
      .populate('createdBy', 'name email')
      .lean();
  }
  
  async findById(productId) {
    return await Product.findById(productId)
      .populate('createdBy', 'name email')
      .lean();
  }
  
  async create(productData) {
    const product = new Product(productData);
    await product.save();
    return product.toObject();
  }
  
  async update(productId, updateData) {
    return await Product.findByIdAndUpdate(
      productId,
      { $set: updateData },
      { new: true, runValidators: true }
    ).lean();
  }
  
  async delete(productId) {
    return await Product.findByIdAndDelete(productId);
  }
  
  async count(query = {}) {
    return await Product.countDocuments(query);
  }
}

module.exports = new ProductRepository();
```

#### Step 3: Create Service

```javascript
// src/services/productService.js
const productRepository = require('../repositories/productRepository');
const { AppError } = require('../utils/errors');
const logger = require('../utils/logger');

class ProductService {
  async getAllProducts({ page, limit, search, category, minPrice, maxPrice }) {
    try {
      const query = { isActive: true };
      
      if (search) {
        query.$text = { $search: search };
      }
      
      if (category) {
        query.category = category;
      }
      
      if (minPrice || maxPrice) {
        query.price = {};
        if (minPrice) query.price.$gte = minPrice;
        if (maxPrice) query.price.$lte = maxPrice;
      }
      
      const skip = (page - 1) * limit;
      
      const [products, total] = await Promise.all([
        productRepository.findAll(query, { skip, limit }),
        productRepository.count(query),
      ]);
      
      return {
        products,
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      };
    } catch (error) {
      logger.error('Error in getAllProducts:', error);
      throw new AppError('Failed to fetch products', 500);
    }
  }
  
  async getProductById(productId) {
    const product = await productRepository.findById(productId);
    if (!product) {
      throw new AppError('Product not found', 404);
    }
    return product;
  }
  
  async createProduct(productData, userId) {
    try {
      productData.createdBy = userId;
      const product = await productRepository.create(productData);
      logger.info(`Product created: ${product._id}`);
      return product;
    } catch (error) {
      logger.error('Error in createProduct:', error);
      throw new AppError('Failed to create product', 500);
    }
  }
  
  async updateProduct(productId, updateData, userId) {
    const product = await productRepository.findById(productId);
    
    if (!product) {
      throw new AppError('Product not found', 404);
    }
    
    // Check ownership
    if (product.createdBy.toString() !== userId.toString()) {
      throw new AppError('Not authorized to update this product', 403);
    }
    
    const updated = await productRepository.update(productId, updateData);
    logger.info(`Product updated: ${productId}`);
    return updated;
  }
  
  async deleteProduct(productId, userId) {
    const product = await productRepository.findById(productId);
    
    if (!product) {
      throw new AppError('Product not found', 404);
    }
    
    // Check ownership
    if (product.createdBy.toString() !== userId.toString()) {
      throw new AppError('Not authorized to delete this product', 403);
    }
    
    await productRepository.delete(productId);
    logger.info(`Product deleted: ${productId}`);
    return product;
  }
}

module.exports = new ProductService();
```

#### Step 4: Create Controller

```javascript
// src/controllers/productController.js
const productService = require('../services/productService');
const { successResponse, errorResponse } = require('../utils/response');

exports.getAllProducts = async (req, res, next) => {
  try {
    const { page = 1, limit = 10, search, category, minPrice, maxPrice } = req.query;
    
    const result = await productService.getAllProducts({
      page: parseInt(page, 10),
      limit: parseInt(limit, 10),
      search,
      category,
      minPrice: minPrice ? parseFloat(minPrice) : undefined,
      maxPrice: maxPrice ? parseFloat(maxPrice) : undefined,
    });
    
    return successResponse(res, {
      data: result.products,
      pagination: {
        page: result.page,
        limit: result.limit,
        total: result.total,
        pages: result.pages,
      },
    });
  } catch (error) {
    next(error);
  }
};

exports.getProductById = async (req, res, next) => {
  try {
    const { id } = req.params;
    const product = await productService.getProductById(id);
    return successResponse(res, { data: product });
  } catch (error) {
    next(error);
  }
};

exports.createProduct = async (req, res, next) => {
  try {
    const productData = req.body;
    const userId = req.user.id; // From auth middleware
    
    const product = await productService.createProduct(productData, userId);
    return successResponse(res, { data: product }, 201);
  } catch (error) {
    next(error);
  }
};

exports.updateProduct = async (req, res, next) => {
  try {
    const { id } = req.params;
    const updateData = req.body;
    const userId = req.user.id;
    
    const product = await productService.updateProduct(id, updateData, userId);
    return successResponse(res, { data: product });
  } catch (error) {
    next(error);
  }
};

exports.deleteProduct = async (req, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user.id;
    
    await productService.deleteProduct(id, userId);
    return successResponse(res, { message: 'Product deleted successfully' });
  } catch (error) {
    next(error);
  }
};
```

#### Step 5: Create Routes

```javascript
// src/routes/products.js
const express = require('express');
const router = express.Router();
const productController = require('../controllers/productController');
const { protect } = require('../middleware/auth');
const { validateRequest } = require('../middleware/validate');
const { productValidation } = require('../utils/validators');

// Public routes
router.get('/', productController.getAllProducts);
router.get('/:id', productController.getProductById);

// Protected routes
router.post(
  '/',
  protect,
  validateRequest(productValidation.createProduct),
  productController.createProduct
);

router.put(
  '/:id',
  protect,
  validateRequest(productValidation.updateProduct),
  productController.updateProduct
);

router.delete(
  '/:id',
  protect,
  productController.deleteProduct
);

module.exports = router;
```

#### Step 6: Add Validation Schema

```javascript
// src/utils/validators.js (add to existing file)
const Joi = require('joi');

exports.productValidation = {
  createProduct: Joi.object({
    name: Joi.string().min(3).max(100).required(),
    description: Joi.string().min(10).max(500).required(),
    price: Joi.number().min(0).required(),
    category: Joi.string().valid('electronics', 'clothing', 'food', 'other').required(),
    stock: Joi.number().integer().min(0).default(0),
    images: Joi.array().items(Joi.string().uri()),
  }),
  
  updateProduct: Joi.object({
    name: Joi.string().min(3).max(100),
    description: Joi.string().min(10).max(500),
    price: Joi.number().min(0),
    category: Joi.string().valid('electronics', 'clothing', 'food', 'other'),
    stock: Joi.number().integer().min(0),
    images: Joi.array().items(Joi.string().uri()),
    isActive: Joi.boolean(),
  }).min(1), // At least one field required
};
```

#### Step 7: Register Routes in app.js

```javascript
// src/app.js (add to existing routes)
const productRoutes = require('./routes/products');
app.use('/api/v1/products', productRoutes);
```

#### Step 8: Create Tests

```javascript
// src/tests/integration/product.test.js
const request = require('supertest');
const app = require('../../app');
const Product = require('../../models/Product');
const User = require('../../models/User');

describe('Product API', () => {
  let authToken;
  let userId;
  
  beforeAll(async () => {
    // Create test user and get auth token
    const user = await User.create({
      name: 'Test User',
      email: 'test@example.com',
      password: 'password123',
    });
    userId = user._id;
    
    // Get auth token (implement based on your auth system)
    authToken = 'your-jwt-token';
  });
  
  afterAll(async () => {
    await Product.deleteMany({});
    await User.deleteMany({});
  });
  
  describe('POST /api/v1/products', () => {
    it('should create a new product', async () => {
      const response = await request(app)
        .post('/api/v1/products')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Test Product',
          description: 'Test product description',
          price: 99.99,
          category: 'electronics',
          stock: 10,
        })
        .expect(201);
      
      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty('_id');
      expect(response.body.data.name).toBe('Test Product');
    });
    
    it('should return validation error for invalid data', async () => {
      const response = await request(app)
        .post('/api/v1/products')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'T', // Too short
          description: 'Short',
          price: -10, // Negative
        })
        .expect(400);
      
      expect(response.body.success).toBe(false);
    });
  });
  
  describe('GET /api/v1/products', () => {
    it('should get all products', async () => {
      const response = await request(app)
        .get('/api/v1/products')
        .expect(200);
      
      expect(response.body.success).toBe(true);
      expect(Array.isArray(response.body.data)).toBe(true);
    });
  });
});
```

---

## 🧪 Testing Guidelines

### Test Structure

```
src/tests/
├── unit/
│   ├── services/
│   │   └── userService.test.js
│   ├── repositories/
│   │   └── userRepository.test.js
│   └── utils/
│       └── validators.test.js
└── integration/
    ├── auth.test.js
    ├── users.test.js
    └── products.test.js
```

### Unit Test Example

```javascript
// src/tests/unit/services/userService.test.js
const userService = require('../../../services/userService');
const userRepository = require('../../../repositories/userRepository');

jest.mock('../../../repositories/userRepository');

describe('UserService', () => {
  describe('getUserById', () => {
    it('should return user when found', async () => {
      const mockUser = {
        _id: '123',
        name: 'John Doe',
        email: 'john@example.com',
      };
      
      userRepository.findById.mockResolvedValue(mockUser);
      
      const result = await userService.getUserById('123');
      
      expect(result).toEqual(mockUser);
      expect(userRepository.findById).toHaveBeenCalledWith('123');
    });
    
    it('should throw error when user not found', async () => {
      userRepository.findById.mockResolvedValue(null);
      
      await expect(userService.getUserById('999'))
        .rejects
        .toThrow('User not found');
    });
  });
});
```

### Integration Test Example

```javascript
// src/tests/integration/auth.test.js
const request = require('supertest');
const app = require('../../app');
const User = require('../../models/User');

describe('Auth API', () => {
  beforeEach(async () => {
    await User.deleteMany({});
  });
  
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
      expect(response.body.data.user.email).toBe('john@example.com');
    });
    
    it('should return error for duplicate email', async () => {
      await User.create({
        name: 'Existing User',
        email: 'john@example.com',
        password: 'password123',
      });
      
      const response = await request(app)
        .post('/api/v1/auth/register')
        .send({
          name: 'John Doe',
          email: 'john@example.com',
          password: 'password123',
        })
        .expect(409);
      
      expect(response.body.success).toBe(false);
    });
  });
  
  describe('POST /api/v1/auth/login', () => {
    beforeEach(async () => {
      await request(app)
        .post('/api/v1/auth/register')
        .send({
          name: 'John Doe',
          email: 'john@example.com',
          password: 'password123',
        });
    });
    
    it('should login with valid credentials', async () => {
      const response = await request(app)
        .post('/api/v1/auth/login')
        .send({
          email: 'john@example.com',
          password: 'password123',
        })
        .expect(200);
      
      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty('token');
    });
    
    it('should reject invalid credentials', async () => {
      const response = await request(app)
        .post('/api/v1/auth/login')
        .send({
          email: 'john@example.com',
          password: 'wrongpassword',
        })
        .expect(401);
      
      expect(response.body.success).toBe(false);
    });
  });
});
```

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- auth.test.js

# Run integration tests only
npm test -- --testPathPattern=integration
```

---

## ⚙️ Environment Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NODE_ENV` | Environment mode | `development`, `production`, `test` |
| `PORT` | Server port | `3000` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017/myapp` |
| `JWT_SECRET` | JWT signing secret | `your-super-secret-key` |
| `JWT_EXPIRE` | JWT expiration time | `1h`, `7d`, `30d` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BCRYPT_ROUNDS` | Password hashing rounds | `12` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `LOG_LEVEL` | Logging level | `info` |
| `RATE_LIMIT_WINDOW` | Rate limit window (ms) | `900000` (15 min) |
| `RATE_LIMIT_MAX` | Max requests per window | `100` |

### Loading Configuration

```javascript
// Always load config at the top of your modules
const config = require('./config');

// Access config values
console.log(config.PORT);
console.log(config.MONGODB_URI);
console.log(config.JWT_SECRET);
```

---

## 🔒 Security Practices

### 1. Authentication Middleware

```javascript
// src/middleware/auth.js
const jwt = require('jsonwebtoken');
const config = require('../config');
const { AppError } = require('../utils/errors');
const User = require('../models/User');

exports.protect = async (req, res, next) => {
  try {
    let token;
    
    // Get token from header
    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
      token = req.headers.authorization.split(' ')[1];
    }
    
    if (!token) {
      throw new AppError('Not authorized to access this route', 401);
    }
    
    // Verify token
    const decoded = jwt.verify(token, config.JWT_SECRET);
    
    // Get user from token
    const user = await User.findById(decoded.id);
    
    if (!user) {
      throw new AppError('User not found', 401);
    }
    
    // Attach user to request
    req.user = user;
    next();
  } catch (error) {
    next(new AppError('Not authorized to access this route', 401));
  }
};

exports.authorize = (...roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return next(
        new AppError(`Role ${req.user.role} is not authorized to access this route`, 403)
      );
    }
    next();
  };
};
```

### 2. Input Validation

```javascript
// Always validate user input
const { validateRequest } = require('../middleware/validate');
const { userValidation } = require('../utils/validators');

router.post(
  '/users',
  validateRequest(userValidation.createUser), // Validate before controller
  userController.createUser
);
```

### 3. Password Security

```javascript
// Hash passwords with bcrypt (12+ rounds)
const bcrypt = require('bcryptjs');
const hashedPassword = await bcrypt.hash(password, 12);

// Compare passwords
const isMatch = await bcrypt.compare(candidatePassword, user.password);
```

### 4. SQL Injection Prevention

- ✅ Use Mongoose (NoSQL) - built-in protection
- ✅ Validate all inputs with Joi schemas
- ✅ Never use `eval()` or `Function()` with user input

### 5. XSS Prevention

- ✅ Helmet middleware (already configured)
- ✅ Sanitize HTML inputs
- ✅ Set appropriate Content-Type headers

---

## ❌ Error Handling

### Custom Error Class

```javascript
// src/utils/errors.js
class AppError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
    this.status = `${statusCode}`.startsWith('4') ? 'fail' : 'error';
    this.isOperational = true;
    
    Error.captureStackTrace(this, this.constructor);
  }
}

module.exports = { AppError };
```

### Error Handler Middleware

```javascript
// src/middleware/errorHandler.js
const logger = require('../utils/logger');

const errorHandler = (err, req, res, next) => {
  let error = { ...err };
  error.message = err.message;
  
  // Log error
  logger.error(err);
  
  // Mongoose bad ObjectId
  if (err.name === 'CastError') {
    error.message = 'Resource not found';
    error.statusCode = 404;
  }
  
  // Mongoose duplicate key
  if (err.code === 11000) {
    error.message = 'Duplicate field value entered';
    error.statusCode = 409;
  }
  
  // Mongoose validation error
  if (err.name === 'ValidationError') {
    const messages = Object.values(err.errors).map(val => val.message);
    error.message = messages.join(', ');
    error.statusCode = 400;
  }
  
  // JWT errors
  if (err.name === 'JsonWebTokenError') {
    error.message = 'Invalid token';
    error.statusCode = 401;
  }
  
  if (err.name === 'TokenExpiredError') {
    error.message = 'Token expired';
    error.statusCode = 401;
  }
  
  res.status(error.statusCode || 500).json({
    success: false,
    error: error.message || 'Server Error',
    statusCode: error.statusCode || 500,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  });
};

module.exports = errorHandler;
```

### Throwing Errors

```javascript
// In services
const { AppError } = require('../utils/errors');

if (!user) {
  throw new AppError('User not found', 404);
}

if (user.email === existingUser.email) {
  throw new AppError('Email already in use', 409);
}

if (!user.isActive) {
  throw new AppError('Account is deactivated', 403);
}
```

---

## 📝 API Response Format

### Success Response

```javascript
// src/utils/response.js
exports.successResponse = (res, data, statusCode = 200) => {
  return res.status(statusCode).json({
    success: true,
    statusCode,
    data: data.data || data,
    message: data.message || 'Success',
    ...(data.pagination && { pagination: data.pagination }),
  });
};
```

**Example:**
```json
{
  "success": true,
  "statusCode": 200,
  "data": {
    "_id": "123",
    "name": "John Doe",
    "email": "john@example.com"
  },
  "message": "User retrieved successfully"
}
```

### Error Response

```javascript
exports.errorResponse = (res, message, statusCode = 500) => {
  return res.status(statusCode).json({
    success: false,
    statusCode,
    error: message,
  });
};
```

**Example:**
```json
{
  "success": false,
  "statusCode": 404,
  "error": "User not found"
}
```

### Pagination Response

```json
{
  "success": true,
  "statusCode": 200,
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 100,
    "pages": 10
  },
  "message": "Users retrieved successfully"
}
```

---

## 🎬 Quick Start Commands

```bash
# Install dependencies
npm install

# Run development server (with hot reload)
npm run dev

# Run production server
npm start

# Run tests
npm test
npm run test:coverage

# Lint and format code
npm run lint
npm run lint:fix
npm run format

# Docker commands
npm run docker:build
npm run docker:run
```

---

## 🚨 Common Issues & Solutions

### Issue 1: MongoDB Connection Failed

**Error:** `MongooseServerSelectionError: connect ECONNREFUSED`

**Solution:**
1. Check if MongoDB is running: `systemctl status mongod` (Linux) or check Docker container
2. Verify `MONGODB_URI` in `.env`
3. Ensure MongoDB is accessible from your network

### Issue 2: JWT Token Invalid

**Error:** `JsonWebTokenError: invalid token`

**Solution:**
1. Check `JWT_SECRET` matches between token generation and verification
2. Verify token format: `Bearer <token>`
3. Check token expiration time

### Issue 3: Validation Errors

**Error:** `ValidationError: Path email is required`

**Solution:**
1. Check request body matches validation schema
2. Verify Content-Type header is `application/json`
3. Use `validateRequest` middleware

### Issue 4: CORS Errors

**Error:** `Access-Control-Allow-Origin header`

**Solution:**
1. Add frontend URL to `CORS_ORIGINS` in `.env`
2. Verify CORS middleware is configured correctly
3. Check if credentials are needed: `credentials: true`

---

## 📚 Additional Resources

- **Express.js Docs**: https://expressjs.com/
- **Mongoose Docs**: https://mongoosejs.com/docs/
- **JWT Best Practices**: https://jwt.io/introduction
- **Jest Docs**: https://jestjs.io/docs/getting-started
- **ESLint Rules**: https://eslint.org/docs/rules/

---

## 🤖 Tips for AI Agents

### DO's ✅

1. **Follow the layered architecture** - Always separate concerns (routes → controllers → services → repositories)
2. **Use async/await** - Never use callbacks or raw promises
3. **Validate all inputs** - Use Joi schemas and express-validator
4. **Handle errors properly** - Throw `AppError` with meaningful messages
5. **Write tests** - Add tests for new features (minimum integration tests)
6. **Log important events** - Use Winston logger, not `console.log`
7. **Use environment variables** - Never hardcode sensitive data
8. **Follow naming conventions** - camelCase for files, PascalCase for models
9. **Add JSDoc comments** - Document controller methods and complex functions
10. **Use TypeScript-style comments** - Help IDEs with autocomplete

### DON'Ts ❌

1. **Don't mix business logic in controllers** - Keep controllers thin
2. **Don't query database directly in controllers** - Use service layer
3. **Don't expose sensitive data** - Use `.select('-password')` for queries
4. **Don't use `var`** - Always use `const` or `let`
5. **Don't skip validation** - Validate all user inputs
6. **Don't hardcode values** - Use config/constants
7. **Don't forget error handling** - Wrap async functions in try-catch
8. **Don't commit `.env`** - Only commit `.env.example`
9. **Don't use `console.log`** - Use Winston logger
10. **Don't skip tests** - Test critical paths

---

## 🎯 Agent Task Checklist

When implementing a new feature, follow this checklist:

- [ ] Create Mongoose model with validation
- [ ] Add indexes for frequently queried fields
- [ ] Create repository class with CRUD methods
- [ ] Implement service class with business logic
- [ ] Create controller with request/response handling
- [ ] Define routes with appropriate HTTP methods
- [ ] Add validation schemas (Joi)
- [ ] Implement authentication/authorization if needed
- [ ] Write integration tests
- [ ] Add JSDoc comments
- [ ] Update `.env.example` if new env vars added
- [ ] Test with Postman/curl
- [ ] Run linter and fix issues
- [ ] Check test coverage (>80%)

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Maintained By**: VibeSDLC AI Agent Service

const userRepository = require('../repositories/userRepository');
const AppError = require('../utils/AppError');
const jwt = require('jsonwebtoken');
const config = require('../config');

class AuthService {
  /**
   * Registers a new user.
   * @param {Object} userData - The user registration data.
   * @param {string} userData.email - The user's email.
   * @param {string} userData.password - The user's password (plain text).
   * @returns {Promise<Object>} The created user (lean object, without password hash) and JWT token.
   * @throws {AppError} If registration fails (duplicate email, validation, etc).
   */
  async registerUser(userData) {
    const { email, password } = userData;
    if (!email || !password) {
      throw new AppError('Email and password are required', 400);
    }
    try {
      // The User model expects password_hash, not password
      const createdUser = await userRepository.create({
        email,
        password_hash: password
      });
      // Remove sensitive fields before returning
      const userObj = createdUser.toObject ? createdUser.toObject() : createdUser;
      delete userObj.password_hash;
      // Generate JWT token
      const token = jwt.sign(
        { id: userObj._id, email: userObj.email },
        config.JWT_SECRET,
        { expiresIn: config.JWT_EXPIRE }
      );
      return { user: userObj, token };
    } catch (err) {
      if (err.code === 'DUPLICATE_EMAIL') {
        throw new AppError('Email already in use', 409);
      }
      if (err.name === 'ValidationError') {
        throw new AppError(err.message || 'Validation failed', 400);
      }
      throw new AppError(err.message || 'Registration failed', 500);
    }
  }
}

module.exports = new AuthService();

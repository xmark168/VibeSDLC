const userRepository = require('../repositories/userRepository');

const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const config = require('../config');

class AuthService {
  /**
   * Register a new user
   * @param {Object} userData - { email, password_hash }
   * @returns {Promise<Object>} Created user document
   * @throws {Error} If email already exists
   */
  async registerUser(userData) {
    // Check for duplicate email
    const existingUser = await userRepository.findByEmail(userData.email);
    if (existingUser) {
      const error = new Error('Email already exists');
      error.statusCode = 409;
      throw error;
    }
    // Create user
    return await userRepository.create(userData);
  }

  /**
   * Login user: verify credentials and generate JWT
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{ user: Object, token: string }>} Authenticated user and JWT
   * @throws {Error} If credentials are invalid
   */
  async loginUser(email, password) {
    const user = await userRepository.findByEmail(email);
    if (!user) {
      const error = new Error('Invalid email or password');
      error.statusCode = 401;
      throw error;
    }
    const validPassword = await bcrypt.compare(password, user.password_hash);
    if (!validPassword) {
      const error = new Error('Invalid email or password');
      error.statusCode = 401;
      throw error;
    }
    // Generate JWT
    const payload = {
      id: user._id,
      email: user.email,
      is_verified: user.is_verified
    };
    const token = jwt.sign(payload, config.JWT_SECRET, {
      expiresIn: config.JWT_EXPIRE
    });
    return { user, token };
  }
}

module.exports = new AuthService();

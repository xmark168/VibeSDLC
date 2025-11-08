const User = require('../models/User');

class UserRepository {
  /**
   * Find a user by email
   * @param {string} email
   * @returns {Promise<Object|null>} User document or null
   */
  async findByEmail(email) {
    return await User.findOne({ email }).lean();
  }

  /**
   * Find a user by ID
   * @param {string} id
   * @returns {Promise<Object|null>} User document or null
   */
  async findById(id) {
    return await User.findById(id).lean();
  }

  /**
   * Update user verification status
   * @param {string} id
   * @param {boolean} isVerified
   * @returns {Promise<Object|null>} Updated user document or null
   */
  async updateVerificationStatus(id, isVerified) {
    return await User.findByIdAndUpdate(
      id,
      { is_verified: isVerified },
      { new: true }
    ).lean();
  }

  /**
   * Create a new user and handle duplicate email errors
   * @param {Object} userData
   * @returns {Promise<Object>} Created user document
   * @throws {Error} Duplicate email error
   */
  async create(userData) {
    try {
      const user = new User(userData);
      await user.save();
      return user.toObject();
    } catch (err) {
      // MongoDB duplicate key error code is 11000
      if (err.code === 11000 && err.keyPattern && err.keyPattern.email) {
        const error = new Error('Email already exists');
        error.statusCode = 409;
        throw error;
      }
      throw err;
    }
  }
}

module.exports = new UserRepository();

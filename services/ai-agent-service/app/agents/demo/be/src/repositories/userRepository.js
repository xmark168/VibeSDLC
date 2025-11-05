const User = require('../models/User');

class UserRepository {
  /**
   * Create a new user
   * @param {Object} userData - The user data
   * @returns {Promise<User>} The created user
   * @throws {Error} If email already exists
   */
  async create(userData) {
    // Check for duplicate email
    const existingUser = await User.findOne({ email: userData.email });
    if (existingUser) {
      const error = new Error('Email already exists');
      error.code = 'DUPLICATE_EMAIL';
      throw error;
    }
    const user = new User(userData);
    return await user.save();
  }

  /**
   * Find a user by email
   * @param {string} email - The user's email
   * @returns {Promise<User|null>} The found user or null
   */
  async findByEmail(email) {
    return await User.findOne({ email }).lean();
  }
}

module.exports = new UserRepository();
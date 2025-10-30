const User = require('../models/User');

class UserRepository {
  async findByEmail(email) {
    return await User.findOne({ email }).lean();
  }

  async findById(id) {
    return await User.findById(id).lean();
  }

  async create(userData) {
    // Check for duplicate email
    const existingUser = await this.findByEmail(userData.email);
    if (existingUser) {
      const error = new Error('Email already in use');
      error.code = 'DUPLICATE_EMAIL';
      throw error;
    }
    const user = new User(userData);
    return await user.save();
  }
}

module.exports = new UserRepository();

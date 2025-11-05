const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const config = require('../config');

const userSchema = new mongoose.Schema({
  email: {
    type: String,
    required: true,
    unique: true,
    lowercase: true,
    trim: true
  },
  password_hash: {
    type: String,
    required: true
  }
}, {
  timestamps: true
});

userSchema.index({ email: 1 }, { unique: true });

userSchema.pre('save', async function(next) {
  if (!this.isModified('password_hash')) return next();
  try {
    const salt = await bcrypt.genSalt(config.BCRYPT_ROUNDS);
    this.password_hash = await bcrypt.hash(this.password_hash, salt);
    next();
  } catch (err) {
    next(err);
  }
});

const User = mongoose.model('User', userSchema);

module.exports = User;

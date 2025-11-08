const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
  email: {
    type: String,
    required: true,
    unique: true,
    trim: true,
    lowercase: true,
  },
  password_hash: {
    type: String,
    required: true,
  },
  is_verified: {
    type: Boolean,
    default: false,
  }
}, {
  timestamps: true
});

userSchema.pre('save', async function (next) {
  if (!this.isModified('password_hash')) return next();
  try {
    const salt = await bcrypt.genSalt(10);
    this.password_hash = await bcrypt.hash(this.password_hash, salt);
    next();
  } catch (err) {
    next(err);
  }
});

const User = mongoose.model('User', userSchema);

module.exports = User;
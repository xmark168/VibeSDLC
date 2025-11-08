const mongoose = require('mongoose');
const User = require('../models/User');
const userRepository = require('../repositories/userRepository');
const connectDB = require('../db/mongoose');

describe('UserRepository', () => {
  beforeAll(async () => {
    process.env.MONGODB_URI = process.env.MONGODB_URI_TEST || 'mongodb://localhost:27017/vibesdlc_test';
    await connectDB();
    await User.deleteMany({});
  });

  afterAll(async () => {
    await User.deleteMany({});
    await mongoose.connection.close();
  });

  afterEach(async () => {
    await User.deleteMany({});
  });

  describe('create', () => {
    it('should create a new user', async () => {
      const userData = {
        email: 'test@example.com',
        password_hash: 'password123',
      };
      const user = await userRepository.create(userData);
      expect(user).toHaveProperty('_id');
      expect(user.email).toBe(userData.email);
      expect(user.is_verified).toBe(false);
      expect(user).not.toHaveProperty('password');
    });

    it('should throw error for duplicate email', async () => {
      const userData = {
        email: 'duplicate@example.com',
        password_hash: 'password123',
      };
      await userRepository.create(userData);
      await expect(userRepository.create(userData)).rejects.toThrow('Email already exists');
    });
  });

  describe('findByEmail', () => {
    it('should find a user by email', async () => {
      const userData = {
        email: 'findme@example.com',
        password_hash: 'password123',
      };
      await userRepository.create(userData);
      const found = await userRepository.findByEmail(userData.email);
      expect(found).not.toBeNull();
      expect(found.email).toBe(userData.email);
    });

    it('should return null if user not found', async () => {
      const found = await userRepository.findByEmail('notfound@example.com');
      expect(found).toBeNull();
    });
  });

  describe('findById', () => {
    it('should find a user by id', async () => {
      const userData = {
        email: 'byid@example.com',
        password_hash: 'password123',
      };
      const created = await userRepository.create(userData);
      const found = await userRepository.findById(created._id);
      expect(found).not.toBeNull();
      expect(found.email).toBe(userData.email);
    });

    it('should return null if user not found', async () => {
      const fakeId = new mongoose.Types.ObjectId();
      const found = await userRepository.findById(fakeId);
      expect(found).toBeNull();
    });
  });
});

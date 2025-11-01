const mongoose = require('mongoose');
const User = require('../models/User');
const userRepository = require('../repositories/userRepository');

describe('UserRepository', () => {
  beforeAll(async () => {
    await mongoose.connect('mongodb://localhost:27017/vibesdlc_test', {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });
  });

  afterAll(async () => {
    await mongoose.connection.db.dropDatabase();
    await mongoose.disconnect();
  });

  afterEach(async () => {
    await User.deleteMany({});
  });

  describe('findByEmail', () => {
    it('should return user when email exists', async () => {
      const user = await User.create({
        email: 'testuser@example.com',
        password_hash: 'password123',
      });
      const found = await userRepository.findByEmail('testuser@example.com');
      expect(found).not.toBeNull();
      expect(found.email).toBe('testuser@example.com');
    });

    it('should return null when email does not exist', async () => {
      const found = await userRepository.findByEmail('notfound@example.com');
      expect(found).toBeNull();
    });
  });

  describe('create', () => {
    it('should create a new user when email is unique', async () => {
      const userData = { email: 'unique@example.com', password_hash: 'password123' };
      const user = await userRepository.create(userData);
      expect(user).toHaveProperty('_id');
      expect(user.email).toBe('unique@example.com');
      const found = await User.findOne({ email: 'unique@example.com' });
      expect(found).not.toBeNull();
    });

    it('should throw error when email already exists', async () => {
      await User.create({ email: 'duplicate@example.com', password_hash: 'password123' });
      const userData = { email: 'duplicate@example.com', password_hash: 'password123' };
      await expect(userRepository.create(userData)).rejects.toThrow('Email already in use');
    });
  });
});

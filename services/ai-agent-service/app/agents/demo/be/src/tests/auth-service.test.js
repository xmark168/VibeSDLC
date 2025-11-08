const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const AuthService = require('../services/authService');
const userRepository = require('../repositories/userRepository');
const User = require('../models/User');
const connectDB = require('../db/mongoose');

jest.mock('../repositories/userRepository');
jest.mock('bcryptjs');
jest.mock('jsonwebtoken');

const mockUser = {
  _id: new mongoose.Types.ObjectId(),
  email: 'test@example.com',
  password_hash: 'hashedpassword',
  is_verified: false
};

describe('AuthService', () => {
  beforeAll(async () => {
    process.env.MONGODB_URI = process.env.MONGODB_URI_TEST || 'mongodb://localhost:27017/vibesdlc_test';
    await connectDB();
    await User.deleteMany({});
  });

  afterAll(async () => {
    await User.deleteMany({});
    await mongoose.connection.close();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('registerUser', () => {
    it('should register a new user if email does not exist', async () => {
      userRepository.findByEmail.mockResolvedValue(null);
      userRepository.create.mockResolvedValue(mockUser);
      const userData = { email: mockUser.email, password_hash: mockUser.password_hash };
      const result = await AuthService.registerUser(userData);
      expect(userRepository.findByEmail).toHaveBeenCalledWith(userData.email);
      expect(userRepository.create).toHaveBeenCalledWith(userData);
      expect(result).toEqual(mockUser);
    });

    it('should throw error if email already exists', async () => {
      userRepository.findByEmail.mockResolvedValue(mockUser);
      const userData = { email: mockUser.email, password_hash: mockUser.password_hash };
      await expect(AuthService.registerUser(userData)).rejects.toThrow('Email already exists');
      expect(userRepository.findByEmail).toHaveBeenCalledWith(userData.email);
      expect(userRepository.create).not.toHaveBeenCalled();
    });
  });

  describe('loginUser', () => {
    it('should login user and return user and token if credentials are valid', async () => {
      userRepository.findByEmail.mockResolvedValue(mockUser);
      bcrypt.compare.mockResolvedValue(true);
      jwt.sign.mockReturnValue('mocktoken');
      const result = await AuthService.loginUser(mockUser.email, 'plaintextpassword');
      expect(userRepository.findByEmail).toHaveBeenCalledWith(mockUser.email);
      expect(bcrypt.compare).toHaveBeenCalledWith('plaintextpassword', mockUser.password_hash);
      expect(jwt.sign).toHaveBeenCalledWith(
        {
          id: mockUser._id,
          email: mockUser.email,
          is_verified: mockUser.is_verified
        },
        expect.anything(),
        expect.anything()
      );
      expect(result).toEqual({ user: mockUser, token: 'mocktoken' });
    });

    it('should throw error if user not found', async () => {
      userRepository.findByEmail.mockResolvedValue(null);
      await expect(AuthService.loginUser('notfound@example.com', 'password')).rejects.toThrow('Invalid email or password');
      expect(userRepository.findByEmail).toHaveBeenCalledWith('notfound@example.com');
      expect(bcrypt.compare).not.toHaveBeenCalled();
      expect(jwt.sign).not.toHaveBeenCalled();
    });

    it('should throw error if password is invalid', async () => {
      userRepository.findByEmail.mockResolvedValue(mockUser);
      bcrypt.compare.mockResolvedValue(false);
      await expect(AuthService.loginUser(mockUser.email, 'wrongpassword')).rejects.toThrow('Invalid email or password');
      expect(userRepository.findByEmail).toHaveBeenCalledWith(mockUser.email);
      expect(bcrypt.compare).toHaveBeenCalledWith('wrongpassword', mockUser.password_hash);
      expect(jwt.sign).not.toHaveBeenCalled();
    });
  });
});

const AuthService = require('../services/authService');
const userRepository = require('../repositories/userRepository');
const AppError = require('../utils/AppError');
const jwt = require('jsonwebtoken');

describe('AuthService.registerUser', () => {
  const mockUser = {
    _id: '507f1f77bcf86cd799439011',
    email: 'test@example.com',
    password_hash: 'hashedpassword',
    toObject() {
      return { _id: this._id, email: this.email, password_hash: this.password_hash };
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should register a user and return user object without password_hash and a JWT token', async () => {
    jest.spyOn(userRepository, 'create').mockResolvedValue(mockUser);
    jest.spyOn(jwt, 'sign').mockReturnValue('mocked.jwt.token');

    const result = await AuthService.registerUser({ email: 'test@example.com', password: 'password123' });
    expect(result.user).toEqual({ _id: mockUser._id, email: mockUser.email });
    expect(result.token).toBe('mocked.jwt.token');
    expect(userRepository.create).toHaveBeenCalledWith({ email: 'test@example.com', password_hash: 'password123' });
    expect(jwt.sign).toHaveBeenCalledWith(
      { id: mockUser._id, email: mockUser.email },
      expect.any(String),
      expect.any(Object)
    );
  });

  it('should throw 400 error if email or password is missing', async () => {
    await expect(AuthService.registerUser({ email: '', password: 'pass' })).rejects.toThrow(AppError);
    await expect(AuthService.registerUser({ email: 'test@example.com', password: '' })).rejects.toThrow(AppError);
    await expect(AuthService.registerUser({})).rejects.toThrow(AppError);
  });

  it('should throw 409 error if duplicate email', async () => {
    jest.spyOn(userRepository, 'create').mockRejectedValue({ code: 'DUPLICATE_EMAIL' });
    await expect(AuthService.registerUser({ email: 'test@example.com', password: 'password123' }))
      .rejects.toThrow(AppError);
    try {
      await AuthService.registerUser({ email: 'test@example.com', password: 'password123' });
    } catch (err) {
      expect(err).toBeInstanceOf(AppError);
      expect(err.message).toBe('Email already in use');
      expect(err.statusCode).toBe(409);
    }
  });

  it('should throw 400 error on validation error', async () => {
    jest.spyOn(userRepository, 'create').mockRejectedValue({ name: 'ValidationError', message: 'Invalid email' });
    try {
      await AuthService.registerUser({ email: 'bad', password: 'password123' });
    } catch (err) {
      expect(err).toBeInstanceOf(AppError);
      expect(err.message).toBe('Invalid email');
      expect(err.statusCode).toBe(400);
    }
  });

  it('should throw 500 error on unknown error', async () => {
    jest.spyOn(userRepository, 'create').mockRejectedValue({ message: 'Unknown error' });
    try {
      await AuthService.registerUser({ email: 'test@example.com', password: 'password123' });
    } catch (err) {
      expect(err).toBeInstanceOf(AppError);
      expect(err.message).toBe('Unknown error');
      expect(err.statusCode).toBe(500);
    }
  });
});

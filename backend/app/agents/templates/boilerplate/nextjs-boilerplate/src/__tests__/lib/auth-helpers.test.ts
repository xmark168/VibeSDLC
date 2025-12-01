import { createUser, verifyPassword } from '@/lib/auth-helpers';
import { prisma } from '@/lib/prisma';
import bcrypt from 'bcryptjs';

// Mock Prisma
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      create: jest.fn(),
      findUnique: jest.fn(),
    },
  },
}));

// Mock bcrypt
jest.mock('bcryptjs', () => ({
  hash: jest.fn(),
  compare: jest.fn(),
}));

describe('auth-helpers', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createUser', () => {
    it('should create a user with hashed password', async () => {
      const mockUser = {
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        password: 'hashed-password',
        createdAt: new Date('2024-01-01'),
      };

      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const result = await createUser({
        username: 'testuser',
        password: 'plainpassword',
        email: 'test@example.com',
      });

      expect(bcrypt.hash).toHaveBeenCalledWith('plainpassword', 10);
      expect(prisma.user.create).toHaveBeenCalledWith({
        data: {
          username: 'testuser',
          password: 'hashed-password',
          email: 'test@example.com',
        },
      });
      expect(result).toEqual({
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        createdAt: mockUser.createdAt,
      });
    });

    it('should create a user without email', async () => {
      const mockUser = {
        id: 'user-456',
        username: 'noemailer',
        email: null,
        password: 'hashed-password',
        createdAt: new Date('2024-01-01'),
      };

      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const result = await createUser({
        username: 'noemailer',
        password: 'password123',
      });

      expect(prisma.user.create).toHaveBeenCalledWith({
        data: {
          username: 'noemailer',
          password: 'hashed-password',
          email: null,
        },
      });
      expect(result.email).toBeNull();
    });

    it('should not return password in result', async () => {
      const mockUser = {
        id: 'user-789',
        username: 'secureuser',
        email: 'secure@example.com',
        password: 'hashed-password',
        createdAt: new Date('2024-01-01'),
      };

      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const result = await createUser({
        username: 'secureuser',
        password: 'mypassword',
        email: 'secure@example.com',
      });

      expect(result).not.toHaveProperty('password');
    });
  });

  describe('verifyPassword', () => {
    it('should return true for valid password', async () => {
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await verifyPassword('plainpassword', 'hashed-password');

      expect(bcrypt.compare).toHaveBeenCalledWith('plainpassword', 'hashed-password');
      expect(result).toBe(true);
    });

    it('should return false for invalid password', async () => {
      (bcrypt.compare as jest.Mock).mockResolvedValue(false);

      const result = await verifyPassword('wrongpassword', 'hashed-password');

      expect(bcrypt.compare).toHaveBeenCalledWith('wrongpassword', 'hashed-password');
      expect(result).toBe(false);
    });

    it('should handle empty password', async () => {
      (bcrypt.compare as jest.Mock).mockResolvedValue(false);

      const result = await verifyPassword('', 'hashed-password');

      expect(result).toBe(false);
    });
  });
});

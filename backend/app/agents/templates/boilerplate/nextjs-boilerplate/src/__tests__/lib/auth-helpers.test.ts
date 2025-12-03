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

    it('should handle bcrypt compare error', async () => {
      (bcrypt.compare as jest.Mock).mockRejectedValue(new Error('Bcrypt error'));

      await expect(verifyPassword('password', 'hash')).rejects.toThrow('Bcrypt error');
    });

    it('should handle unicode password', async () => {
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await verifyPassword('密码123пароль', 'hashed-password');

      expect(bcrypt.compare).toHaveBeenCalledWith('密码123пароль', 'hashed-password');
      expect(result).toBe(true);
    });

    it('should handle very long password (1000 chars)', async () => {
      const longPassword = 'x'.repeat(1000);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await verifyPassword(longPassword, 'hashed-password');

      expect(bcrypt.compare).toHaveBeenCalledWith(longPassword, 'hashed-password');
      expect(result).toBe(true);
    });
  });

  describe('createUser - Error handling', () => {
    it('should throw on duplicate username (Prisma P2002)', async () => {
      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      const prismaError = new Error('Unique constraint failed');
      (prismaError as any).code = 'P2002';
      (prisma.user.create as jest.Mock).mockRejectedValue(prismaError);

      await expect(
        createUser({
          username: 'existinguser',
          password: 'password',
          email: 'test@example.com',
        })
      ).rejects.toThrow('Unique constraint failed');
    });

    it('should throw on bcrypt hash failure', async () => {
      (bcrypt.hash as jest.Mock).mockRejectedValue(new Error('Hash computation failed'));

      await expect(
        createUser({
          username: 'testuser',
          password: 'password',
        })
      ).rejects.toThrow('Hash computation failed');
    });

    it('should throw on database connection error', async () => {
      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockRejectedValue(new Error('Connection refused'));

      await expect(
        createUser({
          username: 'testuser',
          password: 'password',
        })
      ).rejects.toThrow('Connection refused');
    });
  });

  describe('createUser - Edge cases', () => {
    it('should handle special characters in username', async () => {
      const mockUser = {
        id: 'user-special',
        username: 'user@domain.com',
        email: null,
        password: 'hashed-password',
        createdAt: new Date(),
      };

      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const result = await createUser({
        username: 'user@domain.com',
        password: 'password',
      });

      expect(result.username).toBe('user@domain.com');
    });

    it('should handle unicode username', async () => {
      const mockUser = {
        id: 'user-unicode',
        username: '用户名',
        email: null,
        password: 'hashed-password',
        createdAt: new Date(),
      };

      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const result = await createUser({
        username: '用户名',
        password: 'password',
      });

      expect(result.username).toBe('用户名');
    });

    it('should handle minimum length password', async () => {
      const mockUser = {
        id: 'user-minpass',
        username: 'minpass',
        email: null,
        password: 'hashed-password',
        createdAt: new Date(),
      };

      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const result = await createUser({
        username: 'minpass',
        password: 'a',
      });

      expect(bcrypt.hash).toHaveBeenCalledWith('a', 10);
      expect(result).toBeDefined();
    });

    it('should handle email with subdomain', async () => {
      const mockUser = {
        id: 'user-subdomain',
        username: 'testuser',
        email: 'user@mail.example.co.uk',
        password: 'hashed-password',
        createdAt: new Date(),
      };

      (bcrypt.hash as jest.Mock).mockResolvedValue('hashed-password');
      (prisma.user.create as jest.Mock).mockResolvedValue(mockUser);

      const result = await createUser({
        username: 'testuser',
        password: 'password',
        email: 'user@mail.example.co.uk',
      });

      expect(result.email).toBe('user@mail.example.co.uk');
    });
  });
});

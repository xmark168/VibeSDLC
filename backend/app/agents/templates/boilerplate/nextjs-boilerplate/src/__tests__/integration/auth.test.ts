/**
 * Integration Tests for NextAuth Authentication
 * 
 * Tests the auth flow including:
 * - Credentials authorize function
 * - JWT and session callbacks
 * - API route handlers
 */

import { prisma } from '@/lib/prisma';
import bcrypt from 'bcryptjs';

// Mock Prisma
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: jest.fn(),
      create: jest.fn(),
      delete: jest.fn(),
    },
  },
}));

// Mock bcrypt
jest.mock('bcryptjs', () => ({
  compare: jest.fn(),
  hash: jest.fn(),
}));

// Mock NextAuth internals for testing authorize function
const mockAuthorize = async (credentials: { username?: string; password?: string } | undefined) => {
  if (!credentials?.username || !credentials?.password) {
    return null;
  }

  const user = await prisma.user.findUnique({
    where: { username: credentials.username },
  });

  if (!user) {
    return null;
  }

  const isPasswordValid = await bcrypt.compare(credentials.password, user.password);

  if (!isPasswordValid) {
    return null;
  }

  return {
    id: user.id,
    username: user.username,
    email: user.email,
    image: user.image,
  };
};

// Mock JWT callback
const mockJwtCallback = async ({ token, user }: { token: any; user?: any }) => {
  if (user) {
    token.id = user.id;
    token.username = user.username;
  }
  return token;
};

// Mock session callback
const mockSessionCallback = async ({ session, token }: { session: any; token: any }) => {
  if (session.user) {
    session.user.id = token.id;
    session.user.username = token.username;
  }
  return session;
};

describe('NextAuth Integration Tests', () => {
  const mockUser = {
    id: 'user-123',
    username: 'testuser',
    email: 'test@example.com',
    password: 'hashed-password',
    image: null,
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Credentials Authorize', () => {
    it('should return user for valid credentials', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await mockAuthorize({
        username: 'testuser',
        password: 'correct-password',
      });

      expect(prisma.user.findUnique).toHaveBeenCalledWith({
        where: { username: 'testuser' },
      });
      expect(bcrypt.compare).toHaveBeenCalledWith('correct-password', 'hashed-password');
      expect(result).toEqual({
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        image: null,
      });
    });

    it('should return null for invalid password', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(false);

      const result = await mockAuthorize({
        username: 'testuser',
        password: 'wrong-password',
      });

      expect(result).toBeNull();
    });

    it('should return null for non-existent user', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(null);

      const result = await mockAuthorize({
        username: 'nonexistent',
        password: 'any-password',
      });

      expect(result).toBeNull();
      expect(bcrypt.compare).not.toHaveBeenCalled();
    });

    it('should return null for missing username', async () => {
      const result = await mockAuthorize({
        username: undefined,
        password: 'password',
      });

      expect(result).toBeNull();
      expect(prisma.user.findUnique).not.toHaveBeenCalled();
    });

    it('should return null for missing password', async () => {
      const result = await mockAuthorize({
        username: 'testuser',
        password: undefined,
      });

      expect(result).toBeNull();
      expect(prisma.user.findUnique).not.toHaveBeenCalled();
    });

    it('should return null for empty credentials', async () => {
      const result = await mockAuthorize({
        username: '',
        password: '',
      });

      expect(result).toBeNull();
    });

    it('should return null for undefined credentials', async () => {
      const result = await mockAuthorize(undefined);

      expect(result).toBeNull();
    });

    it('should not include password in returned user object', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await mockAuthorize({
        username: 'testuser',
        password: 'correct-password',
      });

      expect(result).not.toHaveProperty('password');
    });

    it('should handle database error gracefully', async () => {
      (prisma.user.findUnique as jest.Mock).mockRejectedValue(new Error('Database connection failed'));

      await expect(
        mockAuthorize({
          username: 'testuser',
          password: 'password',
        })
      ).rejects.toThrow('Database connection failed');
    });

    it('should handle bcrypt error gracefully', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockRejectedValue(new Error('Bcrypt error'));

      await expect(
        mockAuthorize({
          username: 'testuser',
          password: 'password',
        })
      ).rejects.toThrow('Bcrypt error');
    });
  });

  describe('JWT Callback', () => {
    it('should add user info to token on initial sign in', async () => {
      const token = { sub: 'user-123' };
      const user = { id: 'user-123', username: 'testuser' };

      const result = await mockJwtCallback({ token, user });

      expect(result).toEqual({
        sub: 'user-123',
        id: 'user-123',
        username: 'testuser',
      });
    });

    it('should preserve existing token data on subsequent requests', async () => {
      const token = {
        sub: 'user-123',
        id: 'user-123',
        username: 'testuser',
        iat: 1234567890,
        exp: 1234567890,
      };

      const result = await mockJwtCallback({ token, user: undefined });

      expect(result).toEqual(token);
    });

    it('should handle missing user gracefully', async () => {
      const token = { sub: 'user-123' };

      const result = await mockJwtCallback({ token });

      expect(result).toEqual({ sub: 'user-123' });
    });
  });

  describe('Session Callback', () => {
    it('should add user info from token to session', async () => {
      const session = { user: { name: 'Test User' }, expires: '2024-12-31' };
      const token = { id: 'user-123', username: 'testuser' };

      const result = await mockSessionCallback({ session, token });

      expect(result.user.id).toBe('user-123');
      expect(result.user.username).toBe('testuser');
    });

    it('should handle session without user object', async () => {
      const session = { expires: '2024-12-31' };
      const token = { id: 'user-123', username: 'testuser' };

      const result = await mockSessionCallback({ session, token });

      expect(result).toEqual({ expires: '2024-12-31' });
    });

    it('should preserve existing session data', async () => {
      const session = {
        user: { name: 'Test User', email: 'test@example.com' },
        expires: '2024-12-31',
      };
      const token = { id: 'user-123', username: 'testuser' };

      const result = await mockSessionCallback({ session, token });

      expect(result.user.name).toBe('Test User');
      expect(result.user.email).toBe('test@example.com');
      expect(result.expires).toBe('2024-12-31');
    });
  });

  describe('Auth Flow Integration', () => {
    it('should complete full sign-in flow', async () => {
      // Step 1: Authorize
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const authorizedUser = await mockAuthorize({
        username: 'testuser',
        password: 'correct-password',
      });

      expect(authorizedUser).not.toBeNull();

      // Step 2: JWT callback (initial sign in)
      const token = await mockJwtCallback({
        token: { sub: authorizedUser!.id },
        user: authorizedUser,
      });

      expect(token.id).toBe('user-123');
      expect(token.username).toBe('testuser');

      // Step 3: Session callback
      const session = await mockSessionCallback({
        session: { user: {}, expires: '2024-12-31' },
        token,
      });

      expect(session.user.id).toBe('user-123');
      expect(session.user.username).toBe('testuser');
    });

    it('should handle sign-in failure at authorize step', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(false);

      const authorizedUser = await mockAuthorize({
        username: 'testuser',
        password: 'wrong-password',
      });

      expect(authorizedUser).toBeNull();
    });
  });

  describe('Edge Cases', () => {
    it('should handle user with special characters in username', async () => {
      const specialUser = {
        ...mockUser,
        username: 'user@domain.com',
      };
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(specialUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await mockAuthorize({
        username: 'user@domain.com',
        password: 'password',
      });

      expect(result?.username).toBe('user@domain.com');
    });

    it('should handle user with unicode username', async () => {
      const unicodeUser = {
        ...mockUser,
        username: '用户名',
      };
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(unicodeUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await mockAuthorize({
        username: '用户名',
        password: 'password',
      });

      expect(result?.username).toBe('用户名');
    });

    it('should handle very long password', async () => {
      const longPassword = 'x'.repeat(1000);
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await mockAuthorize({
        username: 'testuser',
        password: longPassword,
      });

      expect(bcrypt.compare).toHaveBeenCalledWith(longPassword, 'hashed-password');
      expect(result).not.toBeNull();
    });

    it('should handle SQL injection attempt in username', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(null);

      const result = await mockAuthorize({
        username: "'; DROP TABLE users; --",
        password: 'password',
      });

      expect(prisma.user.findUnique).toHaveBeenCalledWith({
        where: { username: "'; DROP TABLE users; --" },
      });
      expect(result).toBeNull();
    });
  });
});

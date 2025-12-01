import { prisma } from '@/lib/prisma';
import bcrypt from 'bcryptjs';

// Mock Prisma
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: jest.fn(),
    },
  },
}));

// Mock bcrypt
jest.mock('bcryptjs', () => ({
  compare: jest.fn(),
}));

// Test the authorize logic separately (extracted from auth.ts)
async function authorizeCredentials(credentials: { username?: string; password?: string } | undefined) {
  if (!credentials?.username || !credentials?.password) {
    return null;
  }

  const user = await prisma.user.findUnique({
    where: {
      username: credentials.username,
    },
  });

  if (!user) {
    return null;
  }

  const isPasswordValid = await bcrypt.compare(
    credentials.password,
    (user as any).password
  );

  if (!isPasswordValid) {
    return null;
  }

  return {
    id: (user as any).id,
    username: (user as any).username,
    email: (user as any).email,
    image: (user as any).image,
  };
}

describe('Auth - Credentials Provider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('authorize', () => {
    const mockUser = {
      id: 'user-123',
      username: 'testuser',
      email: 'test@example.com',
      password: 'hashed-password',
      image: null,
    };

    it('should return user for valid credentials', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await authorizeCredentials({
        username: 'testuser',
        password: 'validpassword',
      });

      expect(prisma.user.findUnique).toHaveBeenCalledWith({
        where: { username: 'testuser' },
      });
      expect(bcrypt.compare).toHaveBeenCalledWith('validpassword', 'hashed-password');
      expect(result).toEqual({
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        image: null,
      });
    });

    it('should return null for missing username', async () => {
      const result = await authorizeCredentials({
        password: 'somepassword',
      });

      expect(prisma.user.findUnique).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should return null for missing password', async () => {
      const result = await authorizeCredentials({
        username: 'testuser',
      });

      expect(prisma.user.findUnique).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should return null for undefined credentials', async () => {
      const result = await authorizeCredentials(undefined);

      expect(prisma.user.findUnique).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should return null for non-existent user', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(null);

      const result = await authorizeCredentials({
        username: 'nonexistent',
        password: 'somepassword',
      });

      expect(prisma.user.findUnique).toHaveBeenCalledWith({
        where: { username: 'nonexistent' },
      });
      expect(bcrypt.compare).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should return null for invalid password', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(false);

      const result = await authorizeCredentials({
        username: 'testuser',
        password: 'wrongpassword',
      });

      expect(bcrypt.compare).toHaveBeenCalledWith('wrongpassword', 'hashed-password');
      expect(result).toBeNull();
    });

    it('should not return password in authorized user', async () => {
      (prisma.user.findUnique as jest.Mock).mockResolvedValue(mockUser);
      (bcrypt.compare as jest.Mock).mockResolvedValue(true);

      const result = await authorizeCredentials({
        username: 'testuser',
        password: 'validpassword',
      });

      expect(result).not.toHaveProperty('password');
    });
  });
});

describe('Auth - JWT Callbacks', () => {
  // Test JWT callback logic
  function jwtCallback({ token, user }: { token: any; user?: any }) {
    if (user) {
      token.id = user.id;
      token.username = user.username;
    }
    return token;
  }

  it('should add user info to token on login', () => {
    const token = { sub: 'token-sub' };
    const user = { id: 'user-123', username: 'testuser' };

    const result = jwtCallback({ token, user });

    expect(result.id).toBe('user-123');
    expect(result.username).toBe('testuser');
  });

  it('should return token unchanged if no user', () => {
    const token = { sub: 'token-sub', id: 'existing-id' };

    const result = jwtCallback({ token });

    expect(result).toEqual(token);
  });
});

describe('Auth - Session Callbacks', () => {
  // Test session callback logic
  function sessionCallback({ session, token }: { session: any; token: any }) {
    if (session.user) {
      session.user.id = token.id;
      session.user.username = token.username;
    }
    return session;
  }

  it('should add token info to session', () => {
    const session = { user: { name: 'Test User' } };
    const token = { id: 'user-123', username: 'testuser' };

    const result = sessionCallback({ session, token });

    expect(result.user.id).toBe('user-123');
    expect(result.user.username).toBe('testuser');
  });

  it('should handle session without user', () => {
    const session = {};
    const token = { id: 'user-123', username: 'testuser' };

    const result = sessionCallback({ session, token });

    expect(result).toEqual({});
  });
});

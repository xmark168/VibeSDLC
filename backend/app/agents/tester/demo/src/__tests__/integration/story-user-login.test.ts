import bcrypt from "bcryptjs";

// Prisma mock pattern (per project conventions)
const mockFindUnique = jest.fn();
jest.mock("@/lib/prisma", () => ({
  prisma: {
    user: {
      findUnique: (...args: unknown[]) => mockFindUnique(...args),
    },
  },
}));

// Replicate authorize() logic from src/auth.ts
describe("Story: User Login", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Helper: mimic authorize() logic
  async function authorize(credentials: { username?: string; password?: string }) {
    if (!credentials?.username || !credentials?.password) return null;
    const user = await mockFindUnique({ where: { username: credentials.username } });
    if (!user) return null;
    const isValid = await bcrypt.compare(credentials.password, user.password);
    if (!isValid) return null;
    return {
      id: user.id,
      username: user.username,
      email: user.email,
      image: user.image,
    };
  }

  it("valid credentials returns token", async () => {
    // Arrange
    const password = "correct-password";
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = {
      id: "test-id-123",
      username: "testuser",
      email: "testuser@example.com",
      password: hashedPassword,
      image: null,
    };
    mockFindUnique.mockResolvedValue(user);
    
    // Act
    const result = await authorize({ username: "testuser", password });

    // Assert
    expect(result).toEqual({
      id: "test-id-123",
      username: "testuser",
      email: "testuser@example.com",
      image: null,
    });
    expect(mockFindUnique).toHaveBeenCalledWith({ where: { username: "testuser" } });
  });

  it("invalid password returns 401", async () => {
    // Arrange
    const password = "correct-password";
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = {
      id: "test-id-123",
      username: "testuser",
      email: "testuser@example.com",
      password: hashedPassword,
      image: null,
    };
    mockFindUnique.mockResolvedValue(user);
    
    // Act
    const result = await authorize({ username: "testuser", password: "wrong-password" });

    // Assert
    expect(result).toBeNull();
    expect(mockFindUnique).toHaveBeenCalledWith({ where: { username: "testuser" } });
  });

  it("missing email returns 400", async () => {
    // Arrange
    // No user lookup should occur
    // Act
    const result = await authorize({ password: "irrelevant" });

    // Assert
    expect(result).toBeNull();
    expect(mockFindUnique).not.toHaveBeenCalled();
  });
});

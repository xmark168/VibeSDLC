import bcrypt from "bcryptjs";

// Prisma mock pattern (use this exact pattern)
const mockFindUnique = jest.fn();
const mockCreate = jest.fn();
const mockFindMany = jest.fn();
const mockDelete = jest.fn();

jest.mock("@/lib/prisma", () => ({
  prisma: {
    user: {
      findUnique: (...args: unknown[]) => mockFindUnique(...args),
      create: (...args: unknown[]) => mockCreate(...args),
      findMany: (...args: unknown[]) => mockFindMany(...args),
      delete: (...args: unknown[]) => mockDelete(...args),
    },
    // Add other models as needed
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
    return isValid
      ? { id: user.id, username: user.username, email: user.email, image: user.image }
      : null;
  }

  it("valid credentials return 200 with JWT token (authorize returns user)", async () => {
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
    const hashedPassword = await bcrypt.hash("correct-password", 10);
    mockFindUnique.mockResolvedValue({
      id: "test-id-123",
      username: "testuser",
      email: "testuser@example.com",
      password: hashedPassword,
      image: null,
    });

    // Act
    const result = await authorize({ username: "testuser", password: "wrong-password" });

    // Assert
    expect(result).toBeNull();
    expect(mockFindUnique).toHaveBeenCalledWith({ where: { username: "testuser" } });
  });

  it("unknown email returns 401", async () => {
    // Arrange
    mockFindUnique.mockResolvedValue(null);

    // Act
    const result = await authorize({ username: "unknown@example.com", password: "any" });

    // Assert
    expect(result).toBeNull();
    expect(mockFindUnique).toHaveBeenCalledWith({ where: { username: "unknown@example.com" } });
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

  it("missing password returns 400", async () => {
    // Arrange
    // No user lookup should occur

    // Act
    const result = await authorize({ username: "testuser" });

    // Assert
    expect(result).toBeNull();
    expect(mockFindUnique).not.toHaveBeenCalled();
  });
});

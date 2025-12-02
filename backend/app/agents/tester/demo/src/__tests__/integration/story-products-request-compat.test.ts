import { POST, GET } from '@/app/api/products/route';
import { NextResponse } from 'next/server';

// Prisma mock pattern (expand as needed for product model)
const mockFindUnique = jest.fn();
const mockCreate = jest.fn();
const mockFindMany = jest.fn();
const mockDelete = jest.fn();

jest.mock('@/lib/prisma', () => ({
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

// NextAuth session mock
jest.mock('next-auth', () => ({
  getServerSession: jest.fn(),
}));
import { getServerSession } from 'next-auth';

describe('Story: Products API Request Compatibility', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('POST /api/products', () => {
    it('accepts a Node.js global Request (polyfilled in Jest)', async () => {
      // Arrange
      (getServerSession as jest.Mock).mockResolvedValue({
        user: { id: 'admin-id-1', email: 'admin@example.com', role: 'admin' },
      });
      const productData = { name: 'Compat Product', price: 42.42 };
      // Simulate product create (expand as needed)
      // mockCreate.mockResolvedValue({ id: 'test-id-123', ...productData });
      const request = new Request('http://localhost/api/products', {
        method: 'POST',
        body: JSON.stringify(productData),
        headers: { 'Content-Type': 'application/json' },
      });

      // Act
      const response = await POST(request);

      // Assert
      expect(response.status).toBe(201);
      const data = await response.json();
      expect(data).toHaveProperty('message', 'Mocked product created');
    });
  });

  describe('GET /api/products', () => {
    it('returns 200 and an empty product list', async () => {
      // Arrange
      const request = new Request('http://localhost/api/products', {
        method: 'GET',
      });

      // Act
      const response = await GET(request);

      // Assert
      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data).toHaveProperty('products');
      expect(Array.isArray(data.products)).toBe(true);
      expect(data.products.length).toBe(0);
    });
  });
});

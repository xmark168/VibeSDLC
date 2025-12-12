import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { successResponse, handleError } from '@/lib/api-response';

/**
 * GET /api/books/bestsellers
 * Fetches bestseller books based on order quantity
 * Query params:
 * - limit: number of books to return (default: 10)
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const limit = parseInt(searchParams.get('limit') ?? '10');

    // Get books with most order items (bestsellers)
    // Using raw query for complex aggregation with SUM
    const bestsellers = await prisma.$queryRaw<
      Array<{
        id: string;
        title: string;
        author: string;
        price: number;
        coverImage: string | null;
        description: string | null;
        totalQuantity: bigint;
      }>
    >`
      SELECT 
        b.id,
        b.title,
        b.author,
        b.price,
        b."coverImage",
        b.description,
        COALESCE(SUM(oi.quantity), 0) as "totalQuantity"
      FROM "Book" b
      LEFT JOIN "OrderItem" oi ON b.id = oi."bookId"
      LEFT JOIN "Order" o ON oi."orderId" = o.id
      WHERE o.status = 'COMPLETED' OR o.status IS NULL
      GROUP BY b.id
      ORDER BY "totalQuantity" DESC
      LIMIT ${limit}
    `;

    // Convert BigInt to number and format response
    const formattedBestsellers = bestsellers.map((book) => ({
      id: book.id,
      title: book.title,
      author: book.author,
      price: Number(book.price),
      coverImage: book.coverImage,
      description: book.description,
      totalSold: Number(book.totalQuantity),
    }));

    return successResponse(formattedBestsellers);
  } catch (error) {
    return handleError(error);
  }
}

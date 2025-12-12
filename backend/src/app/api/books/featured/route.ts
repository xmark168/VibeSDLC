import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { successResponse, handleError } from '@/lib/api-response';

/**
 * GET /api/books/featured
 * Fetches 8-12 featured books with cover images, titles, authors, and prices
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '12');
    
    // Validate limit range
    const validLimit = Math.min(Math.max(limit, 8), 12);

    const books = await prisma.book.findMany({
      where: {
        isFeatured: true,
        isActive: true,
      },
      select: {
        id: true,
        title: true,
        coverImage: true,
        price: true,
        authors: {
          select: {
            author: {
              select: {
                id: true,
                name: true,
              },
            },
          },
        },
      },
      take: validLimit,
      orderBy: {
        createdAt: 'desc',
      },
    });

    // Transform data to flatten authors and convert Decimal to number
    const transformedBooks = books.map((book) => ({
      id: book.id,
      title: book.title,
      coverImage: book.coverImage,
      price: Number(book.price),
      authors: book.authors.map((ba) => ({
        id: ba.author.id,
        name: ba.author.name,
      })),
    }));

    return successResponse(transformedBooks);
  } catch (error) {
    return handleError(error);
  }
}

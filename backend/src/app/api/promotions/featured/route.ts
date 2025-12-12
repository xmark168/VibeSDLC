import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { successResponse, handleError, ApiErrors } from '@/lib/api-response';

/**
 * GET /api/promotions/featured
 * Fetches the active featured promotion for hero banner display
 * 
 * Returns:
 * - Single promotion with isFeatured=true and active status
 * - Includes related book data with cover image
 * - Returns null if no featured promotion exists
 */
export async function GET(request: NextRequest) {
  try {
    // Fetch the active featured promotion
    const promotion = await prisma.promotion.findFirst({
      where: {
        isFeatured: true,
        isActive: true,
        startDate: {
          lte: new Date(),
        },
        endDate: {
          gte: new Date(),
        },
      },
      include: {
        book: {
          select: {
            id: true,
            title: true,
            slug: true,
            coverImage: true,
            price: true,
            author: true,
          },
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    // Return null if no featured promotion found (not an error)
    if (!promotion) {
      return successResponse(null, 'No featured promotion found');
    }

    // Convert Decimal fields to numbers for JSON serialization
    const formattedPromotion = {
      ...promotion,
      discountPercent: Number(promotion.discountPercent),
      book: promotion.book
        ? {
            ...promotion.book,
            price: Number(promotion.book.price),
          }
        : null,
    };

    return successResponse(formattedPromotion);
  } catch (error) {
    return handleError(error);
  }
}

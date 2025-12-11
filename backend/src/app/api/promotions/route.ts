import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { successResponse, handleError } from '@/lib/api-response';

/**
 * GET /api/promotions
 * Fetches active promotions for hero banner
 * Returns promotions that are currently active (within start/end date range)
 */
export async function GET(request: NextRequest) {
  try {
    const now = new Date();

    const promotions = await prisma.promotion.findMany({
      where: {
        startDate: {
          lte: now,
        },
        endDate: {
          gte: now,
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
      select: {
        id: true,
        title: true,
        description: true,
        imageUrl: true,
        linkUrl: true,
        startDate: true,
        endDate: true,
        createdAt: true,
      },
    });

    return successResponse(promotions);
  } catch (error) {
    return handleError(error);
  }
}

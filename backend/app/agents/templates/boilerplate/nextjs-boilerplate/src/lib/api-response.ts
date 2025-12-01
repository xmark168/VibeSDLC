/**
 * API Response Helpers
 * Utility functions để tạo consistent API responses
 */

import { NextResponse } from 'next/server';
import { ApiResponse, ApiError, HttpStatus, ApiErrorCode } from '@/types/api.types';
import { ZodError } from 'zod';

/**
 * Tạo success response
 */
export function successResponse<T>(
  data: T,
  message?: string,
  status: number = HttpStatus.OK
): NextResponse<ApiResponse<T>> {
  return NextResponse.json(
    {
      success: true,
      data,
      message,
    },
    { status }
  );
}

/**
 * Tạo error response
 */
export function errorResponse(
  error: ApiError,
  status: number = HttpStatus.INTERNAL_SERVER_ERROR
): NextResponse<ApiResponse> {
  return NextResponse.json(
    {
      success: false,
      error,
    },
    { status }
  );
}

/**
 * Xử lý Zod validation errors
 */
export function handleZodError(error: ZodError): NextResponse<ApiResponse> {
  const formattedErrors = error.issues.map((err) => ({
    field: err.path.join('.'),
    message: err.message,
  }));

  return errorResponse(
    {
      code: ApiErrorCode.VALIDATION_ERROR,
      message: 'Dữ liệu không hợp lệ',
      details: { errors: formattedErrors },
    },
    HttpStatus.UNPROCESSABLE_ENTITY
  );
}

/**
 * Xử lý generic errors
 */
export function handleError(error: unknown): NextResponse<ApiResponse> {
  console.error('API Error:', error);

  // Zod validation error
  if (error instanceof ZodError) {
    return handleZodError(error);
  }

  // Custom API error
  if (isApiError(error)) {
    return errorResponse(
      {
        code: error.code,
        message: error.message,
        details: error.details,
      },
      error.status || HttpStatus.INTERNAL_SERVER_ERROR
    );
  }

  // Generic error
  const message = error instanceof Error ? error.message : 'Đã xảy ra lỗi không xác định';

  return errorResponse(
    {
      code: ApiErrorCode.INTERNAL_ERROR,
      message,
      stack: process.env.NODE_ENV === 'development' ? (error as Error).stack : undefined,
    },
    HttpStatus.INTERNAL_SERVER_ERROR
  );
}

/**
 * Custom API Error class
 */
export class ApiException extends Error {
  constructor(
    public code: ApiErrorCode,
    public message: string,
    public status: number = HttpStatus.INTERNAL_SERVER_ERROR,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiException';
  }
}

/**
 * Type guard cho API error
 */
function isApiError(error: unknown): error is ApiException {
  return error instanceof ApiException;
}

/**
 * Predefined error responses
 */
export const ApiErrors = {
  unauthorized: () =>
    new ApiException(
      ApiErrorCode.UNAUTHORIZED,
      'Bạn cần đăng nhập để thực hiện hành động này',
      HttpStatus.UNAUTHORIZED
    ),

  forbidden: () =>
    new ApiException(
      ApiErrorCode.FORBIDDEN,
      'Bạn không có quyền thực hiện hành động này',
      HttpStatus.FORBIDDEN
    ),

  notFound: (resource: string = 'Resource') =>
    new ApiException(
      ApiErrorCode.NOT_FOUND,
      `${resource} không tồn tại`,
      HttpStatus.NOT_FOUND
    ),

  conflict: (message: string) =>
    new ApiException(ApiErrorCode.CONFLICT, message, HttpStatus.CONFLICT),

  validation: (message: string, details?: Record<string, any>) =>
    new ApiException(
      ApiErrorCode.VALIDATION_ERROR,
      message,
      HttpStatus.UNPROCESSABLE_ENTITY,
      details
    ),

  badRequest: (message: string = 'Yêu cầu không hợp lệ') =>
    new ApiException(
      ApiErrorCode.BAD_REQUEST,
      message,
      HttpStatus.BAD_REQUEST
    ),

  methodNotAllowed: (method: string) =>
    new ApiException(
      ApiErrorCode.METHOD_NOT_ALLOWED,
      `Method ${method} không được hỗ trợ`,
      HttpStatus.METHOD_NOT_ALLOWED
    ),

  tooManyRequests: (retryAfter?: number) =>
    new ApiException(
      ApiErrorCode.TOO_MANY_REQUESTS,
      'Quá nhiều yêu cầu, vui lòng thử lại sau',
      HttpStatus.TOO_MANY_REQUESTS,
      retryAfter ? { retryAfter } : undefined
    ),

  serviceUnavailable: (message: string = 'Dịch vụ tạm thời không khả dụng') =>
    new ApiException(
      ApiErrorCode.SERVICE_UNAVAILABLE,
      message,
      HttpStatus.SERVICE_UNAVAILABLE
    ),

  timeout: (operation: string = 'Operation') =>
    new ApiException(
      ApiErrorCode.TIMEOUT,
      `${operation} đã hết thời gian chờ`,
      HttpStatus.GATEWAY_TIMEOUT
    ),

  database: (message: string = 'Lỗi cơ sở dữ liệu') =>
    new ApiException(
      ApiErrorCode.DATABASE_ERROR,
      message,
      HttpStatus.INTERNAL_SERVER_ERROR
    ),
};


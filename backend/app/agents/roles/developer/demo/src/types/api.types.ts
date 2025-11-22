import { z } from 'zod';

/**
 * Generic API Response Types
 * Sử dụng cho tất cả API responses để đảm bảo consistency
 */

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiError;
  message?: string;
  meta?: PaginationMeta;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  stack?: string; // Chỉ hiển thị trong development
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

/**
 * HTTP Status Codes
 */
export enum HttpStatus {
  OK = 200,
  CREATED = 201,
  NO_CONTENT = 204,
  BAD_REQUEST = 400,
  UNAUTHORIZED = 401,
  FORBIDDEN = 403,
  NOT_FOUND = 404,
  CONFLICT = 409,
  UNPROCESSABLE_ENTITY = 422,
  INTERNAL_SERVER_ERROR = 500,
}

/**
 * API Error Codes
 */
export enum ApiErrorCode {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND',
  CONFLICT = 'CONFLICT',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  DATABASE_ERROR = 'DATABASE_ERROR',
}

/**
 * AUTHENTICATION
 */

// Request for user login
export interface LoginRequest {
  username: string;
  password: string;
}

// Response after successful user login
export interface LoginResponse {
  user: {
    id: string;
    username: string;
    // Potentially more user data, but avoid sending sensitive info
  };
  token: string; // JWT or similar access token
  expiresIn: number; // Token expiration time in seconds
}

// Response for user profile data
export interface UserProfileResponse {
  id: string;
  username: string;
  email?: string; // Optional email
  createdAt: Date;
  updatedAt: Date;
}

/**
 * REGISTRATION
 */

// Zod schema for user registration input validation
export const registerSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters long'),
  password: z.string().min(6, 'Password must be at least 6 characters long'),
});

// Type for user registration request payload
export type RegisterRequest = z.infer<typeof registerSchema>;

// Type for user registration response
export interface RegisterResponse {
  userId: string;
  username: string;
}


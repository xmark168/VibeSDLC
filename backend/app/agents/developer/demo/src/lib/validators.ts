import { z } from 'zod';
import { LoginRequest } from '@/types/api.types';

/**
 * Zod schema for login form validation
 */
export const loginSchema = z.object({
  email: z
    .string()
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(6, 'Password must be at least 6 characters long')
    .max(100, 'Password must not exceed 100 characters'),
});

/**
 * Infer the TypeScript type from the login schema
 */
export type LoginFormData = z.infer<typeof loginSchema>;

/**
 * Zod schema for user registration validation
 */
export const registerSchema = z.object({
  username: z
    .string()
    .min(3, 'Username must be at least 3 characters long')
    .max(50, 'Username must not exceed 50 characters'),
  email: z
    .string()
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(6, 'Password must be at least 6 characters long')
    .max(100, 'Password must not exceed 100 characters'),
});

/**
 * Infer the TypeScript type from the register schema
 */
export type RegisterFormData = z.infer<typeof registerSchema>;

/**
 * Application configuration constants
 * Centralized config for environment variables and app settings
 */

/**
 * API configuration
 */
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
} as const

/**
 * Authentication configuration
 */
export const AUTH_CONFIG = {
  TOKEN_STORAGE_KEY: 'refreshToken',
  ACCESS_TOKEN_EXPIRY: 15 * 60 * 1000, // 15 minutes
  REFRESH_TOKEN_EXPIRY: 7 * 24 * 60 * 60 * 1000, // 7 days
} as const

/**
 * UI configuration
 */
export const UI_CONFIG = {
  TOAST_DURATION: 5000, // 5 seconds
  TOAST_POSITION: 'top-right',
  DEFAULT_LANGUAGE: 'vi',
  SUPPORTED_LANGUAGES: ['vi', 'en'],
} as const

/**
 * Application metadata
 */
export const APP_CONFIG = {
  NAME: 'VibeSDLC',
  DESCRIPTION: 'Kanban-based Software Development Lifecycle Management',
  VERSION: '1.0.0',
} as const

/**
 * Feature flags
 */
export const FEATURES = {
  ENABLE_DARK_MODE: true,
  ENABLE_NOTIFICATIONS: true,
  ENABLE_ANALYTICS: false,
  ENABLE_I18N: true,
} as const

/**
 * Validation rules
 */
export const VALIDATION = {
  PASSWORD_MIN_LENGTH: 6,
  USERNAME_MIN_LENGTH: 3,
  USERNAME_MAX_LENGTH: 50,
  EMAIL_REGEX: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
} as const

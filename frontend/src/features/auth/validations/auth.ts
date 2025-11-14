import { z } from 'zod'

// Login validation schema
export const loginSchema = z.object({
  identifier: z
    .string()
    .min(1, 'Vui lòng nhập email hoặc tên đăng nhập')
    .max(255, 'Email hoặc tên đăng nhập quá dài'),
  password: z
    .string()
    .min(1, 'Vui lòng nhập mật khẩu')
    .min(6, 'Mật khẩu phải có ít nhất 6 ký tự')
    .max(100, 'Mật khẩu quá dài'),
})

// Register validation schema
export const registerSchema = z.object({
  username: z
    .string()
    .min(1, 'Vui lòng nhập tên đăng nhập')
    .min(3, 'Tên đăng nhập phải có ít nhất 3 ký tự')
    .max(50, 'Tên đăng nhập không được quá 50 ký tự')
    .regex(
      /^[a-zA-Z0-9_]+$/,
      'Tên đăng nhập chỉ được chứa chữ cái, số và dấu gạch dưới'
    ),
  email: z
    .string()
    .min(1, 'Vui lòng nhập email')
    .email('Email không hợp lệ')
    .max(255, 'Email quá dài'),
  password: z
    .string()
    .min(1, 'Vui lòng nhập mật khẩu')
    .min(8, 'Mật khẩu phải có ít nhất 8 ký tự')
    .max(100, 'Mật khẩu quá dài'),
  confirmPassword: z
    .string()
    .min(1, 'Vui lòng xác nhận mật khẩu'),
  fullName: z
    .string()
    .max(100, 'Họ tên quá dài')
    .optional()
    .or(z.literal('')),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Mật khẩu xác nhận không khớp',
  path: ['confirmPassword'],
})

// Export inferred types
export type LoginFormValues = z.infer<typeof loginSchema>
export type RegisterFormValues = z.infer<typeof registerSchema>

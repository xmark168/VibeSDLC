const authService = require('../services/authService');
const AppError = require('../utils/AppError');

class AuthController {
  /**
   * Handles user registration.
   * Delegates to AuthService and formats the response.
   * @param {import('express').Request} req
   * @param {import('express').Response} res
   * @param {Function} next
   */
  async register(req, res, next) {
    try {
      const result = await authService.registerUser(req.body);
      // Format response: only user (no password hash) and token
      res.status(201).json({
        user: result.user,
        token: result.token
      });
    } catch (err) {
      // Pass error to error middleware
      next(err instanceof AppError ? err : new AppError(err.message || 'Registration failed', 500));
    }
  }
}

module.exports = new AuthController();

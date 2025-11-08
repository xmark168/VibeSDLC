const authService = require('../services/authService');
const loginSchema = require('../utils/loginSchema');
const loginResponseDto = require('../dtos/loginResponseDto');

class AuthController {
  /**
   * Register a new user
   * @param {import('express').Request} req
   * @param {import('express').Response} res
   * @param {Function} next
   */
  async register(req, res, next) {
    try {
      const userData = req.body;
      const user = await authService.registerUser(userData);
      res.status(201).json({ user });
    } catch (err) {
      next(err);
    }
  }

  /**
   * Login user
   * @param {import('express').Request} req
   * @param {import('express').Response} res
   * @param {Function} next
   */
  async login(req, res, next) {
    try {
      const { error, value } = loginSchema.validate(req.body, { abortEarly: false });
      if (error) {
        return res.status(400).json({
          errors: error.details.map(e => e.message)
        });
      }
      const { email, password } = value;
      const { user, token } = await authService.loginUser(email, password);
      res.status(200).json(loginResponseDto(user, token));
    } catch (err) {
      if (err.statusCode) {
        return res.status(err.statusCode).json({ error: err.message });
      }
      next(err);
    }
  }
}

module.exports = new AuthController();
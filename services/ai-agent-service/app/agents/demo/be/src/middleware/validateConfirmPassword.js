const Joi = require('joi');

// Schema for password + confirm_password validation
const passwordWithConfirmSchema = Joi.object({
  password: Joi.string().min(8).required(),
  confirm_password: Joi.string().required().valid(Joi.ref('password')).messages({
    'any.only': 'Confirm password must match password',
    'any.required': 'Confirm password is required'
  })
});

/**
 * Middleware to validate password and confirm_password in req.body
 * Usage: app.post('/route', validateConfirmPassword, ...)
 */
function validateConfirmPassword(req, res, next) {
  const { error } = passwordWithConfirmSchema.validate(req.body, { abortEarly: false });
  if (error) {
    return res.status(400).json({
      message: 'Validation error',
      details: error.details.map(d => d.message)
    });
  }
  next();
}

module.exports = validateConfirmPassword;

const Joi = require('joi');

const registerSchema = Joi.object({
  email: Joi.string().email().required().messages({
    'string.base': 'Email must be a string',
    'string.email': 'Email must be a valid email address',
    'any.required': 'Email is required'
  }),
  password: Joi.string().min(8).max(128).required().messages({
    'string.base': 'Password must be a string',
    'string.min': 'Password must be at least 8 characters',
    'string.max': 'Password must be at most 128 characters',
    'any.required': 'Password is required'
  }),
  confirm_password: Joi.string().valid(Joi.ref('password')).required().messages({
    'any.only': 'Confirm password must match password',
    'any.required': 'Confirm password is required',
    'string.base': 'Confirm password must be a string'
  })
});

module.exports = registerSchema;

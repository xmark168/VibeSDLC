const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const validateConfirmPassword = require('../middleware/validateConfirmPassword');

// POST /api/auth/register
router.post('/api/auth/register', validateConfirmPassword, authController.register);

module.exports = router;
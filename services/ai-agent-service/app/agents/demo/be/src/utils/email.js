const nodemailer = require('nodemailer');
const config = require('../config');

// Configure transporter (example uses Gmail, replace with your SMTP settings)
const transporter = nodemailer.createTransport({
  service: process.env.EMAIL_SERVICE || 'gmail',
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS,
  },
});

/**
 * Send an email
 * @param {string} to - Recipient email address
 * @param {string} subject - Email subject
 * @param {string} html - HTML content
 * @returns {Promise<void>}
 */
async function sendEmail(to, subject, html) {
  const mailOptions = {
    from: process.env.EMAIL_FROM || process.env.EMAIL_USER,
    to,
    subject,
    html,
  };
  await transporter.sendMail(mailOptions);
}

module.exports = { sendEmail };
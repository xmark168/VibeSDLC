/**
 * Express.js Basic Application
 * Main application entry point with middleware and routes setup.
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const logger = require('./utils/logger');
const compression = require('compression');
const rateLimit = require('express-rate-limit');

const config = require('./config');




// Create Express app
const app = express();


// Security middleware
app.use(helmet());

// CORS configuration
app.use(cors({
  origin: config.CORS_ORIGINS,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: {
    error: 'Too many requests from this IP, please try again later.',
  },
});
app.use('/api/', limiter);

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Compression middleware
app.use(compression());

// Logging middleware
if (config.NODE_ENV !== 'test') {
  app.use(morgan('combined', {
    stream: {
      write: (message) => logger.http(message.trim()),
    },
  }));
}

// Swagger API docs
const { swaggerUi, specs } = require('./swagger');
app.use('/api/v1/docs', swaggerUi.serve, swaggerUi.setup(specs));

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'Express Basic API',
    version: '1.0.0',
    documentation: '/api/v1/docs',
    health: '/health',
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `Route ${req.originalUrl} not found`,
    statusCode: 404,
  });
});

// Error handling middleware (must be last)
const errorHandler = require('./middleware/errorHandler');
app.use(errorHandler);

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  process.exit(0);
});

// Start server
// const PORT = config.PORT || 3000;

if (require.main === module) {
  app.listen(3000, () => {
    // logger.info(`🚀 Server running on port ${PORT}`);
    // logger.info(`📚 Environment: ${config.NODE_ENV}`);
    // logger.info(`🔗 Health check: http://localhost:${PORT}/health`);
    console.log('success')
  });
}

module.exports = app;

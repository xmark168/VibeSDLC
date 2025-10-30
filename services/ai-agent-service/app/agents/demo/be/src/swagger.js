const swaggerUi = require('swagger-ui-express');
const swaggerDocument = require('./swagger.json');

module.exports = (app) => {
  app.use('/api/v1/docs', swaggerUi.serve, swaggerUi.setup(swaggerDocument));
};
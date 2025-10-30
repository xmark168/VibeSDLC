const request = require('supertest');
const express = require('express');
const authRoutes = require('../../routes/auth');
const errorHandler = require('../../middleware/errorHandler');
const mongoose = require('mongoose');
const User = require('../../models/User');

const app = express();
app.use(express.json());
app.use(authRoutes);
app.use(errorHandler);

// Setup and teardown for DB
beforeAll(async () => {
  const url = 'mongodb://127.0.0.1/vibe_test_db';
  await mongoose.connect(url, { useNewUrlParser: true, useUnifiedTopology: true });
});
afterAll(async () => {
  await mongoose.connection.db.dropDatabase();
  await mongoose.disconnect();
});
afterEach(async () => {
  await User.deleteMany({});
});

describe('POST /api/auth/register', () => {
  it('should register a user successfully', async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        email: 'newuser@example.com',
        password: 'Password123!',
        confirmPassword: 'Password123!'
      });
    expect(res.statusCode).toBe(201);
    expect(res.body).toHaveProperty('user');
    expect(res.body.user).toHaveProperty('_id');
    expect(res.body.user.email).toBe('newuser@example.com');
    expect(res.body).toHaveProperty('token');
    expect(res.body.user).not.toHaveProperty('password_hash');
  });

  it('should fail if email is missing', async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({ password: 'Password123!', confirmPassword: 'Password123!' });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('message');
  });

  it('should fail if password is missing', async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({ email: 'user@example.com', confirmPassword: 'Password123!' });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('message');
  });

  it('should fail if confirmPassword does not match password', async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        email: 'user@example.com',
        password: 'Password123!',
        confirmPassword: 'Password456!'
      });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('message');
  });

  it('should fail if email is invalid', async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        email: 'not-an-email',
        password: 'Password123!',
        confirmPassword: 'Password123!'
      });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('message');
  });

  it('should fail if email is duplicate', async () => {
    await User.create({ email: 'dupe@example.com', password_hash: 'hashed' });
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        email: 'dupe@example.com',
        password: 'Password123!',
        confirmPassword: 'Password123!'
      });
    expect(res.statusCode).toBe(409);
    expect(res.body).toHaveProperty('message');
  });
});

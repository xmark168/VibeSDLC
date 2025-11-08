const request = require('supertest');
const mongoose = require('mongoose');
const app = require('../../app');
const User = require('../../models/User');
const connectDB = require('../../db/mongoose');

const testUser = {
  email: 'loginuser@example.com',
  password: 'Password123!'
};

beforeAll(async () => {
  process.env.MONGODB_URI = process.env.MONGODB_URI_TEST || 'mongodb://localhost:27017/vibesdlc_test';
  await connectDB();
  await User.deleteMany({});
  // Register user for login test
  const user = new User({
    email: testUser.email,
    password_hash: testUser.password
  });
  await user.save();
});

afterAll(async () => {
  await User.deleteMany({});
  await mongoose.connection.close();
});

describe('POST /api/auth/login', () => {
  it('should login successfully with valid credentials', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: testUser.email, password: testUser.password });
    expect(res.statusCode).toBe(200);
    expect(res.body).toHaveProperty('user');
    expect(res.body.user).toHaveProperty('_id');
    expect(res.body.user.email).toBe(testUser.email);
    expect(res.body).toHaveProperty('token');
    expect(typeof res.body.token).toBe('string');
  });

  it('should fail with invalid password', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: testUser.email, password: 'WrongPassword123!' });
    expect(res.statusCode).toBe(401);
    expect(res.body).toHaveProperty('error');
    expect(res.body.error).toMatch(/invalid email or password/i);
  });

  it('should fail with non-existent email', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: 'notfound@example.com', password: 'Password123!' });
    expect(res.statusCode).toBe(401);
    expect(res.body).toHaveProperty('error');
    expect(res.body.error).toMatch(/invalid email or password/i);
  });

  it('should fail with missing email', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ password: testUser.password });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('errors');
    expect(Array.isArray(res.body.errors)).toBe(true);
    expect(res.body.errors).toEqual(expect.arrayContaining([
      expect.stringMatching(/email is required/i)
    ]));
  });

  it('should fail with missing password', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: testUser.email });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('errors');
    expect(Array.isArray(res.body.errors)).toBe(true);
    expect(res.body.errors).toEqual(expect.arrayContaining([
      expect.stringMatching(/password is required/i)
    ]));
  });

  it('should fail with invalid email format', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: 'not-an-email', password: testUser.password });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('errors');
    expect(Array.isArray(res.body.errors)).toBe(true);
    expect(res.body.errors).toEqual(expect.arrayContaining([
      expect.stringMatching(/email must be a valid email address/i)
    ]));
  });

  it('should fail with short password', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: testUser.email, password: 'short' });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('errors');
    expect(Array.isArray(res.body.errors)).toBe(true);
    expect(res.body.errors).toEqual(expect.arrayContaining([
      expect.stringMatching(/password must be at least 8 characters/i)
    ]));
  });
});

import type { NextAuthConfig } from 'next-auth';
import bcrypt from 'bcryptjs';
import { PrismaClient } from '@prisma/client';
import { PrismaAdapter } from '@next-auth/prisma-adapter';

const prisma = new PrismaClient();

export const authOptions: NextAuthConfig = {
  // Configure one or more authentication providers
  adapter: PrismaAdapter(prisma),
  providers: [
    // Credentials Provider for email/password authentication
    {
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email', placeholder: 'your-email@example.com' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials, req) {
        try {
          // Validate credentials
          if (!credentials?.email || !credentials?.password) {
            return null;
          }

          // Find user by email
          const user = await prisma.user.findUnique({
            where: {
              email: credentials.email as string,
            },
          });

          // If user not found or password doesn't match, return null
          if (!user || !(await bcrypt.compare(credentials.password as string, user.hashedPassword))) {
            return null;
          }

          // Return user object for successful authentication
          return {
            id: user.id,
            email: user.email,
            username: user.username,
          };
        } catch (error) {
          console.error('Authorization error:', error);
          return null;
        }
      },
    },
  ],

  // Configure session management
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },

  // Configure JWT
  jwt: {
    secret: process.env.NEXTAUTH_SECRET,
  },

  // Configure pages
  pages: {
    signIn: '/login',
    error: '/auth/error',
  },

  // Configure callbacks
  callbacks: {
    async jwt({ token, user }) {
      // On initial sign in, add user data to token
      if (user) {
        token.id = user.id;
        token.email = user.email;
        token.username = user.username;
      }
      return token;
    },

    async session({ session, token }) {
      // Add user data to session
      if (token) {
        session.user = {
          id: token.id as string,
          email: token.email as string,
          username: token.username as string,
        };
      }
      return session;
    },
  },

  // Enable debug in development
  debug: process.env.NODE_ENV === 'development',

  // Configure secret
  secret: process.env.NEXTAUTH_SECRET,
};
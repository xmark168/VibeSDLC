# NextAuth.js v5 Integration Guide

## Overview
NextAuth.js v5 (Auth.js) đã được tích hợp vào boilerplate với **Credentials provider** và **JWT session strategy**.

## 📦 Installed Packages

```json
{
  "next-auth": "^5.0.0-beta",
  "@auth/prisma-adapter": "^latest",
  "bcryptjs": "^latest"
}
```

## 🗄️ Database Schema

Prisma schema đã được update với NextAuth models:

- **User**: Extended với `email`, `emailVerified`, `image`
- **Account**: OAuth accounts
- **Session**: Database sessions (nếu dùng database strategy)
- **VerificationToken**: Email verification tokens

## 🚀 Setup Instructions

### 1. Database Migration

Chạy migration để tạo tables:

```bash
npx prisma migrate dev --name add_nextauth_models
npx prisma generate
```

**Note**: Nếu gặp lỗi authentication, check `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/database_name
AUTH_SECRET=your-super-secret-key-change-this-in-production
AUTH_URL=http://localhost:3000
```

### 2. Generate AUTH_SECRET

Trong production, generate secure AUTH_SECRET:

```bash
npx auth secret
```

Hoặc:

```bash
openssl rand -base64 32
```

## 📁 File Structure

```
demo/
├── src/
│   ├── auth.ts                          # NextAuth configuration
│   ├── middleware.ts                    # Auth middleware cho protected routes
│   ├── types/
│   │   └── next-auth.d.ts              # TypeScript type extensions
│   ├── components/
│   │   └── SessionProvider.tsx         # Client-side session provider
│   └── app/
│       ├── api/
│       │   └── auth/
│       │       └── [...nextauth]/
│       │           └── route.ts        # NextAuth API handler
│       └── layout.tsx                   # Root layout with SessionProvider
└── prisma/
    └── schema.prisma                    # Updated with NextAuth models
```

## 🔧 Configuration

### Auth Config (`src/auth.ts`)

```typescript
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { PrismaAdapter } from "@auth/prisma-adapter";
import { prisma } from "@/lib/prisma";
import bcrypt from "bcryptjs";

export const { handlers, signIn, signOut, auth } = NextAuth({
  adapter: PrismaAdapter(prisma),
  session: {
    strategy: "jwt", // Stateless JWT sessions
  },
  providers: [
    Credentials({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        // Authentication logic
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      // Add custom fields to JWT
    },
    async session({ session, token }) {
      // Add custom fields to session
    },
  },
  pages: {
    signIn: "/login", // Custom login page
  },
});
```

### Middleware (`src/middleware.ts`)

```typescript
export { auth as middleware } from "@/auth";

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
```

**Current config**: Middleware runs on ALL routes. Update `matcher` để protect specific routes:

```typescript
// Example: Only protect /dashboard và /profile
export const config = {
  matcher: ["/dashboard/:path*", "/profile/:path*"],
};
```

## 💻 Usage Examples

### Server Components (Server-side)

```typescript
import { auth } from "@/auth";

export default async function ProtectedPage() {
  const session = await auth();

  if (!session) {
    return <div>Not authenticated</div>;
  }

  return (
    <div>
      <h1>Welcome, {session.user.username}!</h1>
      <p>User ID: {session.user.id}</p>
    </div>
  );
}
```

### Client Components (Client-side)

```typescript
"use client";

import { useSession, signIn, signOut } from "next-auth/react";

export default function UserProfile() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <div>Loading...</div>;
  }

  if (status === "unauthenticated") {
    return (
      <button onClick={() => signIn()}>
        Sign in
      </button>
    );
  }

  return (
    <div>
      <p>Signed in as {session.user.username}</p>
      <button onClick={() => signOut()}>
        Sign out
      </button>
    </div>
  );
}
```

### API Routes

```typescript
import { auth } from "@/auth";
import { NextResponse } from "next/server";

export async function GET() {
  const session = await auth();

  if (!session) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  return NextResponse.json({
    message: "Protected data",
    userId: session.user.id,
  });
}
```

### Sign In/Out Programmatically

```typescript
import { signIn, signOut } from "@/auth";

// Sign in (Server Action)
await signIn("credentials", {
  username: "john",
  password: "password123",
  redirect: false,
});

// Sign out
await signOut();
```

## 🔐 Creating Users

Users phải được hash password với bcrypt trước khi save:

```typescript
import bcrypt from "bcryptjs";
import { prisma } from "@/lib/prisma";

async function createUser(username: string, password: string) {
  const hashedPassword = await bcrypt.hash(password, 10);

  const user = await prisma.user.create({
    data: {
      username,
      password: hashedPassword,
      email: null, // Optional
    },
  });

  return user;
}
```

## 🎨 Protected Routes Strategy

### Option 1: Middleware-based (Current)

Middleware checks authentication cho ALL routes. Update `matcher` để customize.

**Pros**: Automatic protection, runs before page loads  
**Cons**: Runs on every request

### Option 2: Component-based

Check session trong component và redirect manually:

```typescript
"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ProtectedPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "loading") return <div>Loading...</div>;
  if (!session) return null;

  return <div>Protected content</div>;
}
```

## 🧪 Testing Authentication

### 1. Create test user

```bash
# Via Prisma Studio
npx prisma studio

# Or via code (remember to hash password!)
```

### 2. Test sign in

```typescript
await signIn("credentials", {
  username: "testuser",
  password: "testpassword",
  callbackUrl: "/dashboard",
});
```

### 3. Check session

```typescript
const session = await auth();
console.log(session);
```

## 📝 TypeScript Support

Type definitions extended in `src/types/next-auth.d.ts`:

```typescript
declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      username: string;
    } & DefaultSession["user"];
  }

  interface User {
    username: string;
  }
}
```

Autocomplete sẽ work cho `session.user.username` và `session.user.id`.

## 🔮 Next Steps (Optional)

### Add OAuth Providers

```bash
npm install @auth/core
```

```typescript
// In src/auth.ts
import Google from "next-auth/providers/google";

providers: [
  Google({
    clientId: process.env.GOOGLE_CLIENT_ID,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  }),
  Credentials({...}),
]
```

### Add Email Verification

Sử dụng `VerificationToken` model để send verification emails.

### Database Sessions

Change strategy từ `jwt` sang `database`:

```typescript
session: {
  strategy: "database",
  maxAge: 30 * 24 * 60 * 60, // 30 days
}
```

## 🐛 Troubleshooting

### Error: "No database adapter found"

**Fix**: Make sure `@auth/prisma-adapter` installed và configured trong `auth.ts`.

### Error: "JWT secret not set"

**Fix**: Add `AUTH_SECRET` to `.env` file.

### Session không persist

**Fix**: Check `AUTH_URL` trong `.env` match với current dev URL (default: `http://localhost:3000`).

### TypeScript errors với session types

**Fix**: Restart TypeScript server (`Cmd/Ctrl + Shift + P` → "Restart TS Server").

## 📚 Resources

- [NextAuth.js v5 Docs](https://authjs.dev/)
- [Prisma Adapter](https://authjs.dev/reference/adapter/prisma)
- [Credentials Provider](https://authjs.dev/reference/core/providers_credentials)
- [JWT Strategy](https://authjs.dev/concepts/session-strategies#jwt)

---

**Status**: ✅ NextAuth v5 integration complete  
**Session Strategy**: JWT (stateless)  
**Providers**: Credentials (username/password)  
**Database**: PostgreSQL via Prisma

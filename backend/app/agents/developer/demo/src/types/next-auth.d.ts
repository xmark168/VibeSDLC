// NextAuth.js type extensions
import type { DefaultSession, DefaultUser } from "next-auth";
import type { AdapterUser } from "next-auth/adapters";

/**
 * Module augmentation for `next-auth` types.
 * Allows us to add custom properties to the `session` object and keep type safety.
 *
 * @see https://next-auth.js.org/getting-started/typescript#module-augmentation
 */
declare module "next-auth" {
  /**
   * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` component.
   */
  interface Session extends DefaultSession {
    user?: {
      id: string;
      email?: string;
      username?: string;
    } & DefaultSession["user"];
  }

  interface User extends DefaultUser {
    username?: string;
    email?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT extends DefaultJWT {
    id?: string;
    username?: string;
    email?: string;
  }
}
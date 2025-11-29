import bcrypt from "bcryptjs";
import { prisma } from "@/lib/prisma";

export async function createUser(data: {
  username: string;
  password: string;
  email?: string;
}) {
  const hashedPassword = await bcrypt.hash(data.password, 10);

  const user = await prisma.user.create({
    data: {
      username: data.username,
      password: hashedPassword,
      email: data.email || null,
    },
  });

  return {
    id: user.id,
    username: user.username,
    email: user.email,
    createdAt: user.createdAt,
  };
}

export async function verifyPassword(password: string, hashedPassword: string) {
  return bcrypt.compare(password, hashedPassword);
}

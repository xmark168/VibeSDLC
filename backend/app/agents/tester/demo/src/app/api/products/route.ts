// Minimal mock API route for products (for test import)
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  return NextResponse.json({ message: 'Mocked product created' }, { status: 201 });
}

export async function GET(request: Request) {
  return NextResponse.json({ products: [] }, { status: 200 });
}

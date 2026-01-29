import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    NEXTAUTH_URL: process.env.NEXTAUTH_URL || null,
    NEXTAUTH_SECRET_SET: Boolean(process.env.NEXTAUTH_SECRET),
    BACKEND_URL: process.env.BACKEND_URL || null,
    NODE_ENV: process.env.NODE_ENV || null,
  })
}


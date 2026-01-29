import { NextResponse } from 'next/server'

const backendBase = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}))
    const res = await fetch(`${backendBase}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    const data = await res.json().catch(() => ({}))
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json(
      { error: e?.message || 'Unable to complete token login' },
      { status: 500 },
    )
  }
}

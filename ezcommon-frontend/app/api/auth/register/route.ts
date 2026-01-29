import { NextResponse } from 'next/server'

const backendBase = process.env.BACKEND_URL || 'https://ezcollegeapp1.com'

export async function POST(request: Request) {
  try {
    const payload = await request.json()

    const res = await fetch(`${backendBase}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const responseBody = await res.text()

    return new NextResponse(responseBody, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('content-type') ?? 'application/json',
      },
    })
  } catch (e) {
    console.error('Register proxy failed:', e)
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}

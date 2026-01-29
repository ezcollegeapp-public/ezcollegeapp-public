import { NextResponse } from 'next/server'

const backendBase = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}))
    // Prefer body refresh_token, fall back to cookie passthrough
    const res = await fetch(`${backendBase}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      credentials: 'include',
    })

    const data = await res.json().catch(() => ({}))
    // Bubble up set-cookie headers from backend if any
    const resp = NextResponse.json(data, { status: res.status })
    const setCookie = res.headers.get('set-cookie')
    if (setCookie) {
      resp.headers.set('set-cookie', setCookie)
    }
    return resp
  } catch (e: any) {
    return NextResponse.json(
      { error: e?.message || 'Unable to refresh token' },
      { status: 500 },
    )
  }
}

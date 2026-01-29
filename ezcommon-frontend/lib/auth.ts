import NextAuth, { type NextAuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import GoogleProvider from 'next-auth/providers/google'
import { z } from 'zod'

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  remember: z.union([z.literal('true'), z.literal('false')]).optional(),
  // login_type is used to distinguish student vs organization login
  login_type: z.union([z.literal('student'), z.literal('org')]).optional(),
})

type TokenResponse = {
  access_token: string
  refresh_token: string
  expires_in?: number
  refresh_expires_in?: number
  user: any
}

async function refreshAccessToken(token: any) {
  try {
    const base = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
    const res = await fetch(`${base}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    })
    if (!res.ok) throw new Error('refresh failed')
    const data = (await res.json()) as TokenResponse
    const expiresInMs = (data.expires_in ?? 1800) * 1000
    return {
      ...token,
      accessToken: data.access_token,
      refreshToken: data.refresh_token || token.refreshToken,
      accessTokenExpires: Date.now() + expiresInMs,
    }
  } catch {
    return { ...token, accessToken: null, accessTokenExpires: 0 }
  }
}

export const authOptions: NextAuthOptions = {
  // Fallback secret to unblock local dev if env not loaded
  secret: process.env.NEXTAUTH_SECRET ?? 'dev-only-secret-change-me',
  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 1 day
  },
  jwt: {
    maxAge: 24 * 60 * 60, // 1 day
  },
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
        remember: { label: 'Remember', type: 'text' },
      },
      authorize: async (raw) => {
        const parsed = credentialsSchema.safeParse(raw)
        if (!parsed.success) return null
        const { email, password, remember, login_type } = parsed.data
        const base = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
        const requestedLoginType = login_type ?? 'student'

        try {
          const res = await fetch(`${base}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          })
          if (!res.ok) return null
          const data = (await res.json()) as TokenResponse | any
          const userPayload: any = (data as any)?.user ?? data

          // Enforce that the selected login type matches the user's role
          const role: string = userPayload.role ?? 'student'
          const isStudent = role === 'student'
          const isOrgUser = role === 'org_admin' || role === 'org_staff'

          if (requestedLoginType === 'student' && !isStudent) return null
          if (requestedLoginType === 'org' && !isOrgUser) return null

          const name = [userPayload.first_name, userPayload.last_name].filter(Boolean).join(' ')
          return {
            id: userPayload.id,
            email: userPayload.email,
            name,
            remember: remember === 'true',
            role,
            orgId: userPayload.org_id ?? null,
            accessToken: (data as any)?.access_token,
            refreshToken: (data as any)?.refresh_token,
            accessTokenExpiresIn: (data as any)?.expires_in,
          } as any
        } catch {
          return null
        }
      },
    }),
    ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
      ? [
          GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID!,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
          }),
        ]
      : []),
  ],
  callbacks: {
    async jwt({ token, user, trigger, session }) {
      // When user signs in, add their id and role/org info to the token
      if (user) {
        token.sub = (user as any).id
        ;(token as any).role = (user as any).role ?? 'student'
        ;(token as any).orgId = (user as any).orgId ?? null
      }

      if (user && (user as any).accessToken) {
        ;(token as any).accessToken = (user as any).accessToken
        ;(token as any).refreshToken = (user as any).refreshToken
        const expiresInMs = ((user as any).accessTokenExpiresIn ?? 1800) * 1000
        ;(token as any).accessTokenExpires = Date.now() + expiresInMs
      }

      const accessTokenExpires = (token as any).accessTokenExpires as number | undefined
      if (accessTokenExpires && Date.now() > accessTokenExpires - 60_000) {
        return await refreshAccessToken(token as any)
      }

      return token
    },
    async session({ session, token }) {
      // Add user id and role/org info to session from token
      if (session?.user && token?.sub) {
        ;(session.user as any).id = token.sub
        ;(session.user as any).role = (token as any).role ?? 'student'
        ;(session.user as any).orgId = (token as any).orgId ?? null
      }
      ;(session as any).accessToken = (token as any).accessToken ?? null
      return session
    },
  },
  pages: {
    signIn: '/auth/login',
  },
}

const handler = NextAuth(authOptions)
export { handler }

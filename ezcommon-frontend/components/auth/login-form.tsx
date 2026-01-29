"use client"
import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import Link from 'next/link'
import { signIn } from 'next-auth/react'

const LoginSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email' }),
  password: z.string().min(6, { message: 'At least 6 characters' }),
  remember: z.boolean().optional().default(false),
  // loginType controls whether the user logs in as a student or as an organization
  loginType: z.enum(['student', 'org']).default('student'),
})

type LoginValues = z.infer<typeof LoginSchema>

export function LoginForm() {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const appBase = process.env.NEXT_PUBLIC_APP_URL || '/'

  const form = useForm<LoginValues>({
    resolver: zodResolver(LoginSchema),
    defaultValues: {
      email: '',
      password: '',
      remember: false,
      loginType: 'student',
    },
  })

  const loginType = form.watch('loginType')

  useEffect(() => {
    const saved = window.localStorage.getItem('remember_device')
    if (saved === 'true') {
      form.setValue('remember', true)
    }
  }, [form])

  const onSubmit = useCallback(async (values: LoginValues) => {
    setError(null)
    setLoading(true)
    try {
      window.localStorage.setItem('remember_device', values.remember ? 'true' : 'false')
      const res = await signIn('credentials', {
        email: values.email,
        password: values.password,
        remember: values.remember ? 'true' : 'false',
        login_type: values.loginType === 'org' ? 'org' : 'student',
        // Always send users to the app root (public URL); server-side will redirect based on role
        callbackUrl: appBase,
        redirect: false,
      })
      try {
        const sessionResp = await fetch('/api/auth/session')
        const sessionJson = await sessionResp.json().catch(() => null)
        console.log('debug: signIn result =', res)
        console.log('debug: session =', sessionJson)
      } catch (e) {
        console.warn('debug: failed to read session', e)
      }
      if (res?.error) {
        setError(res.error)
      } else if (res?.url) {
        window.location.href = res.url
      } else {
        window.location.href = appBase
      }
    } catch (e) {
      setError('Failed to sign in')
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="mx-auto w-full max-w-sm">
      <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
      <p className="text-sm text-muted-foreground mt-1">Welcome back. Please enter your details.</p>

      <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <Label>Login as</Label>
          <div className="inline-flex rounded-md border p-1 text-xs">
            <button
              type="button"
              onClick={() => form.setValue('loginType', 'student')}
              className={`flex-1 rounded-sm px-3 py-1 ${loginType === 'student' ? 'bg-primary text-primary-foreground' : 'bg-background text-foreground'}`}
            >
              Student
            </button>
            <button
              type="button"
              onClick={() => form.setValue('loginType', 'org')}
              className={`flex-1 rounded-sm px-3 py-1 ${loginType === 'org' ? 'bg-primary text-primary-foreground' : 'bg-background text-foreground'}`}
            >
              Organization
            </button>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" placeholder="you@example.com" {...form.register('email')} />
          {form.formState.errors.email && (
            <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" placeholder="••••••••" {...form.register('password')} />
          {form.formState.errors.password && (
            <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>
          )}
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={form.watch('remember')} onCheckedChange={(v) => form.setValue('remember', Boolean(v))} />
            Remember this device
          </label>
          <Link href="#" className="text-sm text-primary hover:underline">Forgot password?</Link>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" disabled={loading} className="w-full">
          {loading ? 'Signing in...' : 'Sign In'}
        </Button>

        <div className="text-sm text-muted-foreground">
          Don&apos;t have an account?{' '}
          <Link href="/auth/register" className="text-primary hover:underline">Register</Link>
        </div>

        <div className="flex items-center gap-4">
          <Separator className="flex-1" />
          <span className="text-xs text-muted-foreground">Or log in with</span>
          <Separator className="flex-1" />
        </div>

        <Button type="button" variant="outline" className="w-full" onClick={() => signIn('google', { callbackUrl: '/' })}>
          <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
            <path fill="#EA4335" d="M12 10.2v3.6h5.1c-.2 1.2-1.5 3.6-5.1 3.6-3.1 0-5.7-2.6-5.7-5.7S8.9 6 12 6c1.8 0 3 .8 3.7 1.5l2.5-2.5C16.8 3.5 14.6 2.4 12 2.4 6.9 2.4 2.9 6.4 2.9 11.5S6.9 20.6 12 20.6c6 0 9.3-4.2 9.3-8.9 0-.6-.1-1-.1-1.5H12z" />
          </svg>
          Continue with Google
        </Button>
      </form>
    </div>
  )
}

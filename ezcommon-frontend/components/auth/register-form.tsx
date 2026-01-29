"use client"
import { useCallback, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import Link from 'next/link'
import { signIn } from 'next-auth/react'

const RegisterSchema = z
  .object({
    firstName: z.string().min(1, { message: 'First name is required' }),
    lastName: z.string().min(1, { message: 'Last name is required' }),
    email: z.string().email({ message: 'Please enter a valid email' }),
    password: z.string().min(6, { message: 'At least 6 characters' }),
    confirmPassword: z.string().min(6, { message: 'At least 6 characters' }),
    // role decides whether we create a student or an organization admin account
    role: z.enum(['student', 'org_admin']).default('student'),
    // Organization name is only required when role = org_admin
    orgName: z.string().max(200).optional(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })
  .refine(
    (data) => data.role === 'student' || !!data.orgName?.trim(),
    {
      message: 'Organization name is required for organization accounts',
      path: ['orgName'],
    },
  )

type RegisterValues = z.infer<typeof RegisterSchema>

export function RegisterForm() {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const form = useForm<RegisterValues>({
    resolver: zodResolver(RegisterSchema),
    defaultValues: {
      firstName: '',
      lastName: '',
      email: '',
      password: '',
      confirmPassword: '',
      role: 'student',
      orgName: '',
    },
  })

  const role = form.watch('role')

  const onSubmit = useCallback(async (values: RegisterValues) => {
    setError(null)
    setLoading(true)
    try {
      const isOrg = values.role === 'org_admin'
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: values.firstName,
          last_name: values.lastName,
          email: values.email,
          password: values.password,
          role: values.role,
          org_name: isOrg ? values.orgName : undefined,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data?.error || 'Failed to register')
      }
      const login = await signIn('credentials', {
        email: values.email,
        password: values.password,
        login_type: isOrg ? 'org' : 'student',
        callbackUrl: process.env.NEXT_PUBLIC_APP_URL || '/',
        redirect: false,
      })
      if (login?.error) throw new Error(login.error)
      window.location.href = process.env.NEXT_PUBLIC_APP_URL || '/'
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to register')
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="mx-auto w-full max-w-sm">
      <h1 className="text-2xl font-semibold tracking-tight">Register</h1>
      <p className="text-sm text-muted-foreground mt-1">Create your account.</p>

      <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <Label>Register as</Label>
          <div className="inline-flex rounded-md border p-1 text-xs">
            <button
              type="button"
              onClick={() => form.setValue('role', 'student')}
              className={`flex-1 rounded-sm px-3 py-1 ${role === 'student' ? 'bg-primary text-primary-foreground' : 'bg-background text-foreground'}`}
            >
              Student
            </button>
            <button
              type="button"
              onClick={() => form.setValue('role', 'org_admin')}
              className={`flex-1 rounded-sm px-3 py-1 ${role === 'org_admin' ? 'bg-primary text-primary-foreground' : 'bg-background text-foreground'}`}
            >
              Organization
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="firstName">First name</Label>
            <Input id="firstName" placeholder="John" {...form.register('firstName')} />
            {form.formState.errors.firstName && (
              <p className="text-sm text-destructive">{form.formState.errors.firstName.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="lastName">Last name</Label>
            <Input id="lastName" placeholder="Doe" {...form.register('lastName')} />
            {form.formState.errors.lastName && (
              <p className="text-sm text-destructive">{form.formState.errors.lastName.message}</p>
            )}
          </div>
        </div>


        {role === 'org_admin' && (
          <div className="space-y-2">
            <Label htmlFor="orgName">Organization name</Label>
            <Input
              id="orgName"
              placeholder="Your organization name"
              {...form.register('orgName')}
            />
            {form.formState.errors.orgName && (
              <p className="text-sm text-destructive">{form.formState.errors.orgName.message}</p>
            )}
          </div>
        )}

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

        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm password</Label>
          <Input id="confirmPassword" type="password" placeholder="••••••••" {...form.register('confirmPassword')} />
          {form.formState.errors.confirmPassword && (
            <p className="text-sm text-destructive">{form.formState.errors.confirmPassword.message}</p>
          )}
        </div>

        <p className="text-xs text-muted-foreground">
          By signing up you agree to our{' '}
          <Link href="/term" className="text-primary hover:underline">Terms and Conditions</Link>{' '}and{' '}
          <Link href="/policy" className="text-primary hover:underline">Privacy Policy</Link>.
        </p>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" disabled={loading} className="w-full">
          {loading ? 'Registering...' : 'Register'}
        </Button>

        <div className="text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link href="/auth/login" className="text-primary hover:underline">Log in</Link>
        </div>

        <div className="flex items-center gap-4">
          <Separator className="flex-1" />
          <span className="text-xs text-muted-foreground">Or register with</span>
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

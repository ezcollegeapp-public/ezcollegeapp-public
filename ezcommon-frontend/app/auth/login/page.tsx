import { LoginForm } from '@/components/auth/login-form'

export default function LoginPage() {
  return (
    <main className="min-h-screen w-full flex items-center justify-center px-4">
      <div className="w-full max-w-md border rounded-lg p-6 shadow-sm bg-card">
        <LoginForm />
      </div>
    </main>
  )
}


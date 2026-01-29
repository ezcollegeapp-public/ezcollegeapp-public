import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { redirect } from 'next/navigation'
import { AppLayout } from '@/components/layout/app-layout'

export default async function HomePage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/auth/login')

  const user: any = session.user || {}
  const role: string = user.role ?? 'student'

  // Organization users go to a separate dashboard experience
  if (role === 'org_admin' || role === 'org_staff') {
    redirect('/org/dashboard')
  }

  const name = user.name || user.email || 'User'
  const parts = name.split(' ').filter(Boolean)

  return (
    <AppLayout>
      <div className="p-6">
        <h1 className="text-2xl font-semibold">Welcome back{parts[0] ? `, ${parts[0]}` : ''}!</h1>
        <p className="text-muted-foreground mt-1">Use the menu to continue your application.</p>
      </div>
    </AppLayout>
  )
}

"use client"
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { AccountMenu } from '@/components/home/account-menu'
import { cn } from '@/lib/utils'
import { useEffect } from 'react'

interface MenuItem {
  label: string
  href: string
}

const menu: MenuItem[] = [
  { label: 'Profile', href: '/starter/profile' },
  { label: 'Education', href: '/starter/education' },
  { label: 'Activity', href: '/starter/activity' },
  { label: 'Testing', href: '/starter/testing' },
  { label: 'Review', href: '/files' },
  { label: 'Parse', href: '/parse' },
  { label: 'Invitations', href: '/starter/invitations' },
  { label: 'Setting', href: '/settings' },
]

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { data: session, status } = useSession()
  
  const name = session?.user?.name || session?.user?.email || 'User'
  const parts = name.split(' ').filter(Boolean)
  const initials = (parts[0]?.[0] || '') + (parts[1]?.[0] || '')

  return (
    <div className="min-h-screen w-full flex">
      <aside className="w-56 border-r bg-card p-4 flex-shrink-0">
        <div className="text-xl font-bold mb-6 text-primary">EZCommon</div>
        <nav className="flex flex-col gap-2">
          {menu.map((m) => {
            const isActive = pathname === m.href || pathname?.startsWith(m.href + '/')
            return (
              <Link
                key={m.href}
                href={m.href}
                className={cn(
                  "rounded-md px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors",
                  isActive && "bg-accent text-accent-foreground font-medium"
                )}
              >
                {m.label}
              </Link>
            )
          })}
        </nav>
      </aside>

      <main className="flex-1 flex flex-col">
        <header className="h-14 flex items-center justify-end px-4 border-b flex-shrink-0">
          <AccountMenu initials={initials.toUpperCase()} />
        </header>
        <section className="flex-1 overflow-auto">
          {children}
        </section>
      </main>
    </div>
  )
}

"use client"
import { useState, useEffect, useRef } from 'react'
import { signOut } from 'next-auth/react'
import { LogOut, User } from 'lucide-react'

export function AccountMenu({ initials }: { initials: string }) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // 点击外部区域关闭菜单
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  return (
    <div className="relative" ref={menuRef}>
      <button
        aria-label="Account"
        onClick={() => setOpen(!open)}
        className="h-9 w-9 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-semibold hover:bg-primary/90 transition-colors"
      >
        {initials.slice(0, 2)}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-48 rounded-md border bg-popover text-popover-foreground shadow-lg z-50">
          <div className="p-2">
            <button
              className="w-full flex items-center gap-2 text-left px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
              onClick={() => signOut({ callbackUrl: '/auth/login' })}
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  )
}


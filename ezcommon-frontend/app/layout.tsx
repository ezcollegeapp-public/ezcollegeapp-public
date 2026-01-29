import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'
import FloatingChatbot from '@/components/chatbot/floating-chatbot'

export const metadata: Metadata = {
  title: 'EZCommon',
  description: 'AI-powered college application autofill system',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          {children}
          <FloatingChatbot />
        </Providers>
      </body>
    </html>
  )
}


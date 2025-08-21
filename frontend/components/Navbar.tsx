'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Moon, Sun, Activity } from 'lucide-react'
import { useTheme } from 'next-themes'

const navigation = [
  // { name: 'Dashboard', href: '/' },
  { name: 'Users', href: '/users' },
  { name: 'Transactions', href: '/transactions' },
  // { name: 'Fraud Patterns', href: '/fraud-patterns' },
  // { name: 'Graph View', href: '/graph' },
  { name: 'Admin', href: '/admin' },
  { name: 'API Docs', href: '/docs' },
  { name: 'Zipkin', href: '/tracing' },
]

export default function Navbar() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/" className="flex items-center space-x-2">
              <Activity className="h-6 w-6" />
              <span className="font-bold">Fraud Detection</span>
            </Link>
            
            <div className="hidden md:flex space-x-4">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    pathname === item.href
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                  }`}
                >
                  {item.name}
                </Link>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  )
} 
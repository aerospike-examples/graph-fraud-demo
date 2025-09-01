import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Navbar from '@/components/Navbar'
import { Toaster } from "@/components/ui/sonner"

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Fraud Detection Dashboard',
  description: 'Real-time fraud detection using Aerospike Graph',
}

export default function RootLayout({
  	children,
}: {
  	children: React.ReactNode
}) {
  	return (
    	<html lang="en" suppressHydrationWarning>
      		<body className={inter.className}>
        		<div className="min-h-screen bg-background flex flex-col">
          			<Navbar />
					<main className="container relative mx-auto px-4 py-8 flex flex-col grow">
						{children}
					</main>
				</div>
				<Toaster richColors />
      		</body>
    	</html>
  	)
} 
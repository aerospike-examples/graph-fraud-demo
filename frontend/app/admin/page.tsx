'use server'

import Admin from '@/components/Admin'

export default async function AdminPage() {
  	return (
    	<div className="space-y-6">
      		<div className="flex items-center justify-between">
			<div>
				<h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
				<p className="text-muted-foreground">
					Manage transaction generation and fraud detection scenarios
				</p>
			</div>
      	</div>
      	<Admin />
    </div>
  )
} 
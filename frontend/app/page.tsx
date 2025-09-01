'use server'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, Shield } from 'lucide-react'
import Stat from '@/components/Stat'

interface DashboardStats {
	users: number
	txns: number
	flagged: number
	amount: number
	fraud_rate: number
	health: string
}

const API_BASE_URL = process.env.BASE_URL || "http://localhost:8080/api"

export default async function Dashboard() {
	const response = await fetch(`${API_BASE_URL}/dashboard/stats`, { cache: 'no-store' })
	const stats: DashboardStats = await response.json();

  	return (
    	<div className="space-y-6">
      		<div className="flex justify-between items-center">
        		<div>
          			<h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          			<p className="text-muted-foreground">Real-time fraud detection overview</p>
        		</div>
      		</div>
      		<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
				<Stat 
					title='Total Users'
					stat={stats?.users || 0}
					subtitle='Registered users in the system' 
					icon='users' />
				<Stat 
					title='Total Transactions'
					stat={stats?.txns || 0}
					subtitle='All processed transactions' 
					icon='credit-card' />
				<Stat 
					title='Flagged Transactions'
					stat={stats?.flagged || 0}
					subtitle='Suspicious transactions detected' 
					icon='alert-triangle'
					color='destructive' />
				<Stat 
					title='Total Amount'
					stat={`$${stats?.amount?.toLocaleString('en-US')}` || 0}
					subtitle='Total transaction volume' 
					icon='trending-up'
					color='green-600' />
      		</div>
			<div className="grid gap-4 md:grid-cols-2">
				<Card>
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<Activity className="h-5 w-5" />
							System Health
						</CardTitle>
					</CardHeader>
					<CardContent className='flex flex-col gap-2 items-start'>
						<Badge 
							variant={stats?.health === 'connected' ? 'default' : 'destructive'}
							className={stats?.health === 'connected' ? 'bg-green-600 hover:bg-green-700' : ''}
						>
							{stats?.health || 'unknown'}
						</Badge>
						<div className="text-sm text-muted-foreground">
							Graph database status
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<Shield className="h-5 w-5" />
							Fraud Detection Rate
						</CardTitle>
					</CardHeader>
					<CardContent>
						<div className="text-2xl font-bold">
							{stats?.fraud_rate?.toFixed(1) || '0'}%
						</div>
						<p className="text-sm text-muted-foreground">Accuracy of fraud detection</p>
					</CardContent>
				</Card>
      		</div>
    	</div>
  	)
} 
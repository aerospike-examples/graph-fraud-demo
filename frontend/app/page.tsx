import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
	Users, 
	CreditCard, 
	AlertTriangle, 
	TrendingUp,
	Activity,
	Shield
} from 'lucide-react'
import { api } from '@/lib/api'

interface DashboardStats {
	total_users: number
	total_transactions: number
	flagged_transactions: number
	total_amount: number
	fraud_detection_rate: number
	graph_health: string
}

export default async function Dashboard() {
	const response = await api.get('/dashboard/stats')
	const stats = response.data as DashboardStats;

  	return (
    	<div className="space-y-6">
      		<div className="flex justify-between items-center">
        		<div>
          			<h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          			<p className="text-muted-foreground">Real-time fraud detection overview</p>
        		</div>
      		</div>
      		<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        		<Card>
          			<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            			<CardTitle className="text-sm font-medium">Total Users</CardTitle>
            			<Users className="h-4 w-4 text-muted-foreground" />
          			</CardHeader>
          			<CardContent>
						<div className="text-2xl font-bold">{stats?.total_users || 0}</div>
						<p className="text-xs text-muted-foreground">Registered users in the system</p>
					</CardContent>
        		</Card>
        		<Card>
					<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
						<CardTitle className="text-sm font-medium">Total Transactions</CardTitle>
						<CreditCard className="h-4 w-4 text-muted-foreground" />
					</CardHeader>
					<CardContent>
						<div className="text-2xl font-bold">{stats?.total_transactions || 0}</div>
						<p className="text-xs text-muted-foreground">All processed transactions</p>
					</CardContent>
				</Card>
				<Card>
					<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
						<CardTitle className="text-sm font-medium">Flagged Transactions</CardTitle>
						<AlertTriangle className="h-4 w-4 text-muted-foreground" />
					</CardHeader>
					<CardContent>
						<div className="text-2xl font-bold text-destructive">
							{stats?.flagged_transactions || 0}
						</div>
						<p className="text-xs text-muted-foreground">Suspicious transactions detected</p>
					</CardContent>
				</Card>
				<Card>
					<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
						<CardTitle className="text-sm font-medium">Total Amount</CardTitle>
						<TrendingUp className="h-4 w-4 text-muted-foreground" />
					</CardHeader>
					<CardContent>
						<div className="text-2xl font-bold">
							${stats?.total_amount?.toLocaleString('en-US') || '0'}
						</div>
						<p className="text-xs text-muted-foreground">Total transaction volume</p>
					</CardContent>
				</Card>
      		</div>
			<div className="grid gap-4 md:grid-cols-2">
				<Card>
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<Activity className="h-5 w-5" />
							System Health
						</CardTitle>
					</CardHeader>
					<CardContent>
						<div className="flex items-center gap-2">
							<Badge 
								variant={stats?.graph_health === 'connected' ? 'default' : 'destructive'}
								className={stats?.graph_health === 'connected' ? 'bg-green-600 hover:bg-green-700' : ''}
							>
								{stats?.graph_health || 'unknown'}
							</Badge>
							<span className="text-sm text-muted-foreground">
								Graph database status
							</span>
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
							{stats?.fraud_detection_rate?.toFixed(1) || '0'}%
						</div>
						<p className="text-sm text-muted-foreground">Accuracy of fraud detection</p>
					</CardContent>
				</Card>
      		</div>
    	</div>
  	)
} 
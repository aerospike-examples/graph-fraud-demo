import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
	User, 
	Mail, 
	MapPin, 
	Calendar, 
	Shield,
	CreditCard,
	AlertTriangle,
	CheckCircle,
	TrendingUp,
	TrendingDown,
	Activity,
	Phone,
	Building
} from 'lucide-react'
import { api } from '@/lib/api'
import { type Account } from '@/components/UserDetails/Accounts';
import { type Transaction } from '@/components/UserDetails/Transactions';
import { type Device } from '@/components/UserDetails/Devices';
import Details from '@/components/UserDetails';
import { formatCurrency, formatDate, getRiskLevel } from '@/lib/utils';

interface User {
	id: string
	name: string
	email: string
	age: number
	signup_date: string
	location: string
	risk_score: number
	is_flagged: boolean
	phone?: string
	occupation?: string
}

export interface UserSummary {
	user: User
	accounts: Account[]
	recent_transactions: Transaction[]
	total_transactions: number
	total_amount_sent: number
	total_amount_received: number
	fraud_risk_level: string
	connected_users: string[]
	devices?: Device[]
}

export default async function UserDetailPage({ params }: { params: { id: string }}) {
  	const { id: userId } = params;
  	const response = await api.get(`/user/${userId}/summary`)
    const { user, ...userDetails } = response.data as UserSummary;
  	const risk = getRiskLevel(user.risk_score)

  	return (
    	<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-4">
					<div>
						<h1 className="text-3xl font-bold tracking-tight">{user.name}</h1>
						<p className="text-muted-foreground">User ID: {user.id}</p>
					</div>
				</div>
				<Badge variant={risk.color as any} className="text-lg px-4 py-2">
					{risk.level} Risk ({user.risk_score.toFixed(1)})
				</Badge>
			</div>
			<div className="grid gap-4 md:grid-cols-4">
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Total Transactions</p>
								<p className="text-2xl font-bold">{userDetails.total_transactions}</p>
							</div>
							<Activity className="h-8 w-8 text-muted-foreground" />
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Amount Sent</p>
								<p className="text-2xl font-bold text-destructive">{formatCurrency(userDetails.total_amount_sent)}</p>
							</div>
							<TrendingDown className="h-8 w-8 text-destructive" />
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Amount Received</p>
								<p className="text-2xl font-bold text-green-600">{formatCurrency(userDetails.total_amount_received)}</p>
							</div>
							<TrendingUp className="h-8 w-8 text-green-600" />
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Accounts</p>
								<p className="text-2xl font-bold">{userDetails.accounts.length}</p>
							</div>
							<CreditCard className="h-8 w-8 text-muted-foreground" />
						</div>
					</CardContent>
				</Card>
			</div>
            <div className="grid gap-4 md:grid-cols-2">
				<Card>
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<User className="h-5 w-5" />
							Personal Information
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<div className="grid grid-cols-2 gap-4">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Full Name</p>
								<p className="text-lg font-semibold">{user.name}</p>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Age</p>
								<p className="text-lg font-semibold">{user.age} years</p>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Email</p>
								<div className="flex items-center gap-2">
									<Mail className="h-4 w-4 text-muted-foreground" />
									<p className="text-lg font-semibold">{user.email}</p>
								</div>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Phone</p>
								<div className="flex items-center gap-2">
									<Phone className="h-4 w-4 text-muted-foreground" />
									<p className="text-lg font-semibold">{user.phone || 'N/A'}</p>
								</div>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Location</p>
								<div className="flex items-center gap-2">
									<MapPin className="h-4 w-4 text-muted-foreground" />
									<p className="text-lg font-semibold">{user.location}</p>
								</div>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Occupation</p>
								<div className="flex items-center gap-2">
									<Building className="h-4 w-4 text-muted-foreground" />
									<p className="text-lg font-semibold">{user.occupation || 'N/A'}</p>
								</div>
							</div>
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<Shield className="h-5 w-5" />
							Risk Assessment
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<div className="space-y-3">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Risk Score</p>
								<div className="flex items-center gap-2">
									<p className="text-2xl font-bold">{user.risk_score.toFixed(1)}</p>
									<Badge variant={risk.color as any}>{risk.level}</Badge>
								</div>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Signup Date</p>
								<div className="flex items-center gap-2">
									<Calendar className="h-4 w-4 text-muted-foreground" />
									<p className="text-lg font-semibold">{formatDate(user.signup_date)}</p>
								</div>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Account Status</p>
								<div className="flex items-center gap-2">
									{user.is_flagged ? (<>
										<AlertTriangle className="h-4 w-4 text-destructive" />
										<Badge variant="destructive">Flagged</Badge>
									</>) : (<>
										<CheckCircle className="h-4 w-4 text-green-600" />
										<Badge variant="default">Active</Badge>
									</>)}
								</div>
							</div>
						</div>
					</CardContent>
				</Card>
			</div>
			<Details userDetails={userDetails} userId={userId} />
		</div>
  	)
} 
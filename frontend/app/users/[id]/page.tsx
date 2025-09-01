'use server'

import { formatCurrency, formatDate } from '@/lib/utils';
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Details from '@/components/UserDetails';
import Stat from '@/components/Stat';
import Label from '@/components/Label'
import type { UserSummary } from '@/components/UserDetails'

const API_BASE_URL = process.env.BASE_URL || "http://localhost:8080/api"

export default async function UserDetailPage({ params }: { params: Promise<{ id: string }>}) {
  	const { id: userId } = await params;
  	const response = await fetch(`${API_BASE_URL}/users/${userId}`, { cache: 'no-store' })
    const { user, risk_level, ...userDetails }: UserSummary = await response.json();

  	return (
    	<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-4">
					<div>
						<h1 className="text-3xl font-bold tracking-tight">{user.name}</h1>
						<p className="text-muted-foreground">User ID: {user.id}</p>
					</div>
				</div>
				<Badge variant={risk_level === 'LOW' ? 'default' : 'destructive'} className="text-lg px-4 py-2">
					{risk_level} Risk ({user.risk_score.toFixed(1)})
				</Badge>
			</div>
			<div className="grid gap-4 md:grid-cols-4">
				<Stat
					title='Total Transactions'
					subtitle='Total transactions for this user'
					stat={userDetails.total_txns}
					icon='activity' />
				<Stat
					color='destructive'
					title='Amount Sent'
					subtitle='Total debit amount'
					stat={formatCurrency(userDetails.total_sent)}
					icon='trending-down' />
				<Stat
					color='green-600'
					title='Amount Received'
					subtitle='Total credit amount'
					stat={formatCurrency(userDetails.total_recd)}
					icon='trending-up' />
				<Stat
					title='Accounts'
					subtitle='Total accounts for this user'
					stat={userDetails.accounts.length}
					icon='credit-card' />
			</div>
            <div className="grid gap-4 md:grid-cols-2">
				<Card>
					<CardHeader>
						<Label
							size='2xl'
							className='font-semibold'
							icon="user"
							text='Personal Information' />
					</CardHeader>
					<CardContent className="grid grid-cols-2 gap-4">
						<Label
							size='lg'
							title='Full Name'
							text={user.name} />
						<Label
							size='lg'
							title='Age'
							text={`${user.age} years`} />
						<Label
							size='sm'
							title='Email'
							text={user.email}
							icon='mail' />
						<Label
							size='sm'
							title='Phone'
							text={user.phone}
							icon='phone' />
						<Label
							size='lg'
							title='Location'
							text={user.location}
							icon='map-pin' />
						<Label
							size='lg'
							title='Occupation'
							text={user.occupation ?? 'N/A'}
							icon='building' />
					</CardContent>
				</Card>
				<Card>
					<CardHeader>
						<Label
							size='2xl'
							className='font-semibold'
							icon="shield"
							text='Risk Assessment' />
					</CardHeader>
					<CardContent className="grid grid-cols-1 gap-4">
						<Label
							size='xl'
							title='Risk Score'
							className='font-semibold'
							text={user.risk_score.toFixed(1)}
							badge={{
								variant: risk_level === 'LOW' ? 'default' : 'destructive',
								text: risk_level
							}} />
						<Label
							size='sm'
							title='Signup Date'
							icon='calendar'
							text={formatDate(user.signup_date)} />
						<Label
							title='Account Status'
							icon={user.is_flagged ? 'alert-triangle' : 'check-circle'}
							color={user.is_flagged ? 'destructive' : 'green-600'}
							badge={{
								variant: user.is_flagged ? 'destructive' : 'default',
								text: user.is_flagged ? 'Flagged' : 'Active'
							}} />
					</CardContent>
				</Card>
			</div>
			<Details userDetails={{user, risk_level, ...userDetails}} />
		</div>
  	)
} 
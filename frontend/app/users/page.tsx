'use server'

import Lookup from '@/components/Lookup'
import Results from '@/components/ResultTable'
import Stat from '@/components/Stat'

interface UserStats {
	total_users: number
	total_low_risk: number
	total_med_risk: number
	total_high_risk: number
}

const API_BASE_URL = process.env.BACKEND_URL || "http://localhost:8080/api"

export default async function UsersPage() {
    const response = await fetch(`${API_BASE_URL}/users/stats`, { cache: 'no-store' })
    const { 
		total_users,
		total_low_risk,
		total_med_risk,
		total_high_risk
	}: UserStats = await response.json()
	
  	return (
    	<div className="space-y-6 flex flex-col grow">
			<div>
				<h1 className="text-3xl font-bold tracking-tight">User Explorer</h1>
				<p className="text-muted-foreground">Browse and search user profiles with detailed information</p>
			</div>
			<div className="grid gap-4 md:grid-cols-4">
				<Stat
					title='Total Users'
					subtitle='Total users in system'
					stat={total_users}
					icon='users' />
				<Stat
					color='destructive'
					title='High Risk'
					subtitle='Total users with a risk score > 70'
					stat={total_high_risk}
					icon='shield' />
				<Stat
					title='Medium Risk'
					subtitle='Total users with a risk score > 25 & < 70'
					stat={total_med_risk}
					icon='shield' />
				<Stat
					color='green-600'
					title='Low Risk'
					subtitle='Total users with a risk score > 25'
					stat={total_low_risk}
					icon="shield" />
			</div>
			<Results 
				searchType='user'
				title='Users'
				options={[
					{
						name: "Name",
						key: 'name',
						sortable: true,
						defaultSort: true,
						label: {
							size: 'md',
							text: 'name',
							icon: 'user'
						}
					},
					{
						name: "ID",
						key: 'id',
						label: {
							subtitle: 'id'
						}
					},
					{
						name: "Email",
						key: 'email',
						label: {
							size: 'sm',
							text: 'email',
							icon: 'mail',
							className: 'lowercase'
						}
					},
					{
						name: "Location",
						key: 'location',
						label: {
							size: 'sm',
							text: 'location',
							icon: 'map-pin'
						}
					},
					{
						name: "Age",
						key: 'age',
						label: {
							size: 'sm',
							text: 'age'
						}
					},
					{
						name: "Risk Score",
						key: 'risk_score',
						type: 'risk',
						sortable: true,
						label: {
							badge: {
								text: 'risk_score',
							}
						}
					},
					{
						name: "Signup Date",
						key: 'signup_date',
						type: 'date',
						sortable: true,
						label: {
							size: 'sm',
							text: 'signup_date',
							icon: 'calendar'
						}
					}
				]}
				path='/api/users' />
    	</div>
  	)
}
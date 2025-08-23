import { Card, CardContent } from '@/components/ui/card'
import { User, Shield } from 'lucide-react'
import { api } from '@/lib/api'
import Lookup from '@/components/Lookup'
import Results from '@/components/ResultTable'

interface User {
	id: string
	name: string
	email: string
	age: number
	signup_date: string
	location: string
	risk_score: number
	is_flagged: boolean
}

interface PaginatedUsers {
	users: User[]
	total: number
	page: number
	page_size: number
	total_pages: number
}

export default async function UsersPage() {
    const response = await api.get('/users')
    const { users, total, total_pages }: PaginatedUsers = response.data
	
  	return (
    	<div className="space-y-6 flex flex-col grow">
			<div>
				<h1 className="text-3xl font-bold tracking-tight">User Explorer</h1>
				<p className="text-muted-foreground">Browse and search user profiles with detailed information</p>
			</div>
			<Lookup />
			<div className="grid gap-4 md:grid-cols-4">
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Total Users</p>
								<p className="text-2xl font-bold">{total}</p>
							</div>
							<User className="h-8 w-8 text-muted-foreground" />
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">High Risk</p>
								<p className="text-2xl font-bold text-destructive">
									{users.filter(u => u.risk_score >= 70).length}
								</p>
							</div>
							<Shield className="h-8 w-8 text-destructive" />
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Medium Risk</p>
								<p className="text-2xl font-bold text-warning">
									{users.filter(u => u.risk_score >= 25 && u.risk_score < 70).length}
								</p>
							</div>
							<Shield className="h-8 w-8 text-warning" />
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Low Risk</p>
								<p className="text-2xl font-bold text-green-600">
								{users.filter(u => u.risk_score < 25).length}
								</p>
							</div>
							<Shield className="h-8 w-8 text-green-600" />
						</div>
					</CardContent>
				</Card>
			</div>
			<Results 
				title='Users'
				options={[
					{
						name: "Name",
						key: 'name',
						sortable: true,
						defaultSort: true,
						icon: 'user',
						renderer: 'medium'
					},
					{
						name: "ID",
						key: 'id',
						renderer: 'muted'
					},
					{
						name: "Email",
						key: 'email',
						icon: 'mail',
						renderer: 'small'
					},
					{
						name: "Location",
						key: 'location',
						icon: 'map',
						renderer: 'small'
					},
					{
						name: "Age",
						key: 'age',
						renderer: 'small'
					},
					{
						name: "Risk Score",
						key: 'risk_score',
						sortable: true,
						renderer: 'risk'
					},
					{
						name: "Signup Date",
						key: 'signup_date',
						type: 'date',
						sortable: true,
						icon: 'calendar',
						renderer: 'small'
					}
				]}
				path='/api/users'
				dataKey='users'
				totalPages={total_pages}
				totalEntries={total} />
    	</div>
  	)
} 
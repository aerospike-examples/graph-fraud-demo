import { Card, CardContent } from '@/components/ui/card'
import { CreditCard, Shield } from 'lucide-react'
import { api } from '@/lib/api'
import Results from '@/components/ResultTable'

export interface Transaction {
	id: string
	amount: number
	currency: string
	timestamp: string
	status: string
	method: string
	ip_address?: string
	location_city?: string
	location_country?: string
	latitude?: number
	longitude?: number
	fraud_score?: number
	fraud_status?: string
	fraud_reason?: string
	transaction_type?: string
	is_fraud?: boolean
	fraud_type?: string
}

interface TransactionStats {
	total_txns: number
	total_blocked: number
	total_review: number
	total_clean: number
}

export default async function TransactionsPage() {
  	const response = await api.get('/transactions/stats')
	const { total_txns, total_blocked, total_review, total_clean }: TransactionStats = response.data 
  
  	return (
    	<div className="space-y-6 flex flex-col grow">
      		<div className="flex items-center justify-between">
        		<div>
          			<h1 className="text-3xl font-bold tracking-tight">Transaction Explorer</h1>
          			<p className="text-muted-foreground">Search and explore transaction details and patterns.</p>
        		</div>
      		</div>
			<div className="grid gap-4 md:grid-cols-4">
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Total Transactions</p>
								<p className="text-2xl font-bold">{total_txns}</p>
							</div>
							<CreditCard className="h-8 w-8 text-muted-foreground" />
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-4">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-sm font-medium text-muted-foreground">Blocked</p>
								<p className="text-2xl font-bold text-destructive">
									{total_blocked}
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
								<p className="text-sm font-medium text-muted-foreground">Review</p>
								<p className="text-2xl font-bold text-warning">
									{total_review}
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
								<p className="text-sm font-medium text-muted-foreground">Clean</p>
								<p className="text-2xl font-bold text-green-600">
									{total_clean}
								</p>
							</div>
							<Shield className="h-8 w-8 text-green-600" />
						</div>
					</CardContent>
				</Card>
			</div>
			<Results 
				title='Transactions'
				options={[
					{
						name: 'Transaction ID',
						key: 'id',
						icon: 'card',
						renderer: 'small'
					},
					{
						name: 'Sender',
						key: 'sender_id',
						renderer: 'mono'
					},
					{
						name: 'Receiver',
						key: 'receiver_id',
						renderer: 'mono'
					},
					{
						name: 'Amount',
						key: 'amount',
						type: 'currency',
						sortable: true,
						renderer: 'medium'
					},
					{
						name: 'Risk Score',
						key: 'fraud_score',
						renderer: 'risk',
					},
					{
						name: 'Date',
						key: 'timestamp',
						type: 'datetime',
						renderer: 'small',
						icon: 'calendar',
						sortable: true,
						defaultSort: true,
						defaultOrder: 'desc'
					},
					{
						name: 'Location',
						key: 'location',
						icon: 'map',
						renderer: 'small'
					},
					{
						name: 'Fraud Status',
						key: 'fraud_status',
						renderer: 'fraud'
					}
				]}
				path='/api/transactions'
				dataKey='transactions' />
		</div>
  	)
} 
'use server'

import { Card, CardContent } from '@/components/ui/card'
import { CreditCard } from 'lucide-react'
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

interface PaginatedTransactions {
	transactions: Transaction[]
	total: number
	page: number
	page_size: number
	total_pages: number
}

export default async function TransactionsPage() {
  	const response = await api.get('/transactions?page=1&page_size=10')  
	const { total_pages, total }: PaginatedTransactions = response.data 
  
  	return (
    	<div className="space-y-6">
      		<div className="flex items-center justify-between">
        		<div>
          			<h1 className="text-3xl font-bold tracking-tight">Transaction Explorer</h1>
          			<p className="text-muted-foreground">Search and explore transaction details and patterns.</p>
        		</div>
      		</div>
			<Card>
				<CardContent className="p-6">
					<div className="flex items-center justify-between">
						<div>
							<p className="text-sm font-medium text-muted-foreground">Total Transactions</p>
							<p className="text-3xl font-bold">{total}</p>
						</div>
						<CreditCard className="h-12 w-12 text-muted-foreground" />
					</div>
				</CardContent>
			</Card>
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
						renderer: 'medium'
					},
					{
						name: 'Date',
						key: 'timestamp',
						type: 'datetime',
						renderer: 'small'
					},
					{
						name: 'Location',
						key: 'location',
						icon: 'map',
						renderer: 'small'
					},
					{
						name: 'Risk Score',
						key: 'fraud_score',
						renderer: 'risk'
					},
					{
						name: 'Fraud Status',
						key: 'fraud_status',
						renderer: 'fraud'
					}
				]}
				path='/api/transactions'
				dataKey='transactions'
				totalPages={total_pages}
				totalEntries={total} />
		</div>
  	)
} 
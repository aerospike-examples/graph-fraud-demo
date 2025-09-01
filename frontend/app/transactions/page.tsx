'use server'

import Results from '@/components/ResultTable'
import Stat from '@/components/Stat'
import Lookup from '@/components/Lookup'

interface TransactionStats {
	total_txns: number
	total_blocked: number
	total_review: number
	total_clean: number
}

const API_BASE_URL = process.env.BASE_URL || "http://localhost:8080/api"

export default async function TransactionsPage() {
  	const response = await fetch(`${API_BASE_URL}/transactions/stats`, { cache: 'no-store' })
	const { total_txns, total_blocked, total_review, total_clean }: TransactionStats = await response.json() 
  
  	return (
    	<div className="space-y-6 flex flex-col grow">
      		<div className="flex items-center justify-between">
        		<div>
          			<h1 className="text-3xl font-bold tracking-tight">Transaction Explorer</h1>
          			<p className="text-muted-foreground">Search and explore transaction details and patterns.</p>
        		</div>
      		</div>
			<div className="grid gap-4 md:grid-cols-4">
				<Stat
					title='Total Transactions'
					subtitle='Total transactions processed'
					stat={total_txns}
					icon='credit-card' />
				<Stat
					color='destructive'
					title='Blocked'
					subtitle='Total blocked transactions'
					stat={total_blocked}
					icon='shield' />
				<Stat
					title='Review'
					subtitle='Total transactions needing review'
					stat={total_review}
					icon='shield' />
				<Stat
					color='green-600'
					title='Clean'
					subtitle='Total transactions without fraud'
					stat={total_clean}
					icon='shield' />
			</div>
			<Results 
				searchType='txns'
				title='Transactions'
				options={[
					{
						name: 'Transaction ID',
						key: 'id',
						label: {
							size: 'sm',
							text: 'txn_id',
							icon: 'credit-card'
						}
					},
					{
						name: 'Sender',
						key: 'sender',
						label: {
							size: 'sm',
							text: 'sender',
							className: 'font-mono'
						}
					},
					{
						name: 'Receiver',
						key: 'receiver',
						label: {
							size: 'sm',
							text: 'receiver',
							className: 'font-mono'
						}
					},
					{
						name: 'Amount',
						key: 'amount',
						type: 'currency',
						sortable: true,
						label: {
							text: 'amount'
						}
					},
					{
						name: 'Risk Score',
						key: 'fraud_score',
						type: 'risk',
						sortable: true,
						label: {
							badge: {
								text: 'fraud_score'
							}
						}
					},
					{
						name: 'Date',
						key: 'timestamp',
						type: 'datetime',
						label: {
							size: 'sm',
							text: 'timestamp',
							icon: 'calendar',
						},
						sortable: true,
						defaultSort: true,
						defaultOrder: 'desc'
					},
					{
						name: 'Location',
						key: 'location',
						label: {
							size: 'sm',
							text: 'location',
							icon: 'map-pin',
						},
					},
					{
						name: 'Fraud Status',
						key: 'fraud_status',
						type: 'fraud',
						label: {
							badge: {
								text: 'fraud_status'
							}
						}
					}
				]}
				path='/api/transactions' />
		</div>
  	)
} 
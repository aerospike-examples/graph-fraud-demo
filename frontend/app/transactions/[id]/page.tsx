import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatDateTime, getRiskLevel } from '@/lib/utils'
import { 
	AlertTriangle,
	CheckCircle,
	XCircle,
	TrendingUp,
	TrendingDown,
	Activity,
	Calendar,
	Clock,
	Shield,
	Flag,
} from 'lucide-react'
import { api } from '@/lib/api'
import TxnDetails from "@/components/TxnDetails"
import type { Transaction } from '../page'
import type { Account } from '@/components/TxnDetails/AccountCard'
import type { FraudResult } from '@/components/TxnDetails/Analysis'

export interface TransactionDetail {
	transaction: Transaction
	source_account: Account
	destination_account: Account
	fraud_results: FraudResult[]
}

const TransactionDetailPage = async ({ params }: { params: { id: string }}) => {
	const { id: transactionId } = params;
  	const response = await api.get(`/transaction/${transactionId}`)
    const { transaction, source_account, destination_account, fraud_results } = response.data as TransactionDetail;

	const getTransactionTypeIcon = (type: string | undefined) => {
		switch (type?.toLowerCase()) {
			case 'deposit':
				return <TrendingUp className="h-4 w-4 text-green-600" />
			case 'withdrawal':
				return <TrendingDown className="h-4 w-4 text-destructive" />
			case 'transfer':
				return <Activity className="h-4 w-4 text-blue-600" />
			default:
				return <Activity className="h-4 w-4 text-muted-foreground" />
		}
	}

	const getStatusIcon = (status: string | undefined) => {
		switch (status?.toLowerCase()) {
			case 'completed':
				return <CheckCircle className="h-4 w-4 text-green-600" />
			case 'pending':
				return <Clock className="h-4 w-4 text-yellow-600" />
			case 'failed':
				return <XCircle className="h-4 w-4 text-destructive" />
			default:
				return <Clock className="h-4 w-4 text-muted-foreground" />
		}
	}

  	const calculateOverallRisk = () => {
    	if (!fraud_results || fraud_results.length === 0) {
      		return { score: 0, level: 'Low', color: 'default' }
    	}
    	const maxScore = Math.max(...fraud_results.map(r => r.fraud_score || 0))
    	const riskLevel = getRiskLevel(maxScore)
    	return { score: maxScore, level: riskLevel.level, color: riskLevel.color }
  	}

    const overallRisk = calculateOverallRisk()

	return (
    	<div className="space-y-6">
      		<div className="flex items-center justify-between">
				<div>
					<h1 className="text-3xl font-bold tracking-tight">Transaction Details</h1>
					<p className="text-muted-foreground">ID: {transaction.id}</p>
				</div>
				<div className="flex items-center gap-2">
					{transaction.is_fraud && (
						<Badge variant="destructive" className="text-lg px-4 py-2">
						<Flag className="h-4 w-4 mr-2" />
						Fraudulent
						</Badge>
					)}
					<Badge variant={overallRisk.color as any} className="text-sm px-3 py-1 font-medium border">
						{overallRisk.level} Risk ({(overallRisk.score || 0).toFixed(1)})
					</Badge>
				</div>
      		</div>
      		<div className="grid gap-4 md:grid-cols-4">
        		<Card>
          			<CardContent className="p-4">
						<p className="text-sm font-medium text-muted-foreground">Amount</p>
						<p className={`text-2xl font-bold ${transaction.amount < 0 ? 'text-destructive' : 'text-green-600'}`}>
							{formatCurrency(Math.abs(transaction.amount))}
						</p>
          			</CardContent>
        		</Card>
        		<Card>
          			<CardContent className="p-4">
						<p className="text-sm font-medium text-muted-foreground">Status</p>
						<div className="flex items-center gap-2">
							{getStatusIcon(transaction.status)}
							<p className="text-lg font-bold capitalize">{transaction.status}</p>
						</div>
          			</CardContent>
        		</Card>
        		<Card>
          			<CardContent className="p-4">
						<p className="text-sm font-medium text-muted-foreground">Type</p>
						<div className="flex items-center gap-2">
							{getTransactionTypeIcon(transaction.transaction_type)}
							<p className="text-lg font-bold capitalize">{transaction.transaction_type || 'Transfer'}</p>
						</div>
          			</CardContent>
        		</Card>
        		<Card>
          			<CardContent className="p-4">
						<p className="text-sm text-muted-foreground">Fraud Rules</p>
						<div className="flex items-center gap-2">
							<p className="text-2xl font-bold">{fraud_results.length}</p>
							<Shield className="h-5 w-5 text-muted-foreground" />
						</div>
          			</CardContent>
        		</Card>
      		</div>
			<div className="grid gap-4 md:grid-cols-2">
            	<Card>
              		<CardHeader>
                		<CardTitle className="flex items-center gap-2">
                  			<Activity className="h-5 w-5" />
                  			Transaction Information
                		</CardTitle>
              		</CardHeader>
              		<CardContent className="space-y-4">
                		<div className="grid grid-cols-2 gap-4">
                  			<div>
								<p className="text-sm font-medium text-muted-foreground">Transaction ID</p>
								<p className="text-lg font-semibold font-mono">{transaction.id}</p>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Amount</p>
								<p className={`text-lg font-semibold ${transaction.amount < 0 ? 'text-destructive' : 'text-green-600'}`}>
									{formatCurrency(Math.abs(transaction.amount))}
								</p>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Method</p>
								<p className="text-lg font-semibold capitalize">{transaction.method}</p>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Type</p>
								<div className="flex items-center gap-2">
									{getTransactionTypeIcon(transaction.transaction_type)}
									<p className="text-lg font-semibold capitalize">{transaction.transaction_type || 'Transfer'}</p>
								</div>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Status</p>
								<div className="flex items-center gap-2">
									{getStatusIcon(transaction.status)}
									<p className="text-lg font-semibold capitalize">{transaction.status}</p>
								</div>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Date & Time</p>
								<div className="flex items-center gap-2">
									<Calendar className="h-4 w-4 text-muted-foreground" />
									<p className="text-lg font-semibold">{formatDateTime(transaction.timestamp)}</p>
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
								<p className="text-sm font-medium text-muted-foreground">Fraud Score</p>
								<div className="flex items-center gap-2">
									<div className="text-2xl font-bold">{overallRisk.score?.toFixed(1) || '0.0'}</div>
									<Badge variant={overallRisk.color as any}>{overallRisk.level}</Badge>
								</div>
							</div>
							<div>
								<p className="text-sm font-medium text-muted-foreground">Fraud Status</p>
								<div className="flex items-center gap-2">
								{fraud_results.length > 0 ? (
									<>
									<AlertTriangle className="h-4 w-4 text-destructive" />
									<Badge variant="destructive">Flagged</Badge>
									</>
								) : (
									<>
									<CheckCircle className="h-4 w-4 text-green-600" />
									<Badge variant="default">Clean</Badge>
									</>
								)}
								</div>
							</div>
						</div>
              		</CardContent>
            	</Card>
          	</div>
			<TxnDetails 
				txnDetails={{ 
					transaction,
					source_account,
					destination_account,
					fraud_results
				}} />
    </div>
  )
} 

export default TransactionDetailPage
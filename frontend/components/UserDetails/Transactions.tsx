'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, AlertTriangle, Clock, TrendingDown, TrendingUp, CheckCircle, MapPin } from 'lucide-react'
import { formatCurrency, formatDateTime } from '@/lib/utils'
import { Account } from './Accounts'
import Loading from '@/app/loading'

export interface Transaction {
    id: string
    amount: number
    currency: string
    timestamp: string
    status: string
    fraud_score: number
    fraud_status?: string
    fraud_reason?: string
    transaction_type?: string
    location?: string
    is_fraud?: boolean
    fraud_type?: string
    sender_id: string
    receiver_id: string
    sender_name?: string
    receiver_name?: string
    fraud_rules?: string[]
    direction?: string
}

const Transactions = ({ 
    recent_transactions, 
    accounts 
}: { recent_transactions: Transaction[], accounts: Account[] }) => {
    const [detailedTransactions, setDetailedTransactions] = useState<Transaction[]>([])
    const [loading, setLoading] = useState(true);
    
    const fetchData = async () => {
        setLoading(true)
        const transactions = await Promise.all(
            recent_transactions.map(async (transaction) => {
                try {
                    const response = await fetch(`/api/transaction/${transaction.id}`)
                    if (response.ok) {
                        const detail = await response.json()
                        return {
                            ...transaction,
                            source_account: detail.source_account,
                            destination_account: detail.destination_account,
                            fraud_results: detail.fraud_results || []
                        }
                    }
                    return transaction // fallback to original if detail fetch fails
                } catch (error) {
                    console.error(`Error fetching details for transaction ${transaction.id}:`, error)
                    return transaction // fallback to original
                }
            })
        )
        setDetailedTransactions(transactions);
        setLoading(false);
    }

    useEffect(() => {
        fetchData();   
    }, [])

    const getTransactionDirection = (transaction: any) => {
        if (!accounts) return 'unknown'
        
        const userAccountIds = accounts.map(acc => acc.id)
        const isSender = userAccountIds.includes(transaction.sender_id)
        const isReceiver = userAccountIds.includes(transaction.receiver_id)
    
        if (isSender && !isReceiver) return 'sent'
        if (isReceiver && !isSender) return 'received'
        return 'internal' // both sender and receiver are user's accounts
    }

    const getTransactionParties = (transaction: any) => {
        if (transaction.source_account && transaction.destination_account) {
            return {
                senderName: transaction.source_account.user_name,
                receiverName: transaction.destination_account.user_name,
                senderAccountId: transaction.source_account.id,
                receiverAccountId: transaction.destination_account.id
            }
        }
    }
    
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5" />
                    Recent Transactions ({recent_transactions.length})
                </CardTitle>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <Loading />
                ): (
                    detailedTransactions.length > 0 ? (
                    <div className="space-y-4">
                        {detailedTransactions.map((transaction) => {
                            const direction = getTransactionDirection(transaction)
                            const displayAmount = direction === 'sent' ? -Math.abs(transaction.amount) : Math.abs(transaction.amount)
                            const txnParties = getTransactionParties(transaction)
                            const senderName = txnParties?.senderName ?? "" 
                            const receiverName = txnParties?.receiverName ?? ""
                            const isFraud = transaction.fraud_score > 0
                            
                            return (
                                <Card key={transaction.id} className={`p-4 ${isFraud ? 'border-red-200 bg-red-50' : ''}`}>
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <div className="flex items-center gap-2">
                                                    <p className="font-semibold">
                                                        {transaction.transaction_type ? 
                                                        `${transaction.transaction_type.charAt(0).toUpperCase() + transaction.transaction_type.slice(1)} Transaction` : 
                                                        'Transfer Transaction'}
                                                    </p>
                                                    <Badge variant="secondary" className="text-xs font-mono">
                                                        {transaction.id.substring(0, 8)}
                                                    </Badge>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <p className={`text-lg font-bold ${displayAmount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                                                    {displayAmount < 0 ? '-' : '+'}{formatCurrency(Math.abs(displayAmount))}
                                                </p>
                                                {displayAmount < 0 ? (
                                                    <TrendingDown className="h-4 w-4 text-red-600" />
                                                ) : (
                                                    <TrendingUp className="h-4 w-4 text-green-600" />
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                                            <div className="flex-1">
                                                <p className="text-sm font-medium text-gray-600">From</p>
                                                <p className="font-semibold">{senderName}</p>
                                                <p className="text-xs text-gray-500 font-mono">{getTransactionParties(transaction)?.senderAccountId}</p>
                                            </div>
                                            <div className="flex items-center">
                                                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                                                    <span className="text-blue-600">→</span>
                                                </div>
                                            </div>
                                            <div className="flex-1 text-right">
                                                <p className="text-sm font-medium text-gray-600">To</p>
                                                <p className="font-semibold">{receiverName}</p>
                                                <p className="text-xs text-gray-500 font-mono">{getTransactionParties(transaction)?.receiverAccountId}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <Badge 
                                                    variant={transaction.status === 'completed' ? 'default' : 'secondary'}
                                                    className="text-xs"
                                                >
                                                    {transaction.status === 'completed' ? (
                                                        <CheckCircle className="h-3 w-3 mr-1" />
                                                    ) : (
                                                        <Clock className="h-3 w-3 mr-1" />
                                                    )}
                                                    {transaction.status}
                                                </Badge>
                                                {transaction.location && (
                                                    <div className="flex items-center gap-1">
                                                        <MapPin className="h-3 w-3 text-gray-400" />
                                                        <span className="text-xs text-gray-500">{transaction.location}</span>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <p className="text-xs text-muted-foreground">
                                                    {formatDateTime(transaction.timestamp)}
                                                </p>
                                            </div>
                                        </div>
                                        {isFraud && (
                                            <div className="border-t pt-3 mt-3">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2">
                                                        <Badge variant="destructive" className="text-xs">
                                                            <AlertTriangle className="h-3 w-3 mr-1" />
                                                            FRAUD DETECTED
                                                        </Badge>
                                                    </div>
                                                    <Badge variant="secondary" className="text-xs">
                                                        Risk Score: {(transaction.fraud_score || 0).toFixed(1)}
                                                    </Badge>
                                                </div>
                                            </div>
                                        )}
                                        <div className="border-t pt-2">
                                            <p className="text-xs text-muted-foreground font-mono" title={transaction.id}>
                                                Full ID: {transaction.id}
                                            </p>
                                        </div>
                                    </div>
                                </Card>
                            )}
                        )}
                    </div>
                ) : (
                    <div className="text-center py-8">
                        <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                        <p className="text-muted-foreground">No transactions found for this user.</p>
                    </div>
                ))}
            </CardContent>
        </Card>
    )
}

export default Transactions
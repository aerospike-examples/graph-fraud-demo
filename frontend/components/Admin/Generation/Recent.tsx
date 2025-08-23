'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, CheckCircle, Clock, Database, XCircle } from 'lucide-react'
import type { Transaction } from '@/components/UserDetails/Transactions'

const Recent = ({ recentTxns }: { recentTxns: Transaction[]}) => {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <Clock className="w-5 h-5" />
                        <span>Recent Transactions</span>
                    </div>
                    <Badge variant="secondary">
                        {recentTxns.length} transactions
                    </Badge>
                </CardTitle>
                <CardDescription>
                    Live feed of generated transactions
                </CardDescription>
            </CardHeader>
            <CardContent>
                {recentTxns.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                        <Database className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No transactions generated yet</p>
                        <p className="text-sm">Start generation to see transactions here</p>
                    </div>
                ) : (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                    {recentTxns.map((transaction) => (
                        <div
                            key={transaction.id}
                            className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                        >
                            <div className="flex items-center space-x-3">
                                <div className="flex flex-col">
                                    <span className="font-mono text-sm">{transaction.id}</span>
                                    <span className="text-xs text-muted-foreground">
                                        {new Date(transaction.timestamp).toLocaleTimeString()}
                                    </span>
                                </div>
                            </div>
                            <div className="flex items-center space-x-4">
                                <div className="text-right">
                                    <div className="flex items-center space-x-1">
                                        <span className="font-medium">
                                            ${transaction.amount.toFixed(2)}
                                        </span>
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        {transaction.location}
                                    </div>
                                </div>                       
                                {transaction.is_fraud &&
                                <Badge variant="destructive">
                                    <AlertTriangle className="w-3 h-3 mr-1" />
                                    FRAUD
                                </Badge>}
                                <Badge variant={transaction.status === 'completed' ? 'default' : 'secondary'}>
                                    {transaction.status === 'completed' ? (
                                        <CheckCircle className="w-3 h-3 mr-1" />
                                    ) : (
                                        <XCircle className="w-3 h-3 mr-1" />
                                    )}
                                    {transaction.status}
                                </Badge>
                            </div>
                        </div>
                    ))}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

export default Recent
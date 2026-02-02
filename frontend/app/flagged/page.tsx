'use client'

import { useState } from 'react'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Link from 'next/link'
import { 
    Eye, 
    Search, 
    AlertTriangle, 
    Clock, 
    Shield,
    ChevronLeft,
    ChevronRight,
    Building,
    User,
    Calendar,
    TrendingUp
} from 'lucide-react'
import FlaggedStats from '@/components/Flagged/Stats'

// Mock data for flagged accounts
const mockFlaggedAccounts = [
    {
        id: 'ACC-78234',
        account_holder: 'Marcus Johnson',
        user_id: 'U4521',
        bank_name: 'Chase Bank',
        account_type: 'Checking',
        risk_score: 94.2,
        flagged_date: '2026-01-28',
        flag_reason: 'Multiple high-value transactions to new recipients',
        status: 'pending_review',
        suspicious_transactions: 12,
        total_flagged_amount: 45780.00
    },
    {
        id: 'ACC-91456',
        account_holder: 'Elena Rodriguez',
        user_id: 'U8932',
        bank_name: 'Bank of America',
        account_type: 'Savings',
        risk_score: 89.7,
        flagged_date: '2026-01-28',
        flag_reason: 'Unusual geographic pattern in transactions',
        status: 'under_investigation',
        suspicious_transactions: 8,
        total_flagged_amount: 28450.00
    },
    {
        id: 'ACC-34521',
        account_holder: 'David Chen',
        user_id: 'U2341',
        bank_name: 'Wells Fargo',
        account_type: 'Business',
        risk_score: 87.3,
        flagged_date: '2026-01-27',
        flag_reason: 'Rapid succession of international transfers',
        status: 'pending_review',
        suspicious_transactions: 15,
        total_flagged_amount: 89234.50
    },
    {
        id: 'ACC-56789',
        account_holder: 'Sarah Williams',
        user_id: 'U6712',
        bank_name: 'Citibank',
        account_type: 'Checking',
        risk_score: 85.1,
        flagged_date: '2026-01-27',
        flag_reason: 'Account linked to multiple flagged devices',
        status: 'under_investigation',
        suspicious_transactions: 6,
        total_flagged_amount: 15670.00
    },
    {
        id: 'ACC-12098',
        account_holder: 'Robert Kim',
        user_id: 'U9087',
        bank_name: 'US Bank',
        account_type: 'Savings',
        risk_score: 82.9,
        flagged_date: '2026-01-26',
        flag_reason: 'Sudden spike in transaction frequency',
        status: 'pending_review',
        suspicious_transactions: 22,
        total_flagged_amount: 34120.75
    },
    {
        id: 'ACC-45632',
        account_holder: 'Amanda Foster',
        user_id: 'U3456',
        bank_name: 'PNC Bank',
        account_type: 'Checking',
        risk_score: 79.4,
        flagged_date: '2026-01-26',
        flag_reason: 'Connected to known fraud ring accounts',
        status: 'pending_review',
        suspicious_transactions: 4,
        total_flagged_amount: 67890.00
    },
    {
        id: 'ACC-78901',
        account_holder: 'James Thompson',
        user_id: 'U7823',
        bank_name: 'TD Bank',
        account_type: 'Business',
        risk_score: 76.8,
        flagged_date: '2026-01-25',
        flag_reason: 'Inconsistent account activity patterns',
        status: 'under_investigation',
        suspicious_transactions: 9,
        total_flagged_amount: 52340.25
    },
    {
        id: 'ACC-23456',
        account_holder: 'Michelle Lee',
        user_id: 'U1234',
        bank_name: 'Capital One',
        account_type: 'Savings',
        risk_score: 74.2,
        flagged_date: '2026-01-25',
        flag_reason: 'Multiple failed verification attempts',
        status: 'pending_review',
        suspicious_transactions: 3,
        total_flagged_amount: 12450.00
    }
]

const statusConfig = {
    pending_review: { 
        label: 'Pending Review', 
        color: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
        icon: Clock
    },
    under_investigation: { 
        label: 'Under Investigation', 
        color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
        icon: Shield
    },
    confirmed_fraud: { 
        label: 'Confirmed Fraud', 
        color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
        icon: AlertTriangle
    },
    cleared: { 
        label: 'Cleared', 
        color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
        icon: Shield
    }
}

export default function FlaggedAccountsPage() {
    const [filter, setFilter] = useState<'all' | 'pending_review' | 'under_investigation'>('all')
    const [searchQuery, setSearchQuery] = useState('')

    const filteredAccounts = mockFlaggedAccounts.filter(account => {
        const matchesFilter = filter === 'all' || account.status === filter
        const matchesSearch = searchQuery === '' || 
            account.account_holder.toLowerCase().includes(searchQuery.toLowerCase()) ||
            account.id.toLowerCase().includes(searchQuery.toLowerCase())
        return matchesFilter && matchesSearch
    })

    return (
        <div className="space-y-6 flex flex-col grow">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Flagged Accounts</h1>
                <p className="text-muted-foreground">Review and process high-risk accounts flagged for potential fraud</p>
            </div>

            {/* Stats Section */}
            <div className="grid gap-4 md:grid-cols-4">
                <FlaggedStats />
            </div>

            {/* Main Content */}
            <Card className="grow flex flex-col">
                <CardHeader className="gap-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <CardTitle>Accounts Requiring Review</CardTitle>
                        <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
                            <TabsList>
                                <TabsTrigger value="all">All</TabsTrigger>
                                <TabsTrigger value="pending_review">Pending</TabsTrigger>
                                <TabsTrigger value="under_investigation">Investigating</TabsTrigger>
                            </TabsList>
                        </Tabs>
                    </div>
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search by account holder or ID..."
                                className="pl-9"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="grow overflow-x-auto flex flex-col">
                    <div className="space-y-3">
                        {filteredAccounts.map((account) => {
                            const StatusIcon = statusConfig[account.status as keyof typeof statusConfig].icon
                            return (
                                <div
                                    key={account.id}
                                    className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                                >
                                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                                        {/* Left Section - Account Info */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start gap-3">
                                                <div className="p-2 rounded-full bg-destructive/10 text-destructive">
                                                    <AlertTriangle className="h-5 w-5" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 flex-wrap">
                                                        <h3 className="font-semibold text-lg">{account.account_holder}</h3>
                                                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig[account.status as keyof typeof statusConfig].color}`}>
                                                            <StatusIcon className="h-3 w-3" />
                                                            {statusConfig[account.status as keyof typeof statusConfig].label}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1 flex-wrap">
                                                        <span className="flex items-center gap-1">
                                                            <Building className="h-3.5 w-3.5" />
                                                            {account.id}
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <User className="h-3.5 w-3.5" />
                                                            {account.user_id}
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <Calendar className="h-3.5 w-3.5" />
                                                            Flagged {new Date(account.flagged_date).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                    <p className="text-sm mt-2 text-muted-foreground">
                                                        <span className="font-medium text-foreground">Reason:</span> {account.flag_reason}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Middle Section - Risk Metrics */}
                                        <div className="flex items-center gap-6 lg:gap-8">
                                            <div className="text-center">
                                                <div className="flex items-center gap-1 justify-center">
                                                    <TrendingUp className="h-4 w-4 text-destructive" />
                                                    <span className="text-2xl font-bold text-destructive">{account.risk_score}</span>
                                                </div>
                                                <p className="text-xs text-muted-foreground">Risk Score</p>
                                            </div>
                                            <div className="text-center">
                                                <p className="text-2xl font-bold">{account.suspicious_transactions}</p>
                                                <p className="text-xs text-muted-foreground">Suspicious Txns</p>
                                            </div>
                                            <div className="text-center">
                                                <p className="text-2xl font-bold">${account.total_flagged_amount.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">Flagged Amount</p>
                                            </div>
                                        </div>

                                        {/* Right Section - Action */}
                                        <div className="flex items-center">
                                            <Link href={`/flagged/${account.id}`}>
                                                <Button>
                                                    <Eye className="h-4 w-4 mr-2" />
                                                    Review
                                                </Button>
                                            </Link>
                                        </div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </CardContent>
                <CardFooter className="flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                        Showing {filteredAccounts.length} of {mockFlaggedAccounts.length} flagged accounts
                    </p>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" disabled>
                            <ChevronLeft className="h-4 w-4" />
                            Previous
                        </Button>
                        <Button variant="outline" size="sm" disabled>
                            Next
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </CardFooter>
            </Card>
        </div>
    )
}

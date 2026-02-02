'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
    ArrowLeft,
    AlertTriangle,
    Building,
    User,
    Calendar,
    Clock,
    DollarSign,
    MapPin,
    CreditCard,
    Activity,
    ExternalLink,
    TrendingUp,
    Shield,
    Smartphone,
    Globe
} from 'lucide-react'
import ReviewWorkflow from '@/components/Flagged/Details/ReviewWorkflow'
import GraphVisualization from '@/components/Flagged/Details/GraphVisualization'

// Mock data for the account details
const getMockAccountData = (id: string) => ({
    id: id,
    account_holder: 'Marcus Johnson',
    user_id: 'U4521',
    bank_name: 'Chase Bank',
    account_type: 'Checking',
    account_number: '****4521',
    balance: 12450.75,
    risk_score: 94.2,
    flagged_date: '2026-01-28T14:32:00',
    flag_reason: 'Multiple high-value transactions to new recipients',
    status: 'pending_review',
    created_date: '2023-06-15',
    last_activity: '2026-01-28T16:45:00',
    
    // User Info
    user: {
        name: 'Marcus Johnson',
        email: 'marcus.johnson@email.com',
        phone: '+1 (555) 123-4567',
        location: 'New York, NY',
        signup_date: '2023-06-15',
        age: 34,
        occupation: 'Software Engineer'
    },
    
    // Risk Factors
    risk_factors: [
        { factor: 'High-value transactions to new recipients', severity: 'high', score: 35 },
        { factor: 'Unusual transaction timing patterns', severity: 'medium', score: 20 },
        { factor: 'Multiple failed login attempts', severity: 'medium', score: 15 },
        { factor: 'New device detected', severity: 'low', score: 10 },
        { factor: 'Geographic anomaly in transactions', severity: 'high', score: 14.2 }
    ],
    
    // Suspicious Transactions
    suspicious_transactions: [
        { id: 'TXN-001', date: '2026-01-28', amount: 8500, recipient: 'Unknown Account', type: 'Wire Transfer', risk: 'high' },
        { id: 'TXN-002', date: '2026-01-27', amount: 12300, recipient: 'Offshore LLC', type: 'ACH', risk: 'high' },
        { id: 'TXN-003', date: '2026-01-27', amount: 5400, recipient: 'New Recipient #1', type: 'Wire Transfer', risk: 'medium' },
        { id: 'TXN-004', date: '2026-01-26', amount: 7890, recipient: 'New Recipient #2', type: 'Wire Transfer', risk: 'high' },
        { id: 'TXN-005', date: '2026-01-26', amount: 3200, recipient: 'Foreign Bank', type: 'International', risk: 'medium' },
        { id: 'TXN-006', date: '2026-01-25', amount: 8490, recipient: 'Crypto Exchange', type: 'ACH', risk: 'high' }
    ],
    
    // Linked Devices
    devices: [
        { id: 'DEV-001', type: 'iPhone 15 Pro', os: 'iOS 17.2', last_seen: '2026-01-28', location: 'New York, NY', trusted: true },
        { id: 'DEV-002', type: 'MacBook Pro', os: 'macOS 14.2', last_seen: '2026-01-28', location: 'New York, NY', trusted: true },
        { id: 'DEV-003', type: 'Android Phone', os: 'Android 14', last_seen: '2026-01-27', location: 'Miami, FL', trusted: false }
    ],
    
    // Recent Activity
    activity_log: [
        { time: '2026-01-28 16:45', action: 'Wire transfer initiated', amount: 8500, status: 'pending' },
        { time: '2026-01-28 14:32', action: 'Account flagged by system', status: 'alert' },
        { time: '2026-01-28 14:30', action: 'Large transfer to new recipient', amount: 8500, status: 'warning' },
        { time: '2026-01-28 10:15', action: 'Login from new device', status: 'warning' },
        { time: '2026-01-27 22:30', action: 'Password change attempted', status: 'info' },
        { time: '2026-01-27 18:45', action: 'Multiple failed logins', status: 'warning' }
    ]
})

const riskBadge = (severity: string) => {
    const colors = {
        high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
        medium: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
        low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
    }
    return colors[severity as keyof typeof colors] || colors.low
}

export default function FlaggedAccountDetailsPage() {
    const params = useParams()
    const accountId = params.id as string
    const account = getMockAccountData(accountId)
    const [currentStep, setCurrentStep] = useState(0)
    const [activeTab, setActiveTab] = useState('overview')

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <Link href="/flagged" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-2">
                        <ArrowLeft className="h-4 w-4" />
                        Back to Flagged Accounts
                    </Link>
                    <div className="flex items-center gap-3">
                        <div className="p-3 rounded-full bg-destructive/10 text-destructive">
                            <AlertTriangle className="h-6 w-6" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight">{account.account_holder}</h1>
                            <div className="flex items-center gap-3 text-muted-foreground mt-1">
                                <span className="flex items-center gap-1">
                                    <Building className="h-4 w-4" />
                                    {account.id}
                                </span>
                                <span>•</span>
                                <span className="flex items-center gap-1">
                                    <CreditCard className="h-4 w-4" />
                                    {account.bank_name} - {account.account_type}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Link href={`/users/${account.user_id}`}>
                        <Button variant="outline">
                            <User className="h-4 w-4 mr-2" />
                            View User Profile
                            <ExternalLink className="h-3 w-3 ml-2" />
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Alert Banner */}
            <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                    <div>
                        <h3 className="font-semibold text-red-800 dark:text-red-300">High Risk Alert</h3>
                        <p className="text-sm text-red-700 dark:text-red-400 mt-1">{account.flag_reason}</p>
                        <p className="text-xs text-red-600 dark:text-red-500 mt-2">
                            Flagged on {new Date(account.flagged_date).toLocaleString()}
                        </p>
                    </div>
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Column - Account Details */}
                <div className="lg:col-span-2 space-y-6">
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="grid w-full grid-cols-5">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="graph">Graph</TabsTrigger>
                            <TabsTrigger value="transactions">Transactions</TabsTrigger>
                            <TabsTrigger value="devices">Devices</TabsTrigger>
                            <TabsTrigger value="activity">Activity</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6 mt-6">
                            {/* Risk Score Card */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <TrendingUp className="h-5 w-5 text-destructive" />
                                        Risk Analysis
                                    </CardTitle>
                                    <CardDescription>
                                        Breakdown of risk factors contributing to this flag
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="flex items-center gap-6 mb-6">
                                        <div className="text-center">
                                            <div className="text-5xl font-bold text-destructive">{account.risk_score}</div>
                                            <p className="text-sm text-muted-foreground">Overall Risk Score</p>
                                        </div>
                                        <div className="flex-1">
                                            <div className="h-4 bg-muted rounded-full overflow-hidden">
                                                <div 
                                                    className="h-full bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 transition-all"
                                                    style={{ width: `${account.risk_score}%` }}
                                                />
                                            </div>
                                            <div className="flex justify-between text-xs text-muted-foreground mt-1">
                                                <span>Low (0-25)</span>
                                                <span>Medium (25-70)</span>
                                                <span>High (70-100)</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-3">
                                        {account.risk_factors.map((factor, idx) => (
                                            <div key={idx} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                                                <div className="flex items-center gap-3">
                                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${riskBadge(factor.severity)}`}>
                                                        {factor.severity.toUpperCase()}
                                                    </span>
                                                    <span className="text-sm">{factor.factor}</span>
                                                </div>
                                                <span className="font-semibold">+{factor.score}</span>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Account & User Info */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-lg flex items-center gap-2">
                                            <CreditCard className="h-5 w-5" />
                                            Account Information
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Account ID</span>
                                            <span className="font-medium">{account.id}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Bank</span>
                                            <span className="font-medium">{account.bank_name}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Type</span>
                                            <span className="font-medium">{account.account_type}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Account Number</span>
                                            <span className="font-medium">{account.account_number}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Current Balance</span>
                                            <span className="font-medium">${account.balance.toLocaleString()}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Created</span>
                                            <span className="font-medium">{new Date(account.created_date).toLocaleDateString()}</span>
                                        </div>
                                    </CardContent>
                                </Card>

                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-lg flex items-center gap-2">
                                            <User className="h-5 w-5" />
                                            Account Holder
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Name</span>
                                            <span className="font-medium">{account.user.name}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Email</span>
                                            <span className="font-medium text-sm">{account.user.email}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Phone</span>
                                            <span className="font-medium">{account.user.phone}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Location</span>
                                            <span className="font-medium">{account.user.location}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Member Since</span>
                                            <span className="font-medium">{new Date(account.user.signup_date).toLocaleDateString()}</span>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        </TabsContent>

                        <TabsContent value="graph" className="mt-6">
                            <GraphVisualization accountId={accountId} />
                        </TabsContent>

                        <TabsContent value="transactions" className="mt-6">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <DollarSign className="h-5 w-5" />
                                        Suspicious Transactions
                                    </CardTitle>
                                    <CardDescription>
                                        Transactions that triggered fraud detection alerts
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        {account.suspicious_transactions.map((txn) => (
                                            <div key={txn.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                                                <div className="flex items-center gap-4">
                                                    <div className={`p-2 rounded-full ${
                                                        txn.risk === 'high' ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                                                        'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400'
                                                    }`}>
                                                        <DollarSign className="h-4 w-4" />
                                                    </div>
                                                    <div>
                                                        <p className="font-medium">{txn.recipient}</p>
                                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                            <span>{txn.id}</span>
                                                            <span>•</span>
                                                            <span>{txn.type}</span>
                                                            <span>•</span>
                                                            <span>{new Date(txn.date).toLocaleDateString()}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-lg font-semibold">${txn.amount.toLocaleString()}</p>
                                                    <span className={`text-xs px-2 py-0.5 rounded ${riskBadge(txn.risk)}`}>
                                                        {txn.risk.toUpperCase()} RISK
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="mt-4 pt-4 border-t">
                                        <div className="flex justify-between items-center">
                                            <span className="text-muted-foreground">Total Flagged Amount</span>
                                            <span className="text-2xl font-bold text-destructive">
                                                ${account.suspicious_transactions.reduce((sum, t) => sum + t.amount, 0).toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="devices" className="mt-6">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Smartphone className="h-5 w-5" />
                                        Linked Devices
                                    </CardTitle>
                                    <CardDescription>
                                        Devices associated with this account
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        {account.devices.map((device) => (
                                            <div key={device.id} className={`flex items-center justify-between p-4 border rounded-lg ${
                                                !device.trusted ? 'border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/10' : ''
                                            }`}>
                                                <div className="flex items-center gap-4">
                                                    <div className={`p-2 rounded-full ${
                                                        device.trusted 
                                                            ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
                                                            : 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400'
                                                    }`}>
                                                        <Smartphone className="h-4 w-4" />
                                                    </div>
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <p className="font-medium">{device.type}</p>
                                                            {!device.trusted && (
                                                                <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                                                                    NEW DEVICE
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                            <span>{device.os}</span>
                                                            <span>•</span>
                                                            <span className="flex items-center gap-1">
                                                                <MapPin className="h-3 w-3" />
                                                                {device.location}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="text-right text-sm text-muted-foreground">
                                                    <p>Last seen</p>
                                                    <p className="font-medium text-foreground">{new Date(device.last_seen).toLocaleDateString()}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="activity" className="mt-6">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Activity className="h-5 w-5" />
                                        Recent Activity Log
                                    </CardTitle>
                                    <CardDescription>
                                        Timeline of account activities and alerts
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-4">
                                        {account.activity_log.map((activity, idx) => (
                                            <div key={idx} className="flex gap-4">
                                                <div className="flex flex-col items-center">
                                                    <div className={`w-3 h-3 rounded-full ${
                                                        activity.status === 'alert' ? 'bg-red-500' :
                                                        activity.status === 'warning' ? 'bg-amber-500' :
                                                        activity.status === 'pending' ? 'bg-blue-500' :
                                                        'bg-muted-foreground'
                                                    }`} />
                                                    {idx < account.activity_log.length - 1 && (
                                                        <div className="w-0.5 flex-1 bg-muted" />
                                                    )}
                                                </div>
                                                <div className="pb-4 flex-1">
                                                    <div className="flex items-center justify-between">
                                                        <p className="font-medium">{activity.action}</p>
                                                        {activity.amount && (
                                                            <span className="font-semibold">${activity.amount.toLocaleString()}</span>
                                                        )}
                                                    </div>
                                                    <p className="text-sm text-muted-foreground">{activity.time}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </div>

                {/* Right Column - Workflow */}
                <div className="lg:col-span-1">
                    <ReviewWorkflow 
                        currentStep={currentStep}
                        onStepChange={setCurrentStep}
                    />
                </div>
            </div>
        </div>
    )
}

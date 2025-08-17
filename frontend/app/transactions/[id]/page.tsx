'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  ArrowLeft, 
  Loader2, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Activity,
  MapPin,
  Calendar,
  Clock,
  DollarSign,
  User,
  CreditCard,
  Shield,
  ExternalLink,
  Smartphone,
  Monitor,
  Tablet,
  Building,
  Mail,
  Phone,
  Zap,
  Target,
  Flag,
  Eye,
  BarChart3
} from 'lucide-react'
import { api } from '@/lib/api'
import Link from 'next/link'
import { useParams } from 'next/navigation'

interface Transaction {
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

interface Account {
  id: string
  account_type: string
  balance: number
  created_date: string
  user_id: string
  user_name: string
  user_email: string
}

interface FraudResult {
  rule_id: string
  rule_name: string
  risk_score: number
  risk_level: string
  triggered: boolean
  description: string
  timestamp: string
}

interface TransactionDetail {
  transaction: Transaction
  source_account: Account
  destination_account: Account
  fraud_results: FraudResult[]
}

export default function TransactionDetailPage() {
  const params = useParams()
  const transactionId = params.id as string
  
  const [transactionDetails, setTransactionDetails] = useState<TransactionDetail | null>(null)
  const [fraudResults, setFraudResults] = useState<any[]>([])
  const [fraudResultsLoading, setFraudResultsLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (transactionId) {
      loadTransactionDetails()
      loadFraudResults()
    }
  }, [transactionId])

  const loadTransactionDetails = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.get(`/transaction/${transactionId}`)
      if (response.data) {
        setTransactionDetails(response.data)
      } else {
        setError('Transaction not found. It may have been deleted or does not exist.')
      }
    } catch (error: any) {
      console.error('Failed to load transaction details:', error)
      if (error.response?.status === 404) {
        setError('Transaction not found. It may have been deleted or does not exist.')
      } else {
        setError('Failed to load transaction details. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadFraudResults = async () => {
    setFraudResultsLoading(true)
    
    try {
      const response = await api.get(`/transaction/${transactionId}/fraud-results`)
      if (response.data) {
        setFraudResults(response.data.fraud_results || [])
      }
    } catch (error: any) {
      console.error('Failed to load fraud results:', error)
      setFraudResults([])
    } finally {
      setFraudResultsLoading(false)
    }
  }

  const getRiskLevel = (score: number) => {
    if (score < 25) return { level: 'Low', color: 'default' }
    if (score < 50) return { level: 'Medium', color: 'secondary' } 
    if (score < 75) return { level: 'High', color: 'secondary' }
    return { level: 'Critical', color: 'secondary' }
  }

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'Unknown'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const formatDateTime = (dateString: string | undefined) => {
    if (!dateString) return 'Unknown'
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount)
  }

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

  const formatTime = (dateString: string | undefined) => {
    if (!dateString) return 'Unknown'
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Calculate overall fraud score and risk from actual fraud results
  const calculateOverallRisk = () => {
    if (!fraudResults || fraudResults.length === 0) {
      return { score: 0, level: 'Low', color: 'default' }
    }
    
    const maxScore = Math.max(...fraudResults.map(r => r.fraud_score || 0))
    const riskLevel = getRiskLevel(maxScore)
    return { score: maxScore, level: riskLevel.level, color: riskLevel.color }
  }

  const overallRisk = calculateOverallRisk()

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/transactions">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Transactions
            </Button>
          </Link>
        </div>
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="flex items-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span>Loading transaction details...</span>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !transactionDetails) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/transactions">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Transactions
            </Button>
          </Link>
        </div>
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-center">
              <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
              <p className="text-destructive font-medium">{error || 'Transaction not found'}</p>
              <Button onClick={loadTransactionDetails} className="mt-4">
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { transaction, source_account, destination_account, fraud_results } = transactionDetails
  const risk = getRiskLevel(transaction.fraud_score || 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/transactions">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Transactions
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Transaction Details</h1>
            <p className="text-muted-foreground">ID: {transaction.id}</p>
          </div>
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

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Amount</p>
                <p className={`text-2xl font-bold ${transaction.amount < 0 ? 'text-destructive' : 'text-green-600'}`}>
                  {formatCurrency(Math.abs(transaction.amount))}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Status</p>
                <div className="flex items-center gap-2">
                  {getStatusIcon(transaction.status)}
                  <p className="text-lg font-bold capitalize">{transaction.status}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Type</p>
                <div className="flex items-center gap-2">
                  {getTransactionTypeIcon(transaction.transaction_type)}
                  <p className="text-lg font-bold capitalize">{transaction.transaction_type || 'Transfer'}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Fraud Rules</p>
              <div className="flex items-center gap-2">
                <p className="text-2xl font-bold">{fraudResults.length}</p>
                <Shield className="h-5 w-5 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="accounts">Accounts</TabsTrigger>
          <TabsTrigger value="fraud">Fraud Analysis</TabsTrigger>
          <TabsTrigger value="location">Location</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
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
                      {fraudResults.length > 0 ? (
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
        </TabsContent>

        {/* Accounts Tab */}
        <TabsContent value="accounts" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Source Account */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingDown className="h-5 w-5 text-destructive" />
                  Source Account
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Account ID</p>
                    <p className="text-lg font-semibold font-mono">{source_account.id}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Account Type</p>
                    <p className="text-lg font-semibold capitalize">{source_account.account_type}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Balance</p>
                    <p className={`text-lg font-semibold ${source_account.balance < 0 ? 'text-destructive' : 'text-green-600'}`}>
                      {formatCurrency(source_account.balance)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Owner</p>
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-lg font-semibold">{source_account.user_name}</p>
                        <p className="text-sm text-muted-foreground">{source_account.user_email}</p>
                      </div>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Created</p>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                                                  <p className="text-sm">{formatDate(source_account.created_date || undefined)}</p>
                    </div>
                  </div>
                </div>
                <Link href={`/users/${source_account.user_id}`}>
                  <Button variant="outline" className="w-full">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View User Profile
                  </Button>
                </Link>
              </CardContent>
            </Card>

            {/* Destination Account */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  Destination Account
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Account ID</p>
                    <p className="text-lg font-semibold font-mono">{destination_account.id}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Account Type</p>
                    <p className="text-lg font-semibold capitalize">{destination_account.account_type}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Balance</p>
                    <p className={`text-lg font-semibold ${destination_account.balance < 0 ? 'text-destructive' : 'text-green-600'}`}>
                      {formatCurrency(destination_account.balance)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Owner</p>
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-lg font-semibold">{destination_account.user_name}</p>
                        <p className="text-sm text-muted-foreground">{destination_account.user_email}</p>
                      </div>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Created</p>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                                                  <p className="text-sm">{formatDate(destination_account.created_date || undefined)}</p>
                    </div>
                  </div>
                </div>
                <Link href={`/users/${destination_account.user_id}`}>
                  <Button variant="outline" className="w-full">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View User Profile
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Fraud Analysis Tab */}
        <TabsContent value="fraud" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Fraud Detection Results ({fraudResults.length})
              </CardTitle>
              <CardDescription>
                Detailed analysis of fraud detection rules and their results
              </CardDescription>
            </CardHeader>
            <CardContent>
              {fraudResultsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Loading fraud analysis...</span>
                  </div>
                </div>
              ) : fraudResults.length > 0 ? (
                <div className="space-y-4">
                  {fraudResults.map((result, index) => (
                    <Card key={index} className="p-4 border-red-200 bg-red-50">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2">
                            <h4 className="font-semibold">{result.rule || 'Unknown Rule'}</h4>
                            <Badge variant="destructive" className="text-xs">
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              Triggered
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">{result.reason}</p>
                          <div className="flex items-center gap-4 text-sm">
                            <div className="flex items-center gap-1">
                              <Target className="h-4 w-4 text-muted-foreground" />
                              <span className="text-muted-foreground">Risk Score:</span>
                              <span className="font-medium">{result.fraud_score}/100</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Clock className="h-4 w-4 text-muted-foreground" />
                              <span className="text-muted-foreground">Detected:</span>
                              <span className="font-medium">{formatDateTime(result.evaluation_timestamp)}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Flag className="h-4 w-4 text-muted-foreground" />
                              <span className="text-muted-foreground">Status:</span>
                              <span className="font-medium capitalize">{result.status}</span>
                            </div>
                          </div>
                          
                          {/* Parse and display details if available */}
                          {result.details && (
                            <div className="mt-3 p-3 bg-gray-100 rounded-lg">
                              <h5 className="text-sm font-medium mb-2">Detection Details:</h5>
                              <div className="text-sm text-gray-600">
                                <pre className="whitespace-pre-wrap">{result.details}</pre>
                              </div>
                            </div>
                          )}
                        </div>
                        <div className="ml-4">
                          <Badge 
                            variant={result.fraud_score >= 75 ? 'destructive' : 'secondary'}
                            className="text-xs"
                          >
                            {getRiskLevel(result.fraud_score).level} Risk
                          </Badge>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-muted-foreground mb-2">
                    No fraud detection results available.
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Fraud detection analysis has not been performed on this transaction.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Location Tab */}
        <TabsContent value="location" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                Location Information
              </CardTitle>
              <CardDescription>
                Geographic and network location details for this transaction
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">City</p>
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <p className="text-lg font-semibold">{transaction.location_city || 'Unknown'}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Country</p>
                    <p className="text-lg font-semibold">{transaction.location_country || 'Unknown'}</p>
                  </div>
                  {transaction.latitude && transaction.longitude && (
                    <>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Latitude</p>
                        <p className="text-lg font-semibold">{transaction.latitude.toFixed(6)}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Longitude</p>
                        <p className="text-lg font-semibold">{transaction.longitude.toFixed(6)}</p>
                      </div>
                    </>
                  )}
                </div>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">IP Address</p>
                    <p className="text-lg font-semibold font-mono">{transaction.ip_address || 'Unknown'}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Transaction Time</p>
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <p className="text-lg font-semibold">{formatDateTime(transaction.timestamp)}</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {(!transaction.location_city && !transaction.ip_address) && (
                <div className="text-center py-8 mt-4">
                  <MapPin className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No location information available.</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Location data was not captured for this transaction.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
} 
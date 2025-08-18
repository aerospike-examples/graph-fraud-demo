'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { 
  Play, 
  Square, 
  Trash2, 
  Settings, 
  Activity, 
  Clock, 
  DollarSign, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Database,
  Shield,
  Info,
  Eye,
  Zap,
  Target,
  Globe,
  MapPin,
  TrendingUp,
  Users,
  CreditCard,
  BarChart3
} from 'lucide-react'
import PerformanceDashboard from '@/components/PerformanceDashboard'

interface Transaction {
  id: string
  user_id: string
  account_id: string
  amount: number
  currency: string
  transaction_type: string
  location: string
  timestamp: string
  status: string
  fraud_score: number
  fraud_status?: string
  fraud_reason?: string
  fraud_type?: string
  fraud_scenario?: string
  is_fraud?: boolean
}

interface GenerationStats {
  isRunning: boolean
  totalGenerated: number
  currentRate: number
  startTime?: string
  duration: string
}

interface FraudScenario {
  id: string
  name: string
  description: string
  riskLevel: 'High' | 'Medium-High' | 'Medium' | 'Low'
  enabled: boolean
  priority: 'Phase 1' | 'Phase 2' | 'Phase 3'
  keyIndicators: string[]
  commonUseCase: string
  detailedDescription: string
  disabled?: boolean // For completely disabling scenarios from UI
}

interface FraudPattern {
  id: string
  name: string
  description: string
  risk_level: string
}

interface FraudResult {
  pattern_id: string
  pattern_name: string
  detected_entities: any[]
  risk_score: number
  timestamp: string
  details: any
}

interface Account {
  account_id: string
  account_type: string
  balance: number
  user_name: string
  fraud_flag?: boolean
}

const fraudScenarios: FraudScenario[] = [
  // Real-time scenarios (RT1-RT4)
  {
    id: 'RT1',
    name: 'Transaction to Flagged Account',
    description: 'Immediate threat detection via 1-hop lookup',
    riskLevel: 'High',
    enabled: true,
    priority: 'Phase 1',
    keyIndicators: [
      'Transaction directed to known flagged account',
      '1-hop graph lookup for immediate detection',
      'Real-time risk assessment'
    ],
    commonUseCase: 'Immediate threat detection, known fraudster connections',
    detailedDescription: 'Real-time detection system that flags transactions sent to accounts that have been previously identified as fraudulent. Uses 1-hop graph lookups for immediate threat assessment.'
  },
  {
    id: 'RT3',
    name: 'Supernode Detection (High-Degree)',
    description: 'Alert on highly connected accounts',
    riskLevel: 'Medium-High',
    enabled: true,
    priority: 'Phase 1',
    keyIndicators: [
      'Abnormally high connection count',
      'Centrality score above threshold',
      'Hub-like transaction patterns'
    ],
    commonUseCase: 'Money laundering hubs, distribution networks',
    detailedDescription: 'Identifies accounts with unusually high connectivity in the transaction graph, which may indicate central nodes in money laundering or distribution networks.'
  },
  {
    id: 'RT2',
    name: 'Repeated Small Ring Interactions',
    description: 'Identify mule rings via 2-hop neighborhood analysis',
    riskLevel: 'High',
    enabled: false,
    priority: 'Phase 1',
    keyIndicators: [
      'Multiple small transactions within ring',
      '2-hop neighborhood analysis',
      'Repeated interaction patterns'
    ],
    commonUseCase: 'Money mule ring detection, coordinated fraud networks',
    detailedDescription: 'Detects patterns of repeated small transactions between accounts that form rings or networks, indicating coordinated money mule operations using 2-hop graph analysis.',
    disabled: true
  },
  {
    id: 'RT4',
    name: 'High-Risk Batch Score',
    description: 'Use batch-computed fraud scores for real-time decisions',
    riskLevel: 'Medium',
    enabled: false,
    priority: 'Phase 1',
    keyIndicators: [
      'High fraud score from batch processing',
      'Vertex property lookup',
      'Pre-computed risk assessment'
    ],
    commonUseCase: 'Leveraging historical analysis for real-time decisions',
    detailedDescription: 'Utilizes fraud scores computed during batch processing for real-time transaction assessment, combining historical pattern analysis with immediate decision making.',
    disabled: true
  },
  {
    id: 'RT5',
    name: 'Transaction Burst',
    description: 'Detect rapid successive transactions from same user',
    riskLevel: 'High',
    enabled: true,
    priority: 'Phase 1',
    keyIndicators: [
      'Multiple transactions in short time window',
      'Same user account activity',
      'Rapid transaction succession pattern'
    ],
    commonUseCase: 'Account takeover, automated fraud attacks',
    detailedDescription: 'Real-time detection of rapid successive transactions from the same user account, which may indicate account takeover or automated fraud attacks.'
  },
  // Batch scenarios (A-H, corresponding to BT scenarios)
  {
    id: 'A',
    name: 'Multiple Small Credits → Large Debit',
    description: 'Money laundering technique with structured deposits',
    riskLevel: 'High',
    enabled: true,
    priority: 'Phase 1',
    keyIndicators: [
      'Multiple credits within 24 hours before debit',
      'Total credits ≈ debit amount (90-100%)',
      'At least 2 credit transactions'
    ],
    commonUseCase: 'Money laundering, structuring transactions',
    detailedDescription: 'A sophisticated money laundering technique where an account receives multiple small credit transactions followed by a single large debit transaction. This pattern suggests structured deposits to avoid detection thresholds and reporting requirements.'
  },
  {
    id: 'B',
    name: 'Large Credit → Structured Equal Debits',
    description: 'Organized money distribution pattern',
    riskLevel: 'High',
    enabled: true,
    priority: 'Phase 1',
    keyIndicators: [
            'Large credit (₹8,00,000-₹40,00,000)',
      'Exactly 4 equal debits within 4 hours',
      'Each debit ≈ 1/4 of credit amount',
      'All debits to same destination'
    ],
    commonUseCase: 'Money mule operations, organized fraud rings',
    detailedDescription: 'A pattern where a large credit is immediately followed by exactly 4 equal-sized debit transactions, typically indicating money distribution to multiple accounts. This suggests organized distribution of funds through coordinated networks.'
  },
  {
    id: 'C',
    name: 'Multiple Large ATM Withdrawals',
    description: 'Systematic cash extraction pattern',
    riskLevel: 'Medium-High',
    enabled: false,
    priority: 'Phase 2',
    keyIndicators: [
      '3+ ATM withdrawal transactions',
            'Each withdrawal ₹4,00,000-₹8,00,000',
      'Self-directed transactions'
    ],
    commonUseCase: 'Cash extraction for money laundering',
    detailedDescription: 'A pattern of multiple large ATM withdrawals that could indicate cash extraction for illicit purposes. This suggests systematic cash extraction to avoid digital trails and reporting requirements.'
  },
  {
    id: 'D',
    name: 'High-Frequency Mule Account Transfers',
    description: 'Rapid-fire money movement',
    riskLevel: 'High',
    enabled: true,
    priority: 'Phase 1',
    keyIndicators: [
      '10+ transactions in short time',
      'Amounts ₹40,000-₹4,00,000 each',
      'Mix of credits/debits within 1 hour',
      'High velocity money movement'
    ],
    commonUseCase: 'Money mule networks, account takeover',
    detailedDescription: 'Rapid-fire transactions between multiple accounts, indicating money mule activity or account takeover. This pattern shows high velocity of money movement and suggests coordinated account activity.'
  },
  {
    id: 'E',
    name: 'Salary-Like Deposits → Suspicious Transfers',
    description: 'Account takeover mimicry',
    riskLevel: 'Medium-High',
    enabled: false,
    priority: 'Phase 2',
    keyIndicators: [
            'Initial credit ₹4,00,000-₹8,00,000',
      '3+ outgoing transfers',
            'Transfer amounts ₹4,00,000-₹5,60,000'
    ],
    commonUseCase: 'Account takeover, identity theft',
    detailedDescription: 'A pattern mimicking legitimate salary deposits but followed by suspicious outgoing transfers. This suggests account takeover or identity theft where fraudsters mimic normal salary patterns.'
  },
  {
    id: 'F',
    name: 'Dormant Account Sudden Activity',
    description: 'Account compromise indicator',
    riskLevel: 'High',
    enabled: false,
    priority: 'Phase 2',
    keyIndicators: [
      '30+ days dormancy',
            'Sudden large credit ₹8,00,000-₹40,00,000',
      '4 equal debits following',
      'Total debits ≈ credit amount'
    ],
    commonUseCase: 'Account takeover, dormant account exploitation',
    detailedDescription: 'A previously inactive account suddenly receives a large deposit followed by structured withdrawals. This suggests account compromise or takeover of dormant accounts.'
  },
  {
    id: 'G',
    name: 'International High-Risk Transfers',
    description: 'Cross-border money laundering',
    riskLevel: 'High',
    enabled: false,
    priority: 'Phase 3',
    keyIndicators: [
      '5+ international transfers',
      'Amounts ₹40,000-₹4,00,000 each',
      'High-risk jurisdictions',
      'Dubai, Bahrain, Thailand'
    ],
    commonUseCase: 'International money laundering, terrorist financing',
    detailedDescription: 'Multiple transfers to specific international locations known for financial crime or money laundering. This suggests international money laundering networks and cross-border fraud.'
  },
  {
    id: 'H',
    name: 'Region-Specific Fraud (Indian)',
    description: 'Localized fraud patterns',
    riskLevel: 'High',
    enabled: false,
    priority: 'Phase 3',
    keyIndicators: [
            '3+ large transfers ₹8,00,000-₹40,00,000',
      'High-risk locations',
      'Jamtara, Bharatpur, Alwar',
      'Region-specific patterns'
    ],
    commonUseCase: 'Regional fraud networks, location-based scams',
    detailedDescription: 'Fraud patterns specific to the Indian financial landscape, targeting known fraud-prone regions. This includes location-based scams and regional fraud networks.'
  }
]

interface ExtendedFraudPattern extends FraudPattern {
  priority: 'Phase 1' | 'Phase 2' | 'Phase 3'
  enabled?: boolean
  disabled?: boolean
  keyIndicators?: string[]
  commonUseCase?: string
  detailedDescription?: string
}

const availablePatterns: ExtendedFraudPattern[] = [
  // Phase 1 - High Priority Patterns
  {
    id: 'A',
    name: 'Multiple Small Credits → Large Debit',
    description: 'Money laundering technique with structured deposits',
    risk_level: 'high',
    priority: 'Phase 1',
    enabled: true,
    keyIndicators: [
      'Multiple credits within 24 hours before debit',
      'Total credits ≈ debit amount (90-100%)',
      'At least 2 credit transactions'
    ],
    commonUseCase: 'Money laundering, structuring transactions',
    detailedDescription: 'A sophisticated money laundering technique where an account receives multiple small credit transactions followed by a single large debit transaction.'
  },
  {
    id: 'B',
    name: 'Large Credit → Structured Equal Debits',
    description: 'Organized money distribution pattern',
    risk_level: 'high',
    priority: 'Phase 1',
    enabled: false,
    disabled: true,
    keyIndicators: [
      'Large credit (₹8,00,000-₹40,00,000)',
      'Exactly 4 equal debits within 4 hours',
      'Each debit ≈ 1/4 of credit amount'
    ],
    commonUseCase: 'Money mule operations, organized fraud rings',
    detailedDescription: 'A pattern where a large credit is immediately followed by exactly 4 equal-sized debit transactions, indicating organized distribution of funds.'
  },
  {
    id: 'D',
    name: 'High-Frequency Mule Account Transfers',
    description: 'Rapid-fire money movement',
    risk_level: 'high',
    priority: 'Phase 1',
    enabled: true,
    keyIndicators: [
      '10+ transactions in short time',
      'Amounts ₹40,000-₹4,00,000 each',
      'Mix of credits/debits within 1 hour'
    ],
    commonUseCase: 'Money mule networks, account takeover',
    detailedDescription: 'Rapid-fire transactions between multiple accounts, indicating money mule activity or account takeover.'
  },
  {
    id: 'circular_flow',
    name: 'Circular Transaction Flow',
    description: 'Detect circular money flows between users',
    risk_level: 'high',
    priority: 'Phase 1',
    enabled: false,
    disabled: true
  },
  {
    id: 'high_amount',
    name: 'High Amount Transactions',
    description: 'Detect unusually high transaction amounts',
    risk_level: 'high',
    priority: 'Phase 1',
    enabled: false,
    disabled: true
  },
  {
    id: 'new_user_high_activity',
    name: 'New User High Activity',
    description: 'Detect new users with high transaction activity',
    risk_level: 'high',
    priority: 'Phase 1',
    enabled: true
  },
  
  // Phase 2 - Medium Priority Patterns
  {
    id: 'C',
    name: 'Multiple Large ATM Withdrawals',
    description: 'Systematic cash extraction pattern',
    risk_level: 'medium',
    priority: 'Phase 2',
    enabled: false,
    disabled: true,
    keyIndicators: [
      '3+ ATM withdrawal transactions',
      'Each withdrawal ₹4,00,000-₹8,00,000',
      'Self-directed transactions'
    ],
    commonUseCase: 'Cash extraction for money laundering',
    detailedDescription: 'A pattern of multiple large ATM withdrawals that could indicate cash extraction for illicit purposes.'
  },
  {
    id: 'E',
    name: 'Salary-Like Deposits → Suspicious Transfers',
    description: 'Account takeover mimicry',
    risk_level: 'medium',
    priority: 'Phase 2',
    enabled: false,
    disabled: true,
    keyIndicators: [
      'Initial credit ₹4,00,000-₹8,00,000',
      '3+ outgoing transfers',
      'Transfer amounts ₹4,00,000-₹5,60,000'
    ],
    commonUseCase: 'Account takeover, identity theft',
    detailedDescription: 'A pattern mimicking legitimate salary deposits but followed by suspicious outgoing transfers.'
  },
  {
    id: 'F',
    name: 'Dormant Account Sudden Activity',
    description: 'Account compromise indicator',
    risk_level: 'high',
    priority: 'Phase 2',
    enabled: false,
    disabled: true,
    keyIndicators: [
      '30+ days dormancy',
      'Sudden large credit ₹8,00,000-₹40,00,000',
      '4 equal debits following'
    ],
    commonUseCase: 'Account takeover, dormant account exploitation',
    detailedDescription: 'A previously inactive account suddenly receives a large deposit followed by structured withdrawals.'
  },
  {
    id: 'shared_device',
    name: 'Shared Device Transactions',
    description: 'Detect transactions from the same device by different users',
    risk_level: 'medium',
    priority: 'Phase 2',
    enabled: false,
    disabled: true
  },

  {
    id: 'cross_location',
    name: 'Cross-Location Transactions',
    description: 'Detect transactions between users in different locations',
    risk_level: 'medium',
    priority: 'Phase 2',
    enabled: false,
    disabled: true
  },
  
  // Phase 3 - Lower Priority Patterns
  {
    id: 'G',
    name: 'International High-Risk Transfers',
    description: 'Cross-border money laundering',
    risk_level: 'high',
    priority: 'Phase 3',
    enabled: false,
    disabled: true,
    keyIndicators: [
      '5+ international transfers',
      'Amounts ₹40,000-₹4,00,000 each',
      'High-risk jurisdictions'
    ],
    commonUseCase: 'International money laundering, terrorist financing',
    detailedDescription: 'Multiple transfers to specific international locations known for financial crime or money laundering.'
  },
  {
    id: 'H',
    name: 'Region-Specific Fraud (Indian)',
    description: 'Localized fraud patterns',
    risk_level: 'high',
    priority: 'Phase 3',
    enabled: false,
    disabled: true,
    keyIndicators: [
      '3+ large transfers ₹8,00,000-₹40,00,000',
      'High-risk locations',
      'Jamtara, Bharatpur, Alwar'
    ],
    commonUseCase: 'Regional fraud networks, location-based scams',
    detailedDescription: 'Fraud patterns specific to the Indian financial landscape, targeting known fraud-prone regions.'
  }
]

export default function AdminPage() {
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationRate, setGenerationRate] = useState(5)
  const [stats, setStats] = useState<GenerationStats>({
    isRunning: false,
    totalGenerated: 0,
    currentRate: 0,
    duration: '00:00:00'
  })
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showClearConfirmation, setShowClearConfirmation] = useState(false)
  const [scenarios, setScenarios] = useState<FraudScenario[]>(fraudScenarios)
  const [selectedScenario, setSelectedScenario] = useState<FraudScenario | null>(null)
  const [showScenarioDialog, setShowScenarioDialog] = useState(false)
  const [expandedScenarios, setExpandedScenarios] = useState<Set<string>>(new Set())
  const [isClient, setIsClient] = useState(false)

  // Fraud patterns states
  const [selectedPatterns, setSelectedPatterns] = useState<string[]>(
    availablePatterns.filter(p => p.enabled && !p.disabled).map(p => p.id)
  )
  const [patternResults, setPatternResults] = useState<FraudResult[]>([])
  const [patternLoading, setPatternLoading] = useState(false)
  const [patterns, setPatterns] = useState<ExtendedFraudPattern[]>(availablePatterns)

  // Manual transaction states
  const [accounts, setAccounts] = useState<Account[]>([])
  const [fromAccount, setFromAccount] = useState('')
  const [toAccount, setToAccount] = useState('')
  const [amount, setAmount] = useState('')
  const [transactionType, setTransactionType] = useState('transfer')
  const [manualLoading, setManualLoading] = useState(false)
  const [manualSuccess, setManualSuccess] = useState<string | null>(null)
  
  // Search functionality for account dropdowns
  const [fromAccountSearch, setFromAccountSearch] = useState('')
  const [toAccountSearch, setToAccountSearch] = useState('')
  const [showFromDropdown, setShowFromDropdown] = useState(false)
  const [showToDropdown, setShowToDropdown] = useState(false)
  
  // Filter accounts based on search
  const filteredFromAccounts = accounts.filter(account => 
    account.account_id.toLowerCase().includes(fromAccountSearch.toLowerCase()) ||
    account.user_name.toLowerCase().includes(fromAccountSearch.toLowerCase()) ||
    account.account_type.toLowerCase().includes(fromAccountSearch.toLowerCase())
  )
  
  const filteredToAccounts = accounts.filter(account => 
    account.account_id !== fromAccount &&
    (account.account_id.toLowerCase().includes(toAccountSearch.toLowerCase()) ||
     account.user_name.toLowerCase().includes(toAccountSearch.toLowerCase()) ||
     account.account_type.toLowerCase().includes(toAccountSearch.toLowerCase()))
  )

  // Ensure component only renders on client side
  useEffect(() => {
    setIsClient(true)
  }, [])

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      if (!target.closest('.account-dropdown-container')) {
        setShowFromDropdown(false)
        setShowToDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Update duration timer
  useEffect(() => {
    let timer: NodeJS.Timeout

    if (stats.isRunning && stats.startTime) {
      timer = setInterval(() => {
        const start = new Date(stats.startTime!)
        const now = new Date()
        const diff = now.getTime() - start.getTime()
        const hours = Math.floor(diff / (1000 * 60 * 60))
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
        const seconds = Math.floor((diff % (1000 * 60)) / 1000)
        
        setStats(prev => ({
          ...prev,
          duration: `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
        }))
      }, 1000)
    }

    return () => {
      if (timer) clearInterval(timer)
    }
  }, [stats.isRunning, stats.startTime])

  // Real-time status polling
  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return
    
    let interval: NodeJS.Timeout

    if (isGenerating) {
      // Poll for status updates every 2 seconds
      interval = setInterval(async () => {
        try {
          const response = await fetch('http://localhost:4000/transaction-generation/status')
          if (response.ok) {
            const statusData = await response.json()
            
            setStats(prev => ({
              ...prev,
              totalGenerated: statusData.total_generated,
              currentRate: statusData.generation_rate
            }))
            
            // Update recent transactions
            if (statusData.last_10_transactions) {
              setRecentTransactions(statusData.last_10_transactions)
            }
          }
        } catch (err) {
          console.error('Error polling status:', err)
        }
      }, 2000)
    }

    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [isGenerating])

  // Initial status check on component mount
  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return
    
    const checkInitialStatus = async () => {
      try {
        const response = await fetch('http://localhost:4000/transaction-generation/status')
        if (response.ok) {
          const statusData = await response.json()
          
          if (statusData.status === 'running') {
            setIsGenerating(true)
            setStats(prev => ({
              ...prev,
              isRunning: true,
              totalGenerated: statusData.total_generated,
              currentRate: statusData.generation_rate,
              startTime: new Date().toISOString() // Approximate start time
            }))
          }
          
          if (statusData.last_10_transactions) {
            setRecentTransactions(statusData.last_10_transactions)
          }
        }
      } catch (err) {
        console.error('Error checking initial status:', err)
      }
    }
    
    checkInitialStatus()
    loadAccounts()
  }, [])

  const handleStartGeneration = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`http://localhost:4000/transaction-generation/start?rate=${generationRate}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setIsGenerating(true); // Keep this state for UI consistency
        setStats(prev => ({ ...prev, isRunning: true, startTime: new Date().toISOString() }));
        console.log('Transaction generation started successfully!');
      } else {
        const errorData = await response.json();
        console.error(errorData.detail || 'Failed to start generation');
      }
    } catch (error) {
      console.error('Error starting generation:', error);
      console.error('Failed to start generation');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopGeneration = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('http://localhost:4000/transaction-generation/stop', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setIsGenerating(false); // Keep this state for UI consistency
        setStats(prev => ({ ...prev, isRunning: false }));
        console.log('Transaction generation stopped successfully!');
      } else {
        const errorData = await response.json();
        console.error(errorData.detail || 'Failed to stop generation');
      }
    } catch (error) {
      console.error('Error stopping generation:', error);
      console.error('Failed to stop generation');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearTransactions = async () => {
    if (!showClearConfirmation) {
      setShowClearConfirmation(true)
      return
    }
    
    setIsLoading(true)
    setError(null)
    
    try {
      // For now, we'll just clear the local state since the backend doesn't have a clear endpoint
      // In a real implementation, you would call a backend API to clear transactions
      setRecentTransactions([])
      setStats(prev => ({ ...prev, totalGenerated: 0 }))
      setShowClearConfirmation(false)
    } catch (err) {
      setError('Failed to clear transactions')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleScenario = (scenarioId: string) => {
    setScenarios(prev => prev.map(scenario => 
      scenario.id === scenarioId 
        ? { ...scenario, enabled: !scenario.enabled }
        : scenario
    ))
  }

  const toggleScenarioExpansion = (scenarioId: string) => {
    setExpandedScenarios(prev => {
      const newSet = new Set(prev)
      if (newSet.has(scenarioId)) {
        newSet.delete(scenarioId)
      } else {
        newSet.add(scenarioId)
      }
      return newSet
    })
  }

  const showScenarioDetails = (scenario: FraudScenario) => {
    setSelectedScenario(scenario)
    setShowScenarioDialog(true)
  }

  // Load accounts for manual transaction dropdowns
  const loadAccounts = async () => {
    try {
      const response = await fetch('/api/accounts')
      if (response.ok) {
        const data = await response.json()
        setAccounts(data.accounts)
      }
    } catch (error) {
      console.error('Failed to load accounts:', error)
    }
  }

  // Create manual transaction
  const handleCreateManualTransaction = async () => {
    if (!fromAccount || !toAccount || !amount) {
      setError('Please fill in all required fields')
      return
    }

    if (fromAccount === toAccount) {
      setError('Source and destination accounts must be different')
      return
    }

    const amountValue = parseFloat(amount)
    if (isNaN(amountValue) || amountValue <= 0) {
      setError('Please enter a valid amount')
      return
    }

    setManualLoading(true)
    setError(null)
    setManualSuccess(null)

    try {
      const response = await fetch(`/api/transaction-generation/manual?from_account_id=${fromAccount}&to_account_id=${toAccount}&amount=${amountValue}&transaction_type=${transactionType}`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        
        // Show success message
        setManualSuccess(`Transaction ${data.transaction_id} created successfully!`)
        
        // Reset form
        setFromAccount('')
        setToAccount('')
        setAmount('')
        setTransactionType('transfer')
        
        // Clear success message after 5 seconds
        setTimeout(() => {
          setManualSuccess(null)
        }, 5000)
        
        console.log('Manual transaction created successfully:', data.transaction_id)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to create transaction')
      }
    } catch (error) {
      console.error('Failed to create manual transaction:', error)
      setError('Failed to create transaction')
    } finally {
      setManualLoading(false)
    }
  }

  // Fraud pattern functions
  const togglePattern = (patternId: string) => {
    setSelectedPatterns(prev => 
      prev.includes(patternId) 
        ? prev.filter(id => id !== patternId)
        : [...prev, patternId]
    )
  }

  const togglePatternEnabled = (patternId: string) => {
    setPatterns(prev => prev.map(pattern => 
      pattern.id === patternId 
        ? { ...pattern, enabled: !pattern.enabled }
        : pattern
    ))
    
    // Also update selected patterns to stay in sync
    setSelectedPatterns(prev => {
      const pattern = patterns.find(p => p.id === patternId)
      if (pattern?.enabled) {
        // If pattern is currently enabled, it will be disabled, so remove from selection
        return prev.filter(id => id !== patternId)
      } else {
        // If pattern is currently disabled, it will be enabled, so add to selection
        return prev.includes(patternId) ? prev : [...prev, patternId]
      }
    })
  }

  const runPatterns = async () => {
    if (selectedPatterns.length === 0) return
    
    setPatternLoading(true)
    try {
      const response = await fetch('http://localhost:4000/fraud-patterns/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(selectedPatterns)
      })
      
      if (response.ok) {
        const data = await response.json()
        setPatternResults(data.results || [])
      } else {
        console.error('Failed to run fraud patterns')
      }
    } catch (error) {
      console.error('Failed to run fraud patterns:', error)
    } finally {
      setPatternLoading(false)
    }
  }

  const runAllPatterns = async () => {
    setPatternLoading(true)
    try {
      const response = await fetch('http://localhost:4000/detect/fraudulent-transactions')
      if (response.ok) {
        const data = await response.json()
        setPatternResults(data.results || [])
      } else {
        console.error('Failed to run all fraud patterns')
      }
    } catch (error) {
      console.error('Failed to run all fraud patterns:', error)
    } finally {
      setPatternLoading(false)
    }
  }

  const getFraudScoreColor = (score: number) => {
    if (score >= 80) return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    if (score >= 50) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  }

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'High': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'Medium-High': return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
      case 'Medium': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
      case 'Low': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'Phase 1': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'Phase 2': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
      case 'Phase 3': return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  const getPatternRiskColor = (level: string) => {
    switch (level) {
      case 'high': return 'destructive'
      case 'medium': return 'secondary'
      case 'low': return 'outline'
      default: return 'default'
    }
  }

  const enabledScenarios = scenarios.filter(s => s.enabled)
  const phase1Scenarios = scenarios.filter(s => s.priority === 'Phase 1')
  const phase2Scenarios = scenarios.filter(s => s.priority === 'Phase 2')
  const phase3Scenarios = scenarios.filter(s => s.priority === 'Phase 3')

  // Don't render until client-side
  if (!isClient) {
    return <div className="space-y-6">Loading...</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
          <p className="text-muted-foreground">
            Manage transaction generation and fraud detection scenarios
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {stats.isRunning && (
            <div className="text-right">
              <div className="text-sm text-muted-foreground">Live Transactions</div>
              <div className="text-2xl font-bold text-green-600 animate-pulse">
                {stats.totalGenerated.toLocaleString()}
              </div>
            </div>
          )}
          <Badge variant={stats.isRunning ? "default" : "secondary"}>
            {stats.isRunning ? (
              <>
                <Activity className="w-3 h-3 mr-1 animate-pulse" />
                Active
              </>
            ) : (
              <>
                <XCircle className="w-3 h-3 mr-1" />
                Inactive
              </>
            )}
          </Badge>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
              <span className="text-red-800 dark:text-red-200">{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content with Tabs */}
      <Tabs defaultValue="generation" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="generation" className="flex items-center space-x-2">
            <Activity className="w-4 h-4" />
            <span>Transaction Generation</span>
          </TabsTrigger>
          <TabsTrigger value="real-time-fraud" className="flex items-center space-x-2">
            <Zap className="w-4 h-4" />
            <span>Real Time Fraud Scenarios</span>
          </TabsTrigger>
          <TabsTrigger value="fraud-patterns" className="flex items-center space-x-2">
            <Shield className="w-4 h-4" />
            <span>Fraud Pattern</span>
          </TabsTrigger>
          <TabsTrigger value="performance" className="flex items-center space-x-2">
            <BarChart3 className="w-4 h-4" />
            <span>Performance</span>
          </TabsTrigger>
        </TabsList>

        {/* Performance Monitoring Tab */}
        <TabsContent value="performance" className="space-y-6">
          <PerformanceDashboard />
        </TabsContent>

        {/* Transaction Generation Tab */}
        <TabsContent value="generation" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {/* Generation Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="w-5 h-5" />
                  <span>Generation Controls</span>
                </CardTitle>
                <CardDescription>
                  Start, stop, and configure transaction generation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Generation Rate (transactions/sec)</label>
                  <Input
                    type="number"
                    min="1"
                    max="50"
                    value={generationRate}
                    onChange={(e) => setGenerationRate(parseInt(e.target.value) || 1)}
                    disabled={isGenerating}
                  />
                </div>
                
                <div className="flex space-x-2">
                  <Button
                    onClick={handleStartGeneration}
                    disabled={isGenerating || isLoading}
                    className="flex-1"
                  >
                    {isLoading ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 mr-2" />
                    )}
                    Start
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleStopGeneration}
                    disabled={!isGenerating || isLoading}
                    className="flex-1"
                  >
                    {isLoading ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Square className="w-4 h-4 mr-2" />
                    )}
                    Stop
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Statistics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="w-5 h-5" />
                  <span>Statistics</span>
                </CardTitle>
                <CardDescription>
                  Real-time generation metrics
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">
                      {stats.totalGenerated.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground">Total Generated</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {stats.currentRate}/s
                    </div>
                    <div className="text-xs text-muted-foreground">Current Rate</div>
                  </div>
                </div>
                
                {stats.isRunning && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Generation Progress</span>
                      <span className="text-xs font-mono">
                        {Math.round((stats.totalGenerated % 1000) / 10)}%
                      </span>
                    </div>
                    <Progress value={stats.totalGenerated % 1000} max={1000} />
                  </div>
                )}
                
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Duration</span>
                    <span className="font-mono">{stats.duration}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Status</span>
                    <Badge variant={stats.isRunning ? "default" : "secondary"}>
                      {stats.isRunning ? "Running" : "Stopped"}
                    </Badge>
                  </div>
                </div>

                {/* Quick Actions Section */}
                <div className="pt-4 border-t">
                  <h4 className="text-sm font-medium mb-3 flex items-center space-x-2">
                    <Database className="w-4 h-4" />
                    <span>Quick Actions</span>
                  </h4>
                  <div className="space-y-3">
                    <Button
                      variant={showClearConfirmation ? "destructive" : "outline"}
                      onClick={handleClearTransactions}
                      disabled={isLoading || recentTransactions.length === 0}
                      className="w-full"
                      size="sm"
                    >
                      {isLoading ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4 mr-2" />
                      )}
                      {showClearConfirmation ? "Confirm Clear" : "Clear All Transactions"}
                    </Button>
                    
                    {showClearConfirmation && (
                      <Button
                        variant="outline"
                        onClick={() => setShowClearConfirmation(false)}
                        className="w-full"
                        size="sm"
                      >
                        Cancel
                      </Button>
                    )}
                    
                    <div className="text-xs text-muted-foreground">
                      {showClearConfirmation 
                        ? "This action cannot be undone. Click 'Confirm Clear' to proceed."
                        : "This will remove all generated transactions from the system."
                      }
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Manual Transaction Creation */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <CreditCard className="w-5 h-5" />
                  <span>Manual Transaction</span>
                </CardTitle>
                <CardDescription>
                  Create a transaction between specific accounts
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">From Account</label>
                    <div className="relative account-dropdown-container">
                      <Input
                        type="text"
                        placeholder="Search by account ID, user name, or type..."
                        value={fromAccountSearch}
                        onChange={(e) => {
                          setFromAccountSearch(e.target.value)
                          setShowFromDropdown(true)
                          if (!e.target.value) {
                            setFromAccount('')
                          }
                        }}
                        onFocus={() => setShowFromDropdown(true)}
                        className="w-full"
                        disabled={manualLoading}
                      />
                      {fromAccount && (
                        <button
                          type="button"
                          onClick={() => {
                            setFromAccount('')
                            setFromAccountSearch('')
                            setShowFromDropdown(false)
                          }}
                          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          ✕
                        </button>
                      )}
                      {showFromDropdown && fromAccountSearch && (
                        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                          {filteredFromAccounts.length > 0 ? (
                            filteredFromAccounts.slice(0, 10).map((account) => (
                              <div
                                key={account.account_id}
                                className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                onClick={() => {
                                  setFromAccount(account.account_id)
                                  setFromAccountSearch(`${account.account_id} - ${account.user_name} (${account.account_type})`)
                                  setShowFromDropdown(false)
                                }}
                              >
                                <div className="font-medium">{account.account_id}</div>
                                <div className="text-gray-500 text-xs">{account.user_name} • {account.account_type}</div>
                              </div>
                            ))
                          ) : (
                            <div className="px-3 py-2 text-gray-500 text-sm">No accounts found</div>
                          )}
                          {filteredFromAccounts.length > 10 && (
                            <div className="px-3 py-2 text-gray-500 text-xs border-t">
                              Showing first 10 results. Type more to narrow down.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    {fromAccount && (
                      <div className="text-sm text-green-600 bg-green-50 p-2 rounded">
                        ✓ Selected: {fromAccountSearch}
                      </div>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium">To Account</label>
                    <div className="relative account-dropdown-container">
                      <Input
                        type="text"
                        placeholder="Search by account ID, user name, or type..."
                        value={toAccountSearch}
                        onChange={(e) => {
                          setToAccountSearch(e.target.value)
                          setShowToDropdown(true)
                          if (!e.target.value) {
                            setToAccount('')
                          }
                        }}
                        onFocus={() => setShowToDropdown(true)}
                        className="w-full"
                        disabled={manualLoading}
                      />
                      {toAccount && (
                        <button
                          type="button"
                          onClick={() => {
                            setToAccount('')
                            setToAccountSearch('')
                            setShowToDropdown(false)
                          }}
                          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          ✕
                        </button>
                      )}
                      {showToDropdown && toAccountSearch && (
                        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                          {filteredToAccounts.length > 0 ? (
                            filteredToAccounts.slice(0, 10).map((account) => (
                              <div
                                key={account.account_id}
                                className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                onClick={() => {
                                  setToAccount(account.account_id)
                                  setToAccountSearch(`${account.account_id} - ${account.user_name} (${account.account_type})`)
                                  setShowToDropdown(false)
                                }}
                              >
                                <div className="font-medium">{account.account_id}</div>
                                <div className="text-gray-500 text-xs">{account.user_name} • {account.account_type}</div>
                              </div>
                            ))
                          ) : (
                            <div className="px-3 py-2 text-gray-500 text-sm">No accounts found</div>
                          )}
                          {filteredToAccounts.length > 10 && (
                            <div className="px-3 py-2 text-gray-500 text-xs border-t">
                              Showing first 10 results. Type more to narrow down.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    {toAccount && (
                      <div className="text-sm text-green-600 bg-green-50 p-2 rounded">
                        ✓ Selected: {toAccountSearch}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Amount (INR)</label>
                    <Input
                      type="number"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="Enter amount"
                      min="0.01"
                      step="0.01"
                      disabled={manualLoading}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Transaction Type</label>
                    <select
                      value={transactionType}
                      onChange={(e) => setTransactionType(e.target.value)}
                      className="w-full p-2 border rounded-md bg-background"
                      disabled={manualLoading}
                    >
                      <option value="transfer">Transfer</option>
                      <option value="payment">Payment</option>
                      <option value="deposit">Deposit</option>
                      <option value="withdrawal">Withdrawal</option>
                    </select>
                  </div>
                </div>
                
                <Button
                  onClick={handleCreateManualTransaction}
                  disabled={manualLoading || !fromAccount || !toAccount || !amount}
                  className="w-full"
                >
                  {manualLoading ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <CreditCard className="w-4 h-4 mr-2" />
                  )}
                  Create Transaction
                </Button>
                
                {/* Success Message */}
                {manualSuccess && (
                  <div className="flex items-center space-x-2 p-3 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-md">
                    <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <span className="text-sm text-green-800 dark:text-green-200">{manualSuccess}</span>
                  </div>
                )}
              </CardContent>
            </Card>


          </div>

          {/* Recent Transactions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center space-x-2">
                  <Clock className="w-5 h-5" />
                  <span>Recent Transactions</span>
                </span>
                <Badge variant="secondary">
                  {recentTransactions.length} transactions
                </Badge>
              </CardTitle>
              <CardDescription>
                Live feed of generated transactions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recentTransactions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Database className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No transactions generated yet</p>
                  <p className="text-sm">Start generation to see transactions here</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {recentTransactions.map((transaction) => (
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
                              ₹{transaction.amount.toFixed(2)}
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {transaction.location}
                          </div>
                        </div>
                        
                        {/* <Badge className={getFraudScoreColor(transaction.fraud_score || 0)}>
                          {(transaction.fraud_score || 0).toFixed(1)}
                        </Badge> */}
                        
                        {transaction.is_fraud && (
                          <Badge variant="destructive">
                            <AlertTriangle className="w-3 h-3 mr-1" />
                            FRAUD
                          </Badge>
                        )}
                        
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
        </TabsContent>

        {/* Real Time Fraud Scenarios Tab */}
        <TabsContent value="real-time-fraud" className="space-y-6">
          {/* Fraud Detection Scenarios */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center space-x-2">
                  <Shield className="w-5 h-5" />
                  <span>Real Time Fraud Scenarios</span>
                </span>
                <div className="flex items-center space-x-2">
                  <Badge variant="secondary">
                    {scenarios.filter(s => s.id.startsWith('RT') && s.enabled).length} of {scenarios.filter(s => s.id.startsWith('RT')).length} enabled
                  </Badge>
                </div>
              </CardTitle>
              <CardDescription>
                Configure which fraud detection patterns to monitor in real-time
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Real-time Detection Scenarios */}
              <div className="space-y-3">
                {/* <h3 className="text-lg font-semibold flex items-center space-x-2">
                  <Zap className="w-4 h-4 text-green-600" />
                  <span>Real-time Detection (RT Scenarios)</span>
                </h3>
                <p className="text-sm text-muted-foreground">
                  Immediate fraud detection using graph lookups and real-time analysis
                </p> */}
                                  {scenarios.filter(s => s.id.startsWith('RT')).map((scenario) => (
                  <Collapsible key={scenario.id}>
                    <div className={`border rounded-lg ${scenario.disabled ? 'opacity-50 bg-gray-50 dark:bg-gray-900' : ''}`}>
                      <CollapsibleTrigger
                        onClick={() => !scenario.disabled && toggleScenarioExpansion(scenario.id)}
                        isOpen={expandedScenarios.has(scenario.id)}
                      >
                        <div className="flex items-center justify-between w-full">
                          <div className="flex items-center space-x-3">
                            <div onClick={(e) => e.stopPropagation()}>
                            <Switch
                              checked={scenario.enabled}
                              onCheckedChange={() => !scenario.disabled && toggleScenario(scenario.id)}
                              disabled={scenario.disabled}
                            />
                            </div>
                            <div className="text-left">
                              <div className={`font-medium ${scenario.disabled ? 'text-gray-400' : ''}`}>
                                {scenario.name}
                                {scenario.disabled && <span className="ml-2 text-xs">(Coming Soon)</span>}
                              </div>
                              <div className={`text-sm ${scenario.disabled ? 'text-gray-400' : 'text-muted-foreground'}`}>
                                {scenario.description}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Badge className={`${getRiskLevelColor(scenario.riskLevel)} ${scenario.disabled ? 'opacity-50' : ''}`}>
                              {scenario.riskLevel}
                            </Badge>
                            <div
                              className={`inline-flex items-center justify-center h-9 rounded-md px-3 text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground ${scenario.disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                              onClick={(e) => {
                                if (!scenario.disabled) {
                                  e.stopPropagation()
                                  showScenarioDetails(scenario)
                                }
                              }}
                              onKeyDown={(e) => {
                                if (!scenario.disabled && (e.key === ' ' || e.key === 'Enter')) {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  showScenarioDetails(scenario)
                                }
                              }}
                              tabIndex={scenario.disabled ? -1 : 0}
                              role="button"
                              aria-label="View scenario details"
                            >
                              <Eye className="w-4 h-4" />
                            </div>
                          </div>
                        </div>
                      </CollapsibleTrigger>
                      <CollapsibleContent isOpen={expandedScenarios.has(scenario.id)}>
                        <div className="space-y-3 text-sm">
                          <div>
                            <strong>Key Indicators:</strong>
                            <ul className="list-disc list-inside mt-1 space-y-1">
                              {scenario.keyIndicators.map((indicator, index) => (
                                <li key={index} className="text-muted-foreground">{indicator}</li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <strong>Common Use Case:</strong>
                            <p className="text-muted-foreground mt-1">{scenario.commonUseCase}</p>
                          </div>
                        </div>
                      </CollapsibleContent>
                    </div>
                  </Collapsible>
                ))}
              </div>


            </CardContent>
          </Card>
        </TabsContent>

        {/* Fraud Pattern Tab */}
        <TabsContent value="fraud-patterns" className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold tracking-tight mb-2">Fraud Pattern Detection</h2>
            <p className="text-muted-foreground">
              Run fraud detection algorithms and analyze suspicious patterns
            </p>
          </div>

          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Batch Fraud Patterns
                </span>
                <div className="flex gap-2">
                  <Button 
                    onClick={runPatterns} 
                    disabled={patternLoading || selectedPatterns.length === 0}
                    size="sm"
                  >
                    <Shield className="h-4 w-4 mr-2" />
                    Run Selected ({selectedPatterns.length})
                  </Button>
                  <Button 
                    onClick={runAllPatterns} 
                    disabled={patternLoading}
                    variant="outline"
                    size="sm"
                  >
                    <Activity className="h-4 w-4 mr-2" />
                    Run All
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                             {/* Phase 1 Patterns */}
               <div className="space-y-3">
                 <h3 className="text-lg font-semibold flex items-center space-x-2">
                   <Target className="w-4 h-4 text-blue-600" />
                   <span>Phase 1 - High Priority</span>
                 </h3>
                 <div className="grid gap-3 md:grid-cols-2">
                                     {patterns.filter(p => p.priority === 'Phase 1').map((pattern) => (
                    <div
                      key={pattern.id}
                      className={`p-4 border rounded-lg transition-colors ${
                        selectedPatterns.includes(pattern.id)
                          ? 'border-primary bg-primary/5'
                          : 'border-border'
                      } ${pattern.disabled ? 'opacity-50 bg-gray-50 dark:bg-gray-900' : ''}`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {pattern.enabled !== undefined && (
                            <Switch
                              checked={pattern.enabled}
                              onCheckedChange={() => !pattern.disabled && togglePatternEnabled(pattern.id)}
                              disabled={pattern.disabled}
                            />
                          )}
                          <div 
                            className={`flex-1 ${pattern.disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                            onClick={() => !pattern.disabled && togglePattern(pattern.id)}
                          >
                            <h4 className={`font-medium text-sm ${pattern.disabled ? 'text-gray-400' : ''}`}>
                              {pattern.name}
                              {pattern.disabled && <span className="ml-2 text-xs">(Coming Soon)</span>}
                            </h4>
                          </div>
                        </div>
                        <Badge variant={getPatternRiskColor(pattern.risk_level) as any} className={`text-xs ${pattern.disabled ? 'opacity-50' : ''}`}>
                          {pattern.risk_level}
                        </Badge>
                      </div>
                      <p className={`text-xs mb-2 ${pattern.disabled ? 'text-gray-400' : 'text-muted-foreground'}`}>{pattern.description}</p>
                      {pattern.keyIndicators && (
                        <div className="text-xs">
                          <strong className={pattern.disabled ? 'text-gray-400' : ''}>Key Indicators:</strong>
                          <ul className="list-disc list-inside mt-1 space-y-0.5">
                            {pattern.keyIndicators.slice(0, 2).map((indicator, index) => (
                              <li key={index} className={pattern.disabled ? 'text-gray-400' : 'text-muted-foreground'}>{indicator}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                 </div>
               </div>

                             {/* Phase 2 Patterns */}
               <div className="space-y-3">
                 <h3 className="text-lg font-semibold flex items-center space-x-2">
                   <TrendingUp className="w-4 h-4 text-purple-600" />
                   <span>Phase 2 - Medium Priority</span>
                 </h3>
                 <div className="grid gap-3 md:grid-cols-2">
                                     {patterns.filter(p => p.priority === 'Phase 2').map((pattern) => (
                    <div
                      key={pattern.id}
                      className={`p-4 border rounded-lg transition-colors ${
                        selectedPatterns.includes(pattern.id)
                          ? 'border-primary bg-primary/5'
                          : 'border-border'
                      } ${pattern.disabled ? 'opacity-50 bg-gray-50 dark:bg-gray-900' : ''}`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {pattern.enabled !== undefined && (
                            <Switch
                              checked={pattern.enabled}
                              onCheckedChange={() => !pattern.disabled && togglePatternEnabled(pattern.id)}
                              disabled={pattern.disabled}
                            />
                          )}
                          <div 
                            className={`flex-1 ${pattern.disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                            onClick={() => !pattern.disabled && togglePattern(pattern.id)}
                          >
                            <h4 className={`font-medium text-sm ${pattern.disabled ? 'text-gray-400' : ''}`}>
                              {pattern.name}
                              {pattern.disabled && <span className="ml-2 text-xs">(Coming Soon)</span>}
                            </h4>
                          </div>
                        </div>
                        <Badge variant={getPatternRiskColor(pattern.risk_level) as any} className={`text-xs ${pattern.disabled ? 'opacity-50' : ''}`}>
                          {pattern.risk_level}
                        </Badge>
                      </div>
                      <p className={`text-xs mb-2 ${pattern.disabled ? 'text-gray-400' : 'text-muted-foreground'}`}>{pattern.description}</p>
                      {pattern.keyIndicators && (
                        <div className="text-xs">
                          <strong className={pattern.disabled ? 'text-gray-400' : ''}>Key Indicators:</strong>
                          <ul className="list-disc list-inside mt-1 space-y-0.5">
                            {pattern.keyIndicators.slice(0, 2).map((indicator, index) => (
                              <li key={index} className={pattern.disabled ? 'text-gray-400' : 'text-muted-foreground'}>{indicator}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                 </div>
               </div>

                             {/* Phase 3 Patterns */}
               <div className="space-y-3">
                 <h3 className="text-lg font-semibold flex items-center space-x-2">
                   <Globe className="w-4 h-4 text-gray-600" />
                   <span>Phase 3 - Lower Priority</span>
                 </h3>
                 <div className="grid gap-3 md:grid-cols-2">
                                     {patterns.filter(p => p.priority === 'Phase 3').map((pattern) => (
                    <div
                      key={pattern.id}
                      className={`p-4 border rounded-lg transition-colors ${
                        selectedPatterns.includes(pattern.id)
                          ? 'border-primary bg-primary/5'
                          : 'border-border'
                      } ${pattern.disabled ? 'opacity-50 bg-gray-50 dark:bg-gray-900' : ''}`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {pattern.enabled !== undefined && (
                            <Switch
                              checked={pattern.enabled}
                              onCheckedChange={() => !pattern.disabled && togglePatternEnabled(pattern.id)}
                              disabled={pattern.disabled}
                            />
                          )}
                          <div 
                            className={`flex-1 ${pattern.disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                            onClick={() => !pattern.disabled && togglePattern(pattern.id)}
                          >
                            <h4 className={`font-medium text-sm ${pattern.disabled ? 'text-gray-400' : ''}`}>
                              {pattern.name}
                              {pattern.disabled && <span className="ml-2 text-xs">(Coming Soon)</span>}
                            </h4>
                          </div>
                        </div>
                        <Badge variant={getPatternRiskColor(pattern.risk_level) as any} className={`text-xs ${pattern.disabled ? 'opacity-50' : ''}`}>
                          {pattern.risk_level}
                        </Badge>
                      </div>
                      <p className={`text-xs mb-2 ${pattern.disabled ? 'text-gray-400' : 'text-muted-foreground'}`}>{pattern.description}</p>
                      {pattern.keyIndicators && (
                        <div className="text-xs">
                          <strong className={pattern.disabled ? 'text-gray-400' : ''}>Key Indicators:</strong>
                          <ul className="list-disc list-inside mt-1 space-y-0.5">
                            {pattern.keyIndicators.slice(0, 2).map((indicator, index) => (
                              <li key={index} className={pattern.disabled ? 'text-gray-400' : 'text-muted-foreground'}>{indicator}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                 </div>
               </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Detection Results
              </CardTitle>
            </CardHeader>
            <CardContent>
              {patternLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : patternResults.length > 0 ? (
                <div className="space-y-4">
                  {patternResults.map((result, index) => (
                    <div key={index} className="p-4 border rounded-lg">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-medium">{result.pattern_name}</h3>
                        <Badge variant="destructive">
                          Score: {result.risk_score.toFixed(1)}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        Detected {result.detected_entities.length} entities
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(result.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center py-8">
                  <p className="text-muted-foreground">
                    No results yet. Run a pattern to see results.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {patternResults.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-destructive">
                      {patternResults.length}
                    </div>
                    <p className="text-sm text-muted-foreground">Patterns Detected</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">
                      {patternResults.reduce((sum, r) => sum + r.detected_entities.length, 0)}
                    </div>
                    <p className="text-sm text-muted-foreground">Total Entities</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-600">
                      {(patternResults.reduce((sum, r) => sum + r.risk_score, 0) / patternResults.length).toFixed(1)}
                    </div>
                    <p className="text-sm text-muted-foreground">Avg Risk Score</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {patternResults.filter(r => r.risk_score > 70).length}
                    </div>
                    <p className="text-sm text-muted-foreground">High Risk</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Scenario Details Dialog */}
      <Dialog open={showScenarioDialog} onOpenChange={setShowScenarioDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <Shield className="w-5 h-5" />
              <span>{selectedScenario?.name}</span>
            </DialogTitle>
            <DialogDescription>
              Detailed information about this fraud detection scenario
            </DialogDescription>
          </DialogHeader>
          {selectedScenario && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Risk Level</label>
                  <Badge className={getRiskLevelColor(selectedScenario.riskLevel)}>
                    {selectedScenario.riskLevel}
                  </Badge>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Priority</label>
                  <Badge className={getPriorityColor(selectedScenario.priority)}>
                    {selectedScenario.priority}
                  </Badge>
                </div>
              </div>
              
              <div>
                <label className="text-sm font-medium text-muted-foreground">Description</label>
                <p className="mt-1 text-sm">{selectedScenario.detailedDescription}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-muted-foreground">Key Indicators</label>
                <ul className="mt-2 space-y-1">
                  {selectedScenario.keyIndicators.map((indicator, index) => (
                    <li key={index} className="text-sm flex items-start space-x-2">
                      <span className="text-primary mt-1">•</span>
                      <span>{indicator}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div>
                <label className="text-sm font-medium text-muted-foreground">Common Use Cases</label>
                <p className="mt-1 text-sm">{selectedScenario.commonUseCase}</p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setShowScenarioDialog(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
} 
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Eye, Shield } from 'lucide-react'
import { useState } from 'react'
import { getRiskLevelColor } from '@/lib/utils'

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

const fraudScenarios: FraudScenario[] = [
    // Real-time scenarios (RT1-RT4)
    {
        id: 'RT1',
        name: 'Transaction with Flagged Accounts',
        description: 'Threat detection via 2-hop lookup',
        riskLevel: 'High',
        enabled: true,
        priority: 'Phase 1',
        keyIndicators: [
            'Transaction directed to known flagged account',
            '1-hop graph lookup for immediate detection',
            '2-hop graph lookup for neighborhood analysis',
            'Real-time risk assessment'
        ],
        commonUseCase: 'Immediate threat detection, known fraudster connections',
        detailedDescription: 'Real-time detection system that flags transactions sent to accounts that have been previously identified as fraudulent, or have transactions with accounts identified as fraudulaent. Uses 1-hop graph lookups for immediate threat assessment and 2-hop lookups for neighborhood analysis.'
    },
    {
        id: 'RT2',
        name: 'Transactions with Users Associated with Flagged Devices',
        description: 'Detect threats through flagged device usage',
        riskLevel: 'High',
        enabled: true,
        priority: 'Phase 1',
        keyIndicators: [
            'Transactions directed to users associated with fradulent devices',
            'Multi-hop neighborhood analysis',
            'Transaction history analysis'
        ],
        commonUseCase: 'Immediate threat detection, known fraudster connections',
        detailedDescription: ''
    },
    {
        id: 'RT3',
        name: 'Supernode Detection (High-Degree)',
        description: 'Alert on highly connected accounts',
        riskLevel: 'Medium-High',
        enabled: false,
        priority: 'Phase 1',
        keyIndicators: [
            'Abnormally high connection count',
            'Centrality score above threshold',
            'Hub-like transaction patterns'
        ],
        commonUseCase: 'Money laundering hubs, distribution networks',
        detailedDescription: 'Identifies accounts with unusually high connectivity in the transaction graph, which may indicate central nodes in money laundering or distribution networks.',
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
        enabled: false,
        priority: 'Phase 1',
        keyIndicators: [
            'Multiple transactions in short time window',
            'Same user account activity',
            'Rapid transaction succession pattern'
        ],
        commonUseCase: 'Account takeover, automated fraud attacks',
        detailedDescription: 'Real-time detection of rapid successive transactions from the same user account, which may indicate account takeover or automated fraud attacks.',
        disabled: true
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

const Scenarios = () => {
    const [scenarios, setScenarios] = useState<FraudScenario[]>(fraudScenarios)
    const [expandedScenarios, setExpandedScenarios] = useState<Set<string>>(new Set())

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
            if(newSet.has(scenarioId)) newSet.delete(scenarioId);
            else newSet.add(scenarioId);
            return newSet
        })
    }

    return (
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
                <div className="space-y-3">
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
                                                disabled={scenario.disabled}/>
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
    )
}

export default Scenarios
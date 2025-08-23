import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertTriangle, Clock, Flag, Shield, Target } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { formatDateTime, getRiskLevel } from "@/lib/utils";

export interface FraudResult {
    fraud_score: number
    status: string
    rule: string
    timestamp: string
    reason: string
    details: string
    is_fraud: boolean
}

const Analysis = ({ fraudResults }: { fraudResults: FraudResult[] }) => (
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
            {fraudResults.length > 0 ? (
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
                                        <span className="font-medium">{formatDateTime(result.timestamp)}</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Flag className="h-4 w-4 text-muted-foreground" />
                                        <span className="text-muted-foreground">Status:</span>
                                        <span className="font-medium capitalize">{result.status}</span>
                                    </div>
                                </div>
                                {result.details && (
                                <div className="mt-3 p-3 bg-gray-100 rounded-lg">
                                    <h5 className="text-sm font-medium mb-2">Detection Details:</h5>
                                    <div className="text-sm text-gray-600">
                                        <pre className="whitespace-pre-wrap">{result.details}</pre>
                                    </div>
                                </div>)}
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
)

export default Analysis;
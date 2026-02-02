'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
    Database, 
    Upload, 
    RefreshCw, 
    CheckCircle, 
    XCircle, 
    Loader2,
    HardDrive,
    Users,
    CreditCard,
    Smartphone,
    GitBranch,
    AlertTriangle,
    Play
} from 'lucide-react'
import { toast } from 'sonner'

interface BulkLoadStatus {
    loading: boolean
    success?: boolean
    message?: string
    error?: string
    status?: string
    step?: string
    complete?: boolean
    progress_percentage?: number
    elements_written?: number
    statistics?: {
        total_vertices: number
        total_edges: number
        users: number
        accounts: number
        devices: number
        vertex_counts_by_label: Record<string, number>
        edge_counts_by_label: Record<string, number>
    }
}

interface GraphStats {
    users: number
    accounts: number
    devices: number
    transactions: number
    total_vertices: number
    total_edges: number
}

const DataManagement = () => {
    const [bulkLoadStatus, setBulkLoadStatus] = useState<BulkLoadStatus>({ loading: false })
    const [isLoading, setIsLoading] = useState(false)
    const [graphStats, setGraphStats] = useState<GraphStats | null>(null)
    const [loadingStats, setLoadingStats] = useState(false)

    // Fetch current graph statistics
    const fetchGraphStats = async () => {
        setLoadingStats(true)
        try {
            const response = await fetch('/api/dashboard/stats')
            if (response.ok) {
                const data = await response.json()
                setGraphStats({
                    users: data.users || 0,
                    accounts: 0, // Will get from detailed stats
                    devices: 0,
                    transactions: data.txns || 0,
                    total_vertices: 0,
                    total_edges: 0
                })
            }
        } catch (error) {
            console.error('Failed to fetch graph stats:', error)
        } finally {
            setLoadingStats(false)
        }
    }

    useEffect(() => {
        fetchGraphStats()
    }, [])

    // Trigger bulk load
    const handleBulkLoad = async () => {
        setIsLoading(true)
        setBulkLoadStatus({ loading: true, message: 'Starting bulk load...' })
        
        try {
            const response = await fetch('/api/bulk-load-csv', {
                method: 'POST',
            })
            
            const data = await response.json()
            
            if (data.success) {
                setBulkLoadStatus({
                    loading: false,
                    success: true,
                    message: data.message || 'Bulk load started successfully',
                    statistics: data.statistics
                })
                toast.success('Bulk load initiated successfully!')
                
                // Start polling for status
                pollBulkLoadStatus()
            } else {
                setBulkLoadStatus({
                    loading: false,
                    success: false,
                    error: data.detail || data.error || 'Failed to start bulk load'
                })
                toast.error('Failed to start bulk load')
            }
        } catch (error) {
            setBulkLoadStatus({
                loading: false,
                success: false,
                error: 'Network error - failed to connect to backend'
            })
            toast.error('Failed to connect to backend')
        } finally {
            setIsLoading(false)
        }
    }

    // Poll for bulk load status
    const pollBulkLoadStatus = async () => {
        let attempts = 0
        const maxAttempts = 60 // 5 minutes max
        
        const checkStatus = async (): Promise<boolean> => {
            try {
                const response = await fetch('/api/bulk-load-status')
                const data = await response.json()
                
                // Update status display with current progress
                setBulkLoadStatus({
                    loading: !data.complete,
                    success: data.complete,
                    message: data.message || `Status: ${data.status}`,
                    status: data.status,
                    step: data.step,
                    complete: data.complete,
                    progress_percentage: data.progress_percentage,
                    elements_written: data.elements_written
                })
                
                if (data.complete) {
                    toast.success('Bulk load completed!')
                    fetchGraphStats() // Refresh stats
                    return true
                } else if (data.status?.toLowerCase().includes('failed') || data.status?.toLowerCase().includes('error')) {
                    setBulkLoadStatus(prev => ({
                        ...prev,
                        loading: false,
                        success: false,
                        error: data.error || 'Bulk load failed'
                    }))
                    toast.error('Bulk load failed')
                    return true
                }
                
                return false
            } catch (error) {
                console.error('Error polling status:', error)
                return false
            }
        }
        
        const poll = async () => {
            if (attempts >= maxAttempts) {
                setBulkLoadStatus(prev => ({
                    ...prev,
                    loading: false,
                    message: 'Bulk load is still running in the background. Click refresh to check status.'
                }))
                return
            }
            
            const done = await checkStatus()
            if (!done) {
                attempts++
                setTimeout(poll, 3000) // Check every 3 seconds
            }
        }
        
        // Wait a bit before starting to poll
        setTimeout(poll, 2000)
    }

    // Check bulk load status manually
    const handleCheckStatus = async () => {
        setLoadingStats(true)
        try {
            const response = await fetch('/api/bulk-load-status')
            const data = await response.json()
            
            if (data.success) {
                setBulkLoadStatus({
                    loading: !data.complete,
                    success: data.complete,
                    message: data.message || `Status: ${data.status}`,
                    status: data.status,
                    step: data.step,
                    complete: data.complete,
                    progress_percentage: data.progress_percentage,
                    elements_written: data.elements_written
                })
                
                if (data.complete) {
                    toast.success('Bulk load completed!')
                } else {
                    toast.info(`Bulk load ${data.status}: ${data.step || 'processing...'}`)
                }
            } else {
                setBulkLoadStatus({
                    loading: false,
                    success: false,
                    error: data.error || data.message || 'Unknown error'
                })
                toast.error(data.error || 'Failed to get status')
            }
            
            // Also refresh graph stats
            await fetchGraphStats()
        } catch (error) {
            toast.error('Failed to check status')
        } finally {
            setLoadingStats(false)
        }
    }

    return (
        <div className="grid gap-6 md:grid-cols-2">
            {/* Bulk Load Controls */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Database className="h-5 w-5" />
                        Bulk Data Load
                    </CardTitle>
                    <CardDescription>
                        Load sample data from CSV files into the graph database
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="p-4 bg-muted/50 rounded-lg space-y-2">
                        <p className="text-sm font-medium">Data Sources:</p>
                        <ul className="text-sm text-muted-foreground space-y-1">
                            <li className="flex items-center gap-2">
                                <Users className="h-4 w-4" />
                                <span>10,000 Users</span>
                            </li>
                            <li className="flex items-center gap-2">
                                <CreditCard className="h-4 w-4" />
                                <span>~21,000 Accounts</span>
                            </li>
                            <li className="flex items-center gap-2">
                                <Smartphone className="h-4 w-4" />
                                <span>~25,000 Devices</span>
                            </li>
                            <li className="flex items-center gap-2">
                                <GitBranch className="h-4 w-4" />
                                <span>Ownership & Usage relationships</span>
                            </li>
                        </ul>
                    </div>

                    {/* Status Display */}
                    {(bulkLoadStatus.message || bulkLoadStatus.status) && (
                        <div className={`p-4 rounded-lg flex items-start gap-3 ${
                            bulkLoadStatus.complete || bulkLoadStatus.success
                                ? 'bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800' 
                                : bulkLoadStatus.error 
                                    ? 'bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800'
                                    : 'bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800'
                        }`}>
                            {bulkLoadStatus.loading ? (
                                <Loader2 className="h-5 w-5 animate-spin text-blue-600 flex-shrink-0" />
                            ) : bulkLoadStatus.complete || bulkLoadStatus.success ? (
                                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                            ) : bulkLoadStatus.error ? (
                                <XCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
                            ) : (
                                <AlertTriangle className="h-5 w-5 text-blue-600 flex-shrink-0" />
                            )}
                            <div className="flex-1 min-w-0">
                                <p className={`text-sm font-medium ${
                                    bulkLoadStatus.complete || bulkLoadStatus.success ? 'text-green-800 dark:text-green-300' :
                                    bulkLoadStatus.error ? 'text-red-800 dark:text-red-300' :
                                    'text-blue-800 dark:text-blue-300'
                                }`}>
                                    {bulkLoadStatus.error || bulkLoadStatus.message}
                                </p>
                                {bulkLoadStatus.step && !bulkLoadStatus.complete && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Current step: <span className="font-medium">{bulkLoadStatus.step}</span>
                                    </p>
                                )}
                                {bulkLoadStatus.elements_written && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Elements written: <span className="font-medium">{bulkLoadStatus.elements_written.toLocaleString()}</span>
                                    </p>
                                )}
                                {bulkLoadStatus.progress_percentage !== undefined && (
                                    <div className="mt-2">
                                        <div className="flex justify-between text-xs text-muted-foreground mb-1">
                                            <span>Progress</span>
                                            <span>{bulkLoadStatus.progress_percentage}%</span>
                                        </div>
                                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                                            <div 
                                                className="h-full bg-blue-500 transition-all duration-300"
                                                style={{ width: `${bulkLoadStatus.progress_percentage}%` }}
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Warning */}
                    <div className="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                        <p className="text-sm text-amber-800 dark:text-amber-300 flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4" />
                            This will load/reload all sample data. Existing data may be affected.
                        </p>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3">
                        <Button 
                            onClick={handleBulkLoad} 
                            disabled={isLoading}
                            className="flex-1"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Loading...
                                </>
                            ) : (
                                <>
                                    <Play className="h-4 w-4 mr-2" />
                                    Start Bulk Load
                                </>
                            )}
                        </Button>
                        <Button 
                            variant="outline" 
                            onClick={handleCheckStatus}
                            disabled={loadingStats}
                        >
                            {loadingStats ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <RefreshCw className="h-4 w-4" />
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Current Database Statistics */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <HardDrive className="h-5 w-5" />
                        Database Statistics
                    </CardTitle>
                    <CardDescription>
                        Current data in the graph database
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-muted/50 rounded-lg text-center">
                            <Users className="h-6 w-6 mx-auto mb-2 text-purple-500" />
                            <p className="text-2xl font-bold">
                                {loadingStats ? (
                                    <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                                ) : (
                                    graphStats?.users?.toLocaleString() || '0'
                                )}
                            </p>
                            <p className="text-sm text-muted-foreground">Users</p>
                        </div>
                        <div className="p-4 bg-muted/50 rounded-lg text-center">
                            <CreditCard className="h-6 w-6 mx-auto mb-2 text-blue-500" />
                            <p className="text-2xl font-bold">
                                {loadingStats ? (
                                    <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                                ) : (
                                    '~21K'
                                )}
                            </p>
                            <p className="text-sm text-muted-foreground">Accounts</p>
                        </div>
                        <div className="p-4 bg-muted/50 rounded-lg text-center">
                            <Smartphone className="h-6 w-6 mx-auto mb-2 text-cyan-500" />
                            <p className="text-2xl font-bold">
                                {loadingStats ? (
                                    <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                                ) : (
                                    '~25K'
                                )}
                            </p>
                            <p className="text-sm text-muted-foreground">Devices</p>
                        </div>
                        <div className="p-4 bg-muted/50 rounded-lg text-center">
                            <GitBranch className="h-6 w-6 mx-auto mb-2 text-green-500" />
                            <p className="text-2xl font-bold">
                                {loadingStats ? (
                                    <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                                ) : (
                                    graphStats?.transactions?.toLocaleString() || '0'
                                )}
                            </p>
                            <p className="text-sm text-muted-foreground">Transactions</p>
                        </div>
                    </div>

                    <div className="pt-4 border-t">
                        <Button 
                            variant="outline" 
                            className="w-full"
                            onClick={fetchGraphStats}
                            disabled={loadingStats}
                        >
                            {loadingStats ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Refreshing...
                                </>
                            ) : (
                                <>
                                    <RefreshCw className="h-4 w-4 mr-2" />
                                    Refresh Statistics
                                </>
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

export default DataManagement

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Activity, Database, RefreshCw, Trash2 } from 'lucide-react'
import { useEffect, useState, type Dispatch, type SetStateAction } from 'react'
import { Transaction } from '@/components/UserDetails/Transactions'

export interface GenerationStats {
    isRunning: boolean
    totalGenerated: number
    currentRate: number
    startTime?: string
    duration: string
}

interface Props {
    stats: GenerationStats
    setStats: Dispatch<SetStateAction<GenerationStats>>
    recentTxns: Transaction[]
    setRecentTxns: Dispatch<SetStateAction<Transaction[]>>
}

const Statistics = ({
    stats,
    setStats,
    recentTxns,
    setRecentTxns
}: Props) => {
    const [loading, setLoading] = useState(false)
    const [confirmed, setConfirmed] = useState(false)

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

    const clearTxns = () => {
        if (!confirmed) {
            setConfirmed(true)
            return
        }

        setLoading(true);
        setRecentTxns([])
        setStats(prev => ({ ...prev, totalGenerated: 0 }))
        setConfirmed(false)
        setLoading(false);
    }

    return (
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
                <div className="pt-4 border-t">
                    <h4 className="text-sm font-medium mb-3 flex items-center space-x-2">
                        <Database className="w-4 h-4" />
                        <span>Quick Actions</span>
                    </h4>
                    <div className="text-xs text-muted-foreground mb-2">
                        {confirmed
                            ? "This action cannot be undone. Click 'Confirm Clear' to proceed."
                            : "This will remove all generated transactions from the system."
                        }
                    </div>
                    <div className="space-y-3">
                        {!confirmed &&
                        <Button
                            variant="outline"
                            onClick={clearTxns}
                            disabled={loading || recentTxns.length === 0}
                            className="w-full"
                            size="sm"
                        >
                            {loading ? (
                                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                            ) : (
                                <Trash2 className="w-4 h-4 mr-2" />
                            )}
                            Clear All Transactions
                        </Button>}
                        {confirmed && (
                        <div className='flex gap-2'>
                            <Button
                                variant={"destructive"}
                                onClick={clearTxns}
                                size="sm"
                                className='w-1/2'
                            >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Confirm
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => setConfirmed(false)}
                                size="sm"
                                className='w-1/2'
                            >
                                Cancel
                            </Button>
                        </div>)}
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}

export default Statistics
'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Play, RefreshCw, Settings, Square } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface Props {
    loading: boolean
    isGenerating: boolean
    currentRate: number
    startGeneration: (rate: number) => Promise<void>
    stopGeneration: () => Promise<void>
}

const Controls = ({
    loading,
    isGenerating,
    currentRate,
    startGeneration,
    stopGeneration
}: Props) => {
    const [generationRate, setGenerationRate] = useState(currentRate)

    return (
        <Card className='flex flex-col'>
            <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                    <Settings className="w-5 h-5" />
                    <span>Generation Controls</span>
                </CardTitle>
                <CardDescription>
                    Start, stop, and configure transaction generation
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 grow flex flex-col">
                <div className="space-y-2">
                    <label className="text-sm font-medium">Generation Rate (transactions/sec)</label>
                    <Input
                        name='generation-rate'
                        type="number"
                        min="1"
                        max="50"
                        value={generationRate}
                        onChange={(e) => setGenerationRate(parseInt(e.target.value) || 1)}
                        disabled={isGenerating}
                    />
                </div>
                <div className="flex space-x-2 grow items-end">
                    <Button
                        onClick={() => startGeneration(generationRate)}
                        disabled={isGenerating || loading}
                        className="flex-1"
                    >
                        {loading ? (
                            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                            <Play className="w-4 h-4 mr-2" />
                        )}
                        Start
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={stopGeneration}
                        disabled={!isGenerating || loading}
                        className="flex-1"
                    >
                        {loading ? (
                            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                            <Square className="w-4 h-4 mr-2" />
                        )}
                        Stop
                    </Button>
                </div>
            </CardContent>
        </Card>
    )
}

export default Controls
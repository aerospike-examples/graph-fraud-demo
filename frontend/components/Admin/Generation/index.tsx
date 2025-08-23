'use client'

import { useEffect, useState } from 'react'
import type { Transaction } from '@/components/UserDetails/Transactions'
import Statistics, { type GenerationStats } from './Statistics'
import Controls from './Controls'
import Manual from './Manual'
import Recent from './Recent'

interface Props {
	accounts: []
	initStats: GenerationStats
	initRecent: Transaction[]
}

const Generation = ({ accounts, initStats, initRecent }: Props) => {
    const [isGenerating, setIsGenerating] = useState(initStats.isRunning)
	const [stats, setStats] = useState<GenerationStats>(initStats)
  	const [recentTxns, setRecentTxns] = useState<Transaction[]>(initRecent)
	const [loading, setLoading] = useState(false);
	
	const pollStatus = () => {
		const interval: NodeJS.Timeout | undefined =
			isGenerating ?
			setInterval(async () => {
				try {
					const response = await fetch('/api/transaction-generation/status')
					if (response.ok) {
						const statusData = await response.json()
						setStats(prev => ({
							...prev,
							totalGenerated: statusData.total_generated,
							currentRate: statusData.generation_rate
						}))
						if (statusData.last_10_transactions) {
							setRecentTxns(statusData.last_10_transactions)
						}
					}
				} 
				catch (err) {
					console.error('Error polling status:', err)
				}
			}, 2000)
			: undefined
		return interval
	}
	
	useEffect(() => {	
		const interval = pollStatus();
		return () => {
			if (interval) clearInterval(interval);
		}
	}, [isGenerating])

	const startGeneration = async (rate: number) => {
		setLoading(true);
		const response = await fetch(`/api/transaction-generation/start?rate=${rate}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		if(response.ok) {
			setIsGenerating(true)
			setStats(prev => ({ ...prev, isRunning: true, startTime: new Date().toISOString() }));
			console.log('Transaction generation started successfully!');
		}
		else {
			const errorData = await response.json();
			console.error(errorData.detail || 'Failed to start generation');
		}
		setLoading(false);
	}

	const stopGeneration = async () => {
		setLoading(true);
		const response = await fetch('/api/transaction-generation/stop', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		if(response.ok) {
			setIsGenerating(false)
			setStats(prev => ({ ...prev, isRunning: false }))
			console.log('Transaction generation stopped successfully!')
		} 
		else {
			const errorData = await response.json();
			console.error(errorData.detail || 'Failed to stop generation');
		}
		setLoading(false)
	}

    return (
        <>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Controls
				loading={loading}
				isGenerating={isGenerating}
				startGeneration={startGeneration}
				stopGeneration={stopGeneration} />
			<Statistics
				stats={stats}
				setStats={setStats}
				recentTxns={recentTxns}
				setRecentTxns={setRecentTxns} />
            <Manual accounts={accounts} />
        </div>
        <Recent recentTxns={recentTxns} />
        </>
    )
}

export default Generation
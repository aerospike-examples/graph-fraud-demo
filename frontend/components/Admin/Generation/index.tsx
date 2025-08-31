'use client'

import { useEffect, useState } from 'react'
import type { Transaction } from '@/components/UserDetails/Transactions'
import Statistics, { type GenerationStats } from './Statistics'
import Controls from './Controls'
import Manual from './Manual'
import Recent from './Recent'
import { getDuration } from '@/lib/utils'

const Generation = () => {
	const [stats, setStats] = useState<GenerationStats>({
		isRunning: false,
		totalGenerated: 0,
		currentRate: 1,
		duration: '00:00:00',
		startTime: new Date().toISOString()
	})
	const [isGenerating, setIsGenerating] = useState(stats.isRunning)
	const [recentTxns, setRecentTxns] = useState<Transaction[]>([])
	const [loading, setLoading] = useState(false)

	const getGenerationStats = async () => {
		const response = await fetch('/api/transaction-generation/status')
    	const { 
			status, 
			transaction_count: totalGenerated, 
			generation_rate: currentRate, 
			last_10_transactions,
			start_time: startTime
		} = await response.json()

		const isRunning = status === 'running';
		setIsGenerating(isRunning)
		setStats({
			isRunning,
			totalGenerated,
			currentRate,
			duration: (isRunning && startTime) ? getDuration(startTime) : "00:00:00",
			startTime
		})
		setRecentTxns(last_10_transactions)
	}
	
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
							totalGenerated: statusData.transaction_count,
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
			}, 1000)
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
		try {
			const startTime = new Date().toISOString()
			const response = await fetch(`/api/transaction-generation/start?rate=${rate}&start=${startTime}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});
			if(response.ok) {
				setIsGenerating(true)
				setStats(prev => ({ ...prev, isRunning: true, startTime }));
				console.log('Transaction generation started successfully!');
			}
			else {
				const errorData = await response.json();
				throw new Error(`${errorData.detail} || 'Failed to start generation`);
			}
		}
		catch(e) {
			console.error(e)
		}
		finally {
			setLoading(false);
		}
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

	useEffect(() => {
		getGenerationStats()
	}, []);

    return (
        <>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Controls
				key={stats.currentRate.toString()}
				loading={loading}
				isGenerating={isGenerating}
				currentRate={stats.currentRate}
				startGeneration={startGeneration}
				stopGeneration={stopGeneration} />
			<Statistics
				stats={stats}
				setStats={setStats}
				recentTxns={recentTxns}
				setRecentTxns={setRecentTxns} />
            <Manual />
        </div>
        {/* <Recent recentTxns={recentTxns} /> */}
        </>
    )
}

export default Generation
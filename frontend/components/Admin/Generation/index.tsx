'use client'

import {type Dispatch, type SetStateAction, useEffect, useState } from 'react'
import Statistics, { type GenerationStats } from './Statistics'
import Controls from './Controls'
import Manual from './Manual'
import { getDuration } from '@/lib/utils'
import { toast } from "sonner"


interface Props {
	isGenerating: boolean
	setIsGenerating: Dispatch<SetStateAction<boolean>>
}

const Generation = ({ isGenerating, setIsGenerating }: Props) => {
	const [stats, setStats] = useState<GenerationStats>({
		isRunning: false,
		totalGenerated: 0,
		currentRate: 1,
		duration: '00:00:00',
		startTime: new Date().toISOString()
	})

	const getGenerationStats = async () => {
		const response = await fetch('/api/transaction-generation/status')
    	const { 
			status, 
			transaction_count: totalGenerated, 
			generation_rate: currentRate,
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
		try {
			const startTime = new Date().toISOString()
			const response = await fetch('/generate/start', {
				headers: {
					"Content-Type": "application/json"
				},
				method: 'POST',
				body: JSON.stringify({ rate })
			})
			if(response.ok) {
				setIsGenerating(true)
				toast.success("Transaction generation started")
				setStats(prev => ({ ...prev, isRunning: true, startTime }))
			}
			else {
				const errorData = await response.json();
				throw new Error(`${errorData.detail} || 'Failed to start generation`);
			}
		}
		catch(e) {
			console.error(e)
			toast.error("Transaction generation failed to start")
		}
	}

	const stopGeneration = async () => {
		try {
			const response = await fetch('/generate/stop');
			if(response.ok) {
				setIsGenerating(false)
				toast.success("Transaction generation stopped")
				setStats(prev => ({ ...prev, isRunning: false }))
			} 
			else {
				const errorData = await response.json();
				throw new Error(`${errorData.detail} || 'Failed to stop generation`);
			}
		}
		catch(e) {
			console.error(e)
			toast.error("Transaction generation failed to stop")
		}
	}

	useEffect(() => {
		getGenerationStats()
	}, []);

    return (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Controls
				key={stats.currentRate.toString()}
				isGenerating={isGenerating}
				currentRate={stats.currentRate}
				startGeneration={startGeneration}
				stopGeneration={stopGeneration} />
			<Statistics
				isGenerating={isGenerating}
				stats={stats}
				setStats={setStats} />
            <Manual />
        </div>
    )
}

export default Generation
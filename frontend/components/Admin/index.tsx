'use client'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useState } from 'react'
import { Activity, BarChart3, Shield, Zap } from 'lucide-react'
import Performance from './Performance'
import Generation from './Generation'
import Scenarios from './Scenarios'
import Patterns from './Patterns'

const Admin = () => {
    const [active, setActive] = useState('generation');

    return (
        <Tabs value={active} onValueChange={setActive} className="space-y-4">
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
            <TabsContent value="generation" className="space-y-4">
                <Generation />
            </TabsContent>
            <TabsContent value="real-time-fraud" className="space-y-4">
                <Scenarios />
            </TabsContent>
            <TabsContent value="fraud-patterns" className="space-y-4">
                <Patterns />
            </TabsContent>
            <TabsContent value="performance" className="space-y-4">
                <Performance />                
            </TabsContent>
        </Tabs>
    )
}

export default Admin;
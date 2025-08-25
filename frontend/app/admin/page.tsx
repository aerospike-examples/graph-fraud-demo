'use server'

import Admin from '@/components/Admin'
import { api } from '@/lib/api'
import type { Transaction } from '@/components/UserDetails/Transactions'
import Seed from '@/components/Seed'

export default async function AdminPage() {
	const initStats = {
		isRunning: false,
		totalGenerated: 0,
		currentRate: 0,
		duration: '00:00:00',
		startTime: new Date().toISOString()
	}
	const initRecent: Transaction[] = []
	const response = await api.get('/transaction-generation/status')
    const { status, total_generated, generation_rate, last_10_transactions } = await response.data
	
	initStats.isRunning = status === 'running'
	initStats.totalGenerated = total_generated ?? initStats.totalGenerated
	initStats.currentRate = generation_rate ?? initStats.currentRate
	if(last_10_transactions) {
		initRecent.push(...last_10_transactions)
	}

	const acctRes = await api.get('/accounts')
    const { accounts } = acctRes.data

  	return (
    	<div className="space-y-6">
      		<div className="flex items-center justify-between">
			<div>
				<h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
				<p className="text-muted-foreground">
					Manage transaction generation and fraud detection scenarios
				</p>
			</div>
        	<div className="flex items-center space-x-4">
				<Seed />
				{/* {stats.isRunning && (
					<div className="text-right">
					<div className="text-sm text-muted-foreground">Live Transactions</div>
					<div className="text-2xl font-bold text-green-600 animate-pulse">
						{stats.totalGenerated.toLocaleString()}
					</div>
					</div>
				)} */}
				{/* <Badge variant={stats.isRunning ? "default" : "secondary"}>
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
				</Badge> */}
        	</div>
      	</div>
      	<Admin 
          accounts={accounts}
          initStats={initStats}
          initRecent={initRecent} />

      {/* Scenario Details Dialog */}
      {/* <Dialog open={showScenarioDialog} onOpenChange={setShowScenarioDialog}>
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
      </Dialog> */}
    </div>
  )
} 
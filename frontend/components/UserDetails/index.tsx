'use client'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useState } from 'react'
import Accounts from './Accounts'
import Transactions from './Transactions'
import Devices from './Devices'
import Connections from './Connections'
import type { TransactionDetail } from '@/components/UserDetails/Transactions';
import type { Device } from '@/components/UserDetails/Devices';
import type { Account } from '@/components/UserDetails/Accounts'
import type { Connection } from '@/components/UserDetails/Connections'

export interface UserSummary {
    user: User
    accounts: Account[]
    txns: TransactionDetail[]
    total_txns: number
    total_sent: number
    total_recd: number
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    connected_users: Connection[]
    devices?: Device[]
}

export interface User {
    "1"?: string
    id?: string
    name: string
    email: string
    age: number
    signup_date: string
    location: string
    risk_score: number
    is_flagged: boolean
    phone?: string
    occupation?: string
}

const Details = ({ userDetails }: { userDetails: UserSummary }) => {
    const [active, setActive] = useState('accounts');
    return (
        <Tabs value={active} onValueChange={setActive} className="space-y-4">
            <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="accounts">Accounts</TabsTrigger>
                <TabsTrigger value="transactions">Transactions</TabsTrigger>
                <TabsTrigger value="devices">Devices</TabsTrigger>
                <TabsTrigger value="connections">Connections</TabsTrigger>
            </TabsList>
            <TabsContent value="accounts" className="space-y-4">
                <Accounts accounts={userDetails.accounts} />
            </TabsContent>
            <TabsContent value="transactions" className="space-y-4">
                <Transactions txns={userDetails.txns} accounts={userDetails.accounts} name={userDetails.user.name} />
            </TabsContent>
            <TabsContent value="devices" className="space-y-4">
                <Devices devices={userDetails.devices} />
            </TabsContent>
            <TabsContent value="connections" className="space-y-4">
                <Connections devices={userDetails.devices} connections={userDetails.connected_users} />
            </TabsContent>
        </Tabs>
    )
}

export default Details;
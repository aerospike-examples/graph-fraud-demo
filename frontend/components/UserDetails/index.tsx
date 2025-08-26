'use client'

import { Suspense } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useState } from 'react'
import type { UserSummary } from '@/app/users/[id]/page'
import Accounts from './Accounts'
import Transactions from './Transactions'
import Loading from '@/app/loading'
import Devices from './Devices'
import Connections from './Connections'

const Details = ({ userDetails, userId }: { userDetails: Omit<UserSummary, 'user'>, userId: string }) => {
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
                <Suspense fallback={<Loading />}>
                    <Transactions recent_transactions={userDetails.recent_transactions} accounts={userDetails.accounts} />
                </Suspense>
            </TabsContent>
            <TabsContent value="devices" className="space-y-4">
                <Devices devices={userDetails.devices} />
            </TabsContent>
            <TabsContent value="connections" className="space-y-4">
                <Suspense fallback={<Loading />}>
                    <Connections userId={userId} />
                </Suspense>
            </TabsContent>
        </Tabs>
    )
}

export default Details;
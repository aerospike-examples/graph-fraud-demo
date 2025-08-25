'use client'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useState } from 'react'
import Location from './Location'
import Analysis from './Analysis'
import { TransactionDetail } from '@/app/transactions/[id]/page'
import AccountCard from './AccountCard'

const Details = ({ txnDetails }: { txnDetails: TransactionDetail }) => {
    const [active, setActive] = useState('accounts');

    return (
        <Tabs value={active} onValueChange={setActive} className="space-y-4">
            <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="accounts">Accounts</TabsTrigger>
                <TabsTrigger value="devices">Fraud Analysis</TabsTrigger>
                <TabsTrigger value="connections">Location</TabsTrigger>
            </TabsList>
            <TabsContent value="accounts" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                    <AccountCard {...txnDetails.source_account} variant='source' />
                    <AccountCard {...txnDetails.destination_account} variant='destination' />
                </div>
            </TabsContent>
            <TabsContent value="devices" className="space-y-4">
                <Analysis fraudResults={txnDetails.fraud_results} />
            </TabsContent>
            <TabsContent value="connections" className="space-y-4">
                <Location transaction={txnDetails.transaction} />
            </TabsContent>
        </Tabs>
    )
}

export default Details;
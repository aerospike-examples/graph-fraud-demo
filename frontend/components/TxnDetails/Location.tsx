'use client'

import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { MapPin } from 'lucide-react'
import { formatDateTime } from '@/lib/utils'
import Label from '../Label';
import type { Transaction } from '@/components/UserDetails/Transactions';

const Location = ({ txn }: { txn: Transaction }) => {
    console.log(txn)
    return (
        <Card>
            <CardHeader>
                <Label
                    size='2xl'
                    className='font-semibold'
                    icon='map-pin'
                    text='Location Information'
                    subtitle='Geographic and network location details for this transaction' />
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">

            </CardContent>
        </Card>
    )
}

export default Location;
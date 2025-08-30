'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ArrowRight } from 'lucide-react'
import { FormEvent } from 'react'
import Label from './Label'

const Lookup = ({ type }: { type: 'txn' | 'user'}) => {
    const isUser = type === 'user';
    const router = useRouter()
    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()
        const form = e.target as HTMLFormElement
        const formData = new FormData(form)
        const id = formData.get("search-uid")?.toString() ?? ""
        router.push(`/${isUser ? 'users' : 'transactions'}/${isUser ? id.toUpperCase() : id.toLowerCase()}`)
    }

    return (
        <Card>
            <CardHeader>
                <Label
                    size='2xl'
                    className='font-semibold'
                    text={`Quick ${isUser ? "User" : "Transaction"} Lookup`}
                    icon={isUser ? 'user' : 'credit-card'}
                    subtitle={`Enter a ${isUser ? "user" : "transaction"} ID to directly navigate`} />
            </CardHeader>
            <CardContent>
                <form
                    onSubmit={handleSubmit}
                    className="flex gap-2"
                    id="lookup"
                    autoComplete="off"
                >
                    <Input
                        required
                        autoComplete="off"
                        data-1p-ignore 
                        data-bwignore
                        data-lpignore="true" 
                        data-form-type="other"
                        name='search-uid'
                        type='search'
                        placeholder={`Enter ${isUser ? "user" : "transaction"} ID`}
                        className="flex-1" />
                    <Button type='submit'>
                        <ArrowRight className="h-4 w-4 mr-2" />
                        View {isUser ? "Profile" : "Transaction"}
                    </Button>
                </form>
            </CardContent>
        </Card>
    )
}

export default Lookup;
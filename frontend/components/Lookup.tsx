'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { User, ArrowRight } from 'lucide-react'
import { FormEvent } from 'react'

const Lookup = () => {
    const router = useRouter()
    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()
        const form = e.target as HTMLFormElement
        const formData = new FormData(form)
        router.push(`/users/${formData.get("search-uid")?.toString().toUpperCase()}`)
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <User className="h-5 w-5" />
                    Quick User Lookup
                </CardTitle>
                <CardDescription>
                    Enter a user ID to directly view their profile
                </CardDescription>
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
                        placeholder="Enter user ID (e.g., U0006)"
                        className="flex-1" />
                    <Button type='submit'>
                        <ArrowRight className="h-4 w-4 mr-2" />
                        View Profile
                    </Button>
                </form>
            </CardContent>
        </Card>
    )
}

export default Lookup;
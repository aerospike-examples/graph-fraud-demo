'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SearchIcon } from 'lucide-react'
import { FormEvent } from 'react'

interface Props {
    placeholder: string
}

const Search = ({
    placeholder = "Search"
}: Props ) => {
    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()
        const form = e.target as HTMLFormElement
        const formData = new FormData(form)
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="flex gap-2 items-center"
            id="search"
            autoComplete="off"
        >
            <Input
                required
                autoComplete="off"
                data-1p-ignore 
                data-bwignore
                data-lpignore="true" 
                data-form-type="other"
                name='search'
                type='search'
                placeholder={placeholder}
                className="flex-1" />
            <Button type='submit'>
                <SearchIcon className='w-4 h-4' />
            </Button>
        </form>
    )
}

export default Search;
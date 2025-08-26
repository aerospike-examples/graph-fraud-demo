'use client'

import { useState } from "react"
import { Button } from "./ui/button";

const Seed = () => {
    const [loading, setLoading] = useState(false);
    const seedData = async () => {
        setLoading(true)
        try {
            await fetch('/api/bulk-load-csv', { method: "POST" })
        } 
        catch(error) {
            console.error('Failed to load data:', error)
        }
        finally {
            setLoading(false)
        }
    } 

    return (
        <Button onClick={seedData} disabled={loading}>
            {loading ? 'Loading...' : 'Load Data'}
        </Button>
    )
}

export default Seed
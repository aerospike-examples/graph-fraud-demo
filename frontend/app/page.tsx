'use server'

import Main from "@/components/Main"
import {Suspense} from "react"
import RefreshButton from "@/components/RefreshButton";

export default async function Dashboard() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>

                <div className="mb-2 flex items-center justify-between gap-3">
                    <p className="text-muted-foreground">
                        Real-time fraud detection overview
                    </p>
                    <RefreshButton/>
                </div>
            </div>
            <Suspense fallback={<Main loading/>}>
                <Main/>
            </Suspense>
        </div>
    )
} 
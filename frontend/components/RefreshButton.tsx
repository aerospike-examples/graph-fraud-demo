"use client";

import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

export default function RefreshButton() {
    const router = useRouter();
    const [isPending, start] = useTransition();

    return (
        <Button
            variant="outline"
            size="sm"
            className="gap-1"
            onClick={() => start(() => router.refresh())}
            disabled={isPending}
            aria-label="Refresh stats"
            title="Refresh stats"
        >
            <RefreshCw className={`h-4 w-4 ${isPending ? "animate-spin" : ""}`} />
            Refresh
        </Button>
    );
}
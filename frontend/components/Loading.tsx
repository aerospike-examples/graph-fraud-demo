import { Skeleton } from "./ui/skeleton"

export const LoadingTable = ({ pageSize }: { pageSize: number }) => (
    <table className="w-full">
        <thead>
            <tr className="border-b">
                <th className="h-[48px] p-3  flex items-center">
                    <Skeleton className="h-[20px] w-full rounded-full" />                    
                </th>
            </tr>
        </thead>
        <tbody>
            {Array.from({ length: pageSize }).map((_, idx) => (
                <tr key={idx} className="border-b hover:bg-muted/50">
                    <td className="p-3 h-[61px]">
                        <Skeleton className="h-[20px] w-full rounded-full" />
                    </td> 
                </tr>
            ))}
        </tbody>
    </table>
)
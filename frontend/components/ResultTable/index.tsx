'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Eye } from 'lucide-react'
import Pagination from './Pagination'
import clsx from 'clsx'
import { formatCurrency, formatDate, formatDateTime, getRiskLevel } from '@/lib/utils'
import Search from './Search'
import Label, { type LabelProps } from '../Label'
import { Badge } from '../ui/badge'
import {   
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger
} from '../ui/tooltip'
import { LoadingTable } from '../Loading'


export interface Option {
    name: string
    key: string
    sortable?: boolean
    defaultSort?: boolean
    defaultOrder?: 'asc' | 'desc'
    className?: string
    type?: 'date' | 'datetime' | 'currency' | 'risk' | 'fraud'
    label: LabelProps
}

interface Props {
    searchType: 'user' | 'txns'
    title: string
    options: Option[]
    path: string
}

const Results = ({ 
    searchType,
    title,
    options,
    path,
}: Props) => {
    const pathname = usePathname();
    const [currentPage, setCurrentPage] = useState(1)
    const [pageSize, setPageSize] = useState(10)
    const [totalPages, setTotalPages] = useState<number>(0)
    const [totalEntries, setTotalEntries] = useState<number>(0)
    const [orderBy, setOrderBy] = useState<string>(options.filter(opt => opt.defaultSort)[0]?.key ?? options.find(opt => opt.sortable)?.key ?? "")
    const [order, setOrder] = useState<'asc' | 'desc'>(options.filter(opt => opt.defaultSort)[0]?.defaultOrder ?? 'asc')
    const [results, setResults] = useState<Record<string, any>[]>([])
    const [loading, setLoading] = useState(false)

    const fetchData = async (
        oB: string = orderBy,
        o: string = order,
        q?: string
    ) => {
        setLoading(true);
        const response = await fetch(`${path}?page=${currentPage}&page_size=${pageSize}&order_by=${oB}&order=${o}${q ? `&query=${q}` : ''}`);
        const data = await response.json()
        setResults(data.result)
        setTotalPages(data.total_pages)
        setTotalEntries(data.total)
        setTimeout(() => setLoading(false), 300)
    }

    const handleSort = (key: string) => {
        let o: 'asc' | 'desc' = 'asc';
        if(orderBy === key) o = order === 'asc' ? 'desc' : 'asc'        
        setOrderBy(key)
        setOrder(o)
        fetchData(key, o)
    }

    useEffect(() => {
        fetchData()
    }, [currentPage, pageSize])

    return (
        <Card className='grow flex flex-col'>
            <CardHeader className='gap-4'>
                <CardTitle>{title}</CardTitle>
                <Search
                    fetchData={(q) => fetchData(orderBy, order, q)}
                    placeholder={`Search ${title}`}
                    setCurrentPage={() => setCurrentPage(1)} />
            </CardHeader>
            <CardContent className='grow'>
                <div className="overflow-x-auto">
                    {loading ? (
                        <LoadingTable pageSize={pageSize} />
                    ) : (
                        results.length > 0 ? (
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b">
                                        {options.map(({name, key, sortable}) => (
                                            sortable ? (
                                                <th 
                                                    key={key}
                                                    className="text-left p-3 font-medium cursor-pointer hover:bg-muted/50" 
                                                    onClick={() => handleSort(key)}
                                                >
                                                    {name} {orderBy !== key ? '' : order === 'asc' ? '↑' : '↓'}
                                                </th>
                                            ) : (
                                                <th key={key} className="text-left p-3 font-medium">{name}</th>
                                            )
                                        ))}
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.map((result: Record<string, any>) => (
                                        <tr key={result.id} className={clsx("border-b hover:bg-muted/50", (result?.fraud_status === 'review' || result?.fraud_status === 'blocked') && "bg-red-50/30 dark:bg-red-950/10 border-l-2 border-l-red-200")}>
                                            {options.map(({key, type, className, label }, idx) => {
                                                let value = label?.text ? result[label.text]
                                                    : label?.subtitle ? result[label.subtitle]
                                                        : label?.badge ? result[label.badge.text] : ""
                                                if(searchType === 'txns' && key === 'sender') {
                                                    value = result.IN[1]
                                                }
                                                if(searchType === 'txns' && key === 'receiver') {
                                                    value = result.OUT[1]
                                                }
                                                
                                                let risk = { level: "low", color: "success" }

                                                if(type === 'risk') risk = getRiskLevel(result?.risk_score ?? result?.fraud_score ?? 0)
                                                else if(type === 'date') value = formatDate(value);
                                                else if(type === 'datetime') value = formatDateTime(value);
                                                else if(type === 'currency') value = formatCurrency(value);
                                        
                                                return (
                                                    <td key={value ?? idx} className={clsx('p-3', className)}>
                                                        {type !== 'fraud' ? (
                                                            <Label
                                                                {...label}
                                                                className={`${label?.className ?? ""} truncate max-w-48`}
                                                                {...label?.text && { text: value }}
                                                                {...label?.subtitle && { subtitle: value }}
                                                                {...label?.badge && type === 'risk' && { 
                                                                    badge: { 
                                                                        ...label.badge, 
                                                                        text: `${risk.level} ${(value as number ?? 0).toFixed(1)}`,
                                                                        variant: risk.color as any
                                                                    }
                                                                }} />
                                                        ) : (
                                                            !value ? (
                                                                <Badge variant="default" className="text-xs">CLEAN</Badge>
                                                            ) : (
                                                                <TooltipProvider>
                                                                    <Tooltip>
                                                                        <TooltipTrigger className='hover:cursor-default'>
                                                                            <Badge 
                                                                                variant={value === 'blocked' ? 'destructive' : 'secondary'}
                                                                                className="text-xs"
                                                                            >
                                                                                {(value as string)?.toUpperCase() ?? ""}
                                                                            </Badge>
                                                                        </TooltipTrigger>
                                                                        <TooltipContent>
                                                                            {value === 'review' ? (
                                                                                <span className="text-xs text-muted-foreground">Connected to 1 flagged account(s)</span>
                                                                            ) : (
                                                                                result?.details?.length > 1 ? (
                                                                                    <span className="text-xs text-muted-foreground">Multiple fraud triggers - check analysis</span>
                                                                                ) : (
                                                                                    <span className="text-xs text-muted-foreground">{JSON.parse(result?.details ?? "{}")?.reason ?? "Undefined reason"}</span>
                                                                                )
                                                                            )}
                                                                        </TooltipContent>
                                                                    </Tooltip>
                                                                </TooltipProvider>
                                                            )
                                                        )}
                                                    </td>
                                                )
                                            })}
                                            <td className="p-3">
                                                <Link href={`${pathname}/${encodeURIComponent(result.id)}`}>
                                                    <Button 
                                                        variant="outline" 
                                                        size="sm"
                                                    >
                                                        <Eye className="h-4 w-4 mr-1" />
                                                        View Details
                                                    </Button>
                                                </Link>
                                            </td>
                                        </tr>        
                                    ))}
                                </tbody>
                            </table>
                    ) : (
                        <div className="text-center">
                            <p className="text-muted-foreground">
                                No {title} found
                            </p>
                        </div>
                    ))}
                </div>
            </CardContent>
            <CardFooter>
                <Pagination
                    title={title}
                    currentPage={currentPage}
                    totalPages={totalPages}
                    pageSize={pageSize}
                    totalEntries={totalEntries}
                    setPageSize={setPageSize}
                    handlePagination={setCurrentPage} />
            </CardFooter>
        </Card>
    )
}

export default Results;
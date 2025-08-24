'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Eye } from 'lucide-react'
import Pagination from './Pagination'
import Loading from '@/app/loading'
import clsx from 'clsx'
import { formatCurrency, formatDate, formatDateTime, getRiskLevel } from '@/lib/utils'
import RenderCell from './RenderCell'
import Icons from './Icons'
import Search from './Search'

export interface Option {
    name: string
    key: string
    sortable?: boolean
    defaultSort?: boolean
    className?: string
    type?: 'date' | 'datetime' | 'currency'
    icon?: 'mail' | 'map' | 'user' | 'calendar' | 'card'
    renderer: 'small' | 'medium' | 'muted' | 'mono' | 'risk' | 'fraud'
}

interface Props {
    title: string
    options: Option[]
    path: string
    dataKey: string
}

const Results = ({ 
    title,
    options,
    path,
    dataKey,
}: Props) => {
    const pathname = usePathname();
    const [currentPage, setCurrentPage] = useState(1)
    const [pageSize, setPageSize] = useState(10)
    const [totalPages, setTotalPages] = useState<number>(0)
    const [totalEntries, setTotalEntries] = useState<number>(0)
    const [sortBy, setSortBy] = useState<string>(options.filter(opt => opt.defaultSort)[0]?.key ?? options.find(opt => opt.sortable)?.key ?? "")
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
    const [results, setResults] = useState<Record<string, any>[]>([])
    const [loading, setLoading] = useState(true)

    const getSortIcon = (field: string) => {
        if (sortBy !== field) return null
        return sortOrder === 'asc' ? '↑' : '↓'
    }

    const fetchData = async (orderBy = sortBy, order= sortOrder) => {
        setLoading(true)
        const response = await fetch(`${path}?page=${currentPage}&page_size=${pageSize}&order_by=${orderBy}&order=${order}`);
        const data = await response.json()
        setResults(data[dataKey])
        setTotalPages(data.total_pages)
        setTotalEntries(data.total)
        setLoading(false)
    }

    const handleSort = (key: string) => {
        let order: 'asc' | 'desc' = 'asc';
        if(sortBy === key) order = sortOrder === 'asc' ? 'desc' : 'asc'        
        setSortBy(key)
        setSortOrder(order)
        fetchData(key, order)
    }

    useEffect(() => {
        fetchData()
    }, [currentPage, pageSize])

    return (
        <>
        <Card className='grow flex flex-col'>
            <CardHeader className='gap-4'>
                <CardTitle>{title}</CardTitle>
                <Search
                    placeholder={`Search ${title}`} />
            </CardHeader>
            <CardContent className='grow'>
                {loading ? <Loading /> : (
                results.length > 0 ? (
                    <div className="overflow-x-auto">
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
                                                {name} {getSortIcon(key)}
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
                                        {options.map(({key, renderer, icon, type, className }) => {
                                            let value = result[key]
                                            let risk = getRiskLevel(result?.risk_score ?? result?.fraud_score)
                                            
                                            if(type === 'date') value = formatDate(value);
                                            else if(type === 'datetime') value = formatDateTime(value);
                                            else if(type === 'currency') value = formatCurrency(value);

                                            return (
                                                <td key={value} className={clsx('p-3', className)}>
                                                    <div className="flex items-center gap-2">
                                                        {icon && <Icons icon={icon} />}
                                                        <RenderCell value={value} type={renderer} risk={risk} fraud={result?.fraud_reason}/>
                                                    </div>
                                                </td>
                                            )
                                        })}
                                        <td className="p-3">
                                            <Link href={`${pathname}/${result.id}`}>
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
                    </div>
                ) : (
                    <div className="text-center">
                        <p className="text-muted-foreground">
                            No {title} found
                        </p>
                    </div>
                ))}
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
        </>
    )
}

export default Results;
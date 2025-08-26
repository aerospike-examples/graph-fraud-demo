import { Badge } from '../ui/badge'
import {   
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger
} from '../ui/tooltip'
import type { Option } from './index'

interface Props {
    type: Option['renderer'],
    value: string | number,
    risk: { 
        level: string,
        color: string 
    },
    fraud?: string
}

const RenderCell = ({ 
    type,
    value,
    risk,
    fraud
}: Props ) => {
    switch(type) {
        case 'small':
            return <span className='text-sm truncate max-w-48' title={value as string}>{value}</span>
        case 'mono':
            return <span className='text-sm font-mono' title={value as string}>{value}</span>
        case 'medium':
            return <span className='font-medium'>{value}</span>
        case 'muted':
            return <span className='text-sm text-muted-foreground'>{value}</span>
        case 'risk':
            return (
                <div className="space-y-1">
                    <Badge variant={risk.color as any} className='text-xs'>
                        <span className='text-nowrap'>{risk.level} {(value as number).toFixed(1)}</span>
                    </Badge>
                </div>
            )
        case 'fraud':
            return (
                <div className="space-y-1">
                {value === 'clean' ? (
                    <Badge variant="default" className="text-xs">CLEAN</Badge>
                ) : (
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger>
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
                                    fraud && <span className="text-xs text-muted-foreground">{fraud}</span>
                                )}
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                )}
                </div>
            )
        default:
            return null
    }
}

export default RenderCell;
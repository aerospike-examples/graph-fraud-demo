'use client'

import Icon, { type IconName } from "./Icon"
import { Badge, type BadgeProps } from "./ui/badge"
import { Color } from "./Stat"

export interface LabelProps {
    className?: string
    title?: string
    subtitle?: string
    icon?: IconName
    color?: Color
    text?: string
    badge?: Omit<BadgeProps, 'children'> & { text: string }
    size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
}

const Label = ({
    className,
    title,
    subtitle,
    icon,
    color = 'foreground',
    text,
    badge,
    size = 'md'
}: LabelProps) => {
    const iconSize = size.includes('xl') ? '5' : '4';
    return (
        <div className="flex flex-col gap-1">
            {title && <p className="text-sm font-medium text-muted-foreground">{title}</p>}
            <div>
                <div className='flex items-center gap-2'>
                    {icon && <Icon className={`h-${iconSize} w-${iconSize} text-${color}`} icon={icon} />}
                    {text && <p className={`text-${size} capitalize ${className}`} title={text}>{text}</p>}
                    {badge && 
                    <Badge variant={badge.variant} className={badge.className}>
                        <span className='text-nowrap'>{badge.text}</span>
                    </Badge>}
                </div>
                {subtitle && <p className="text-sm font-medium text-muted-foreground" title={subtitle}>{subtitle}</p>}
            </div>
        </div>
    )
}

export default Label
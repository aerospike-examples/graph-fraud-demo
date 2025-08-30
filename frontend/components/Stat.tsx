import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Icon, { type IconName } from './Icon';
import Label from './Label';
import { Suspense } from 'react';
export type Color = 'destructive' | 'warning' | 'foreground' | 'green-600' | 'blue-600' | 'yellow-600'

interface Props {
    color?: Color
    stat: string | number | {
        icon: {
            name: IconName
            color: Color
        }
        text: string
    }
    title: string
    subtitle?: string
    icon?: IconName
}

const Stat = ({
    color = 'foreground',
    stat,
    title,
    subtitle, 
    icon
}: Props) => {
    
    return (
        <Card>
            <CardHeader className='p-4 pb-1'>
                <CardTitle>
                    <p className="text-sm font-medium">{title}</p>
                </CardTitle>
            </CardHeader>
            <CardContent className='p-4 pt-1'>
                <div className={`flex items-center justify-between text-${color}`}>
                    <div>
                        <Suspense>
                            {typeof stat === 'object' ? (
                                <Label icon={stat.icon.name} color={stat.icon.color} text={stat.text} size='lg'/>
                            ) : (
                                <p className="text-2xl font-bold">{typeof stat === 'number' ? stat.toLocaleString('en-US') : stat}</p>
                            )}
                        </Suspense>
                        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
                    </div>
                    {icon && <Icon icon={icon} className={`h-8 w-8 text-muted-${color}`} />}
                </div>
            </CardContent>
        </Card>
    )
}

export default Stat
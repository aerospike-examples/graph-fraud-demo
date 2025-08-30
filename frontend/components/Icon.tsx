import dynamic from 'next/dynamic'
import { memo } from 'react';
import type { LucideProps } from 'lucide-react'
import dynamicIconImports from 'lucide-react/dynamicIconImports';

export type IconName = keyof typeof dynamicIconImports

interface Props extends LucideProps {
    icon?: IconName
}

const Icon = memo(({icon, ...props}: Props) => {
    const LucideIcon = dynamic(dynamicIconImports[icon!])
    return (
        <LucideIcon {...props} />
    )
})

export default Icon
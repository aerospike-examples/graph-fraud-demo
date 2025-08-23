import { Mail, User, MapPin, Calendar, CreditCard } from 'lucide-react'
import type { Option } from './index'

const Icons = ({ icon }: { icon: Option['icon'] }) => {
    switch(icon) {
        case 'calendar':
            return <Calendar className="h-4 w-4 text-muted-foreground" />
        case 'card':
            return <CreditCard className="h-4 w-4 text-muted-foreground" />
        case 'mail':
            return <Mail className="h-4 w-4 text-muted-foreground" />
        case 'map':
            return <MapPin className="h-4 w-4 text-muted-foreground" />
        case 'user':
            return <User className="h-4 w-4 text-muted-foreground" />
        default:
            return null
    }
}

export default Icons
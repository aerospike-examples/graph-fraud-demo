import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { Button } from '../ui/button'
import { Calendar, ExternalLink, TrendingDown, TrendingUp, User, Variable } from 'lucide-react'
import { formatCurrency, formatDate } from '@/lib/utils'

export interface Account {
	id: string
	account_type: string
	balance: number
	created_date: string
	user_id: string
	user_name: string
	user_email: string
}

interface Props extends Account {
    variant: 'source' | 'destination'
}

const AccountCard = ({ 
    id,
	account_type,
	balance,
	created_date,
	user_id,
	user_name,
	user_email,
    variant
 }: Props) => {
    const isSource = variant === 'source';
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    {isSource ? (
                        <TrendingDown className="h-5 w-5 text-destructive" />
                    ) : (
                        <TrendingUp className="h-5 w-5 text-green-600" />
                    )}
                    
                    {isSource ? "Source" : "Destination"} Account
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 flex flex-col gap-2">
                <div className="space-y-3">
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Account ID</p>
                        <p className="text-lg font-semibold font-mono">{id}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Account Type</p>
                        <p className="text-lg font-semibold capitalize">{account_type}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Balance</p>
                        <p className={`text-lg font-semibold ${balance < 0 ? 'text-destructive' : 'text-green-600'}`}>
                            {formatCurrency(balance)}
                        </p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Owner</p>
                        <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <p className="text-lg font-semibold">{user_name}</p>
                        </div>
                        <p className="text-sm text-muted-foreground">{user_email}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Created</p>
                        <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-muted-foreground" />
                            <p className="text-sm">{formatDate(created_date)}</p>
                        </div>
                    </div>
                </div>
                <Link href={`/users/${user_id}`}>
                    <Button variant="outline" className="w-full">
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View User Profile
                    </Button>
                </Link>
            </CardContent>
        </Card>
    )
}

export default AccountCard;
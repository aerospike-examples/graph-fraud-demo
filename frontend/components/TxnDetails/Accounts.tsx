import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { Button } from '../ui/button'
import { Calendar, ExternalLink, TrendingDown, TrendingUp, User } from 'lucide-react'
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

const Accounts = ({ 
    source,
    destination
}: { source: Account, destination: Account }) => (
    <div className="grid gap-4 md:grid-cols-2">
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <TrendingDown className="h-5 w-5 text-destructive" />
                    Source Account
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-3">
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Account ID</p>
                        <p className="text-lg font-semibold font-mono">{source.id}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Account Type</p>
                        <p className="text-lg font-semibold capitalize">{source.account_type}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Balance</p>
                        <p className={`text-lg font-semibold ${source.balance < 0 ? 'text-destructive' : 'text-green-600'}`}>
                            {formatCurrency(source.balance)}
                        </p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Owner</p>
                        <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <div>
                                <p className="text-lg font-semibold">{source.user_name}</p>
                                <p className="text-sm text-muted-foreground">{source.user_email}</p>
                            </div>
                        </div>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Created</p>
                        <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-muted-foreground" />
                            <p className="text-sm">{formatDate(source.created_date)}</p>
                        </div>
                    </div>
                </div>
                <Link href={`/users/${source.user_id}`}>
                    <Button variant="outline" className="w-full">
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View User Profile
                    </Button>
                </Link>
            </CardContent>
        </Card>
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-green-600" />
                    Destination Account
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-3">
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Account ID</p>
                        <p className="text-lg font-semibold font-mono">{destination.id}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Account Type</p>
                        <p className="text-lg font-semibold capitalize">{destination.account_type}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Balance</p>
                        <p className={`text-lg font-semibold ${destination.balance < 0 ? 'text-destructive' : 'text-green-600'}`}>
                            {formatCurrency(destination.balance)}
                        </p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Owner</p>
                        <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <div>
                                <p className="text-lg font-semibold">{destination.user_name}</p>
                                <p className="text-sm text-muted-foreground">{destination.user_email}</p>
                            </div>
                        </div>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Created</p>
                        <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-muted-foreground" />
                            <p className="text-sm">{formatDate(destination.created_date)}</p>
                        </div>
                    </div>
                </div>
                <Link href={`/users/${destination.user_id}`}>
                    <Button variant="outline" className="w-full">
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View User Profile
                    </Button>
                </Link>
            </CardContent>
        </Card>
    </div>
)

export default Accounts;
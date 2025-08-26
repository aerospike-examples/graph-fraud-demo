import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Clock, MapPin } from 'lucide-react'
import { formatDateTime } from '@/lib/utils'
import { TransactionDetail } from '@/app/transactions/[id]/page';

const Devices = ({ transaction }: { transaction: TransactionDetail['transaction']}) => (
    <Card>
        <CardHeader>
            <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                Location Information
            </CardTitle>
            <CardDescription>
                Geographic and network location details for this transaction
            </CardDescription>
        </CardHeader>
        <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-4">
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">City</p>
                        <div className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-muted-foreground" />
                            <p className="text-lg font-semibold">{transaction.location_city || 'Unknown'}</p>
                        </div>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Country</p>
                        <p className="text-lg font-semibold">{transaction.location_country || 'Unknown'}</p>
                    </div>
                    {transaction.latitude && transaction.longitude && (
                    <>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Latitude</p>
                        <p className="text-lg font-semibold">{transaction.latitude.toFixed(6)}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Longitude</p>
                        <p className="text-lg font-semibold">{transaction.longitude.toFixed(6)}</p>
                    </div>
                    </>)}
                </div>
                <div className="space-y-4">
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">IP Address</p>
                        <p className="text-lg font-semibold font-mono">{transaction.ip_address || 'Unknown'}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-muted-foreground">Transaction Time</p>
                        <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                            <p className="text-lg font-semibold">{formatDateTime(transaction.timestamp)}</p>
                        </div>
                    </div>
                </div>
            </div>  
            {(!transaction.location_city && !transaction.ip_address) && (
            <div className="text-center py-8 mt-4">
                <MapPin className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No location information available.</p>
                <p className="text-sm text-muted-foreground mt-2">
                    Location data was not captured for this transaction.
                </p>
            </div>)}
        </CardContent>
    </Card>
)

export default Devices;
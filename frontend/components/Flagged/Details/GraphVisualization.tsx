'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
    Network, 
    ZoomIn, 
    ZoomOut, 
    Maximize2, 
    RotateCcw,
    User,
    CreditCard,
    Smartphone,
    Globe,
    AlertTriangle,
    X
} from 'lucide-react'

// Node types
type NodeType = 'account' | 'user' | 'device' | 'ip' | 'transaction'

interface GraphNode {
    id: string
    label: string
    type: NodeType
    x: number
    y: number
    risk?: 'high' | 'medium' | 'low'
    isFlagged?: boolean
    details?: Record<string, string>
}

interface GraphEdge {
    source: string
    target: string
    label?: string
    type?: 'transaction' | 'owns' | 'uses' | 'connected'
}

interface Props {
    accountId: string
}

// Mock graph data - in production this would come from API
const generateMockGraphData = (accountId: string): { nodes: GraphNode[], edges: GraphEdge[] } => {
    const centerX = 400
    const centerY = 300
    
    const nodes: GraphNode[] = [
        // Central flagged account
        { 
            id: accountId, 
            label: 'Marcus Johnson\nACC-78234', 
            type: 'account', 
            x: centerX, 
            y: centerY, 
            risk: 'high', 
            isFlagged: true,
            details: { 'Account': 'ACC-78234', 'Bank': 'Chase', 'Balance': '$12,450' }
        },
        // User
        { 
            id: 'U4521', 
            label: 'Marcus Johnson', 
            type: 'user', 
            x: centerX - 150, 
            y: centerY - 100,
            details: { 'User ID': 'U4521', 'Email': 'marcus@email.com', 'Location': 'New York' }
        },
        // Devices
        { 
            id: 'DEV-001', 
            label: 'iPhone 15 Pro', 
            type: 'device', 
            x: centerX - 200, 
            y: centerY + 50,
            details: { 'Device': 'iPhone 15 Pro', 'OS': 'iOS 17.2', 'Last Seen': 'Today' }
        },
        { 
            id: 'DEV-002', 
            label: 'MacBook Pro', 
            type: 'device', 
            x: centerX - 180, 
            y: centerY + 150,
            details: { 'Device': 'MacBook Pro', 'OS': 'macOS 14.2', 'Last Seen': 'Today' }
        },
        { 
            id: 'DEV-003', 
            label: 'Android Phone\n(Suspicious)', 
            type: 'device', 
            x: centerX - 100, 
            y: centerY + 200, 
            risk: 'high',
            details: { 'Device': 'Android Phone', 'OS': 'Android 14', 'Location': 'Miami, FL', 'Status': 'New Device' }
        },
        // IP Addresses
        { 
            id: 'IP-001', 
            label: '192.168.1.xxx\nNew York', 
            type: 'ip', 
            x: centerX - 300, 
            y: centerY,
            details: { 'IP': '192.168.1.xxx', 'Location': 'New York, NY', 'ISP': 'Verizon' }
        },
        { 
            id: 'IP-002', 
            label: '45.33.xxx.xxx\nMiami (VPN)', 
            type: 'ip', 
            x: centerX - 280, 
            y: centerY + 120, 
            risk: 'medium',
            details: { 'IP': '45.33.xxx.xxx', 'Location': 'Miami, FL', 'Type': 'VPN/Proxy', 'Risk': 'Medium' }
        },
        // Connected accounts (1st hop)
        { 
            id: 'ACC-91456', 
            label: 'Elena Rodriguez\nACC-91456', 
            type: 'account', 
            x: centerX + 180, 
            y: centerY - 80, 
            risk: 'high', 
            isFlagged: true,
            details: { 'Account': 'ACC-91456', 'Bank': 'BOA', 'Status': 'Flagged', 'Connection': 'Received $12,300' }
        },
        { 
            id: 'ACC-34521', 
            label: 'Offshore LLC\nACC-34521', 
            type: 'account', 
            x: centerX + 200, 
            y: centerY + 40, 
            risk: 'high',
            details: { 'Account': 'ACC-34521', 'Type': 'Business', 'Country': 'Cayman Islands', 'Connection': 'Received $8,500' }
        },
        { 
            id: 'ACC-56789', 
            label: 'Crypto Exchange\nACC-56789', 
            type: 'account', 
            x: centerX + 150, 
            y: centerY + 150, 
            risk: 'medium',
            details: { 'Account': 'ACC-56789', 'Type': 'Exchange', 'Platform': 'Unknown', 'Connection': 'Received $8,490' }
        },
        // 2nd hop connections
        { 
            id: 'ACC-77123', 
            label: 'Shell Corp A\nACC-77123', 
            type: 'account', 
            x: centerX + 350, 
            y: centerY - 120, 
            risk: 'high',
            details: { 'Account': 'ACC-77123', 'Type': 'Business', 'Status': 'Suspicious', 'Hop': '2nd degree' }
        },
        { 
            id: 'ACC-88234', 
            label: 'John Doe\nACC-88234', 
            type: 'account', 
            x: centerX + 380, 
            y: centerY, 
            risk: 'medium',
            details: { 'Account': 'ACC-88234', 'Bank': 'Wells Fargo', 'Hop': '2nd degree' }
        },
        { 
            id: 'ACC-99345', 
            label: 'Trading LLC\nACC-99345', 
            type: 'account', 
            x: centerX + 320, 
            y: centerY + 100, 
            risk: 'low',
            details: { 'Account': 'ACC-99345', 'Type': 'Business', 'Hop': '2nd degree' }
        },
        // Shared device connection (suspicious)
        { 
            id: 'DEV-SHARED', 
            label: 'Shared Device\n(3 accounts)', 
            type: 'device', 
            x: centerX + 100, 
            y: centerY - 180, 
            risk: 'high',
            details: { 'Device': 'Windows PC', 'Accounts': '3 accounts linked', 'Risk': 'Device sharing detected' }
        },
    ]
    
    const edges: GraphEdge[] = [
        // User owns account
        { source: 'U4521', target: accountId, type: 'owns', label: 'owns' },
        // Devices
        { source: accountId, target: 'DEV-001', type: 'uses', label: 'uses' },
        { source: accountId, target: 'DEV-002', type: 'uses', label: 'uses' },
        { source: accountId, target: 'DEV-003', type: 'uses', label: 'uses' },
        // IPs
        { source: 'DEV-001', target: 'IP-001', type: 'connected', label: 'from' },
        { source: 'DEV-002', target: 'IP-001', type: 'connected', label: 'from' },
        { source: 'DEV-003', target: 'IP-002', type: 'connected', label: 'from' },
        // Transactions (1st hop)
        { source: accountId, target: 'ACC-91456', type: 'transaction', label: '$12,300' },
        { source: accountId, target: 'ACC-34521', type: 'transaction', label: '$8,500' },
        { source: accountId, target: 'ACC-56789', type: 'transaction', label: '$8,490' },
        // 2nd hop transactions
        { source: 'ACC-91456', target: 'ACC-77123', type: 'transaction', label: '$10,000' },
        { source: 'ACC-34521', target: 'ACC-88234', type: 'transaction', label: '$5,000' },
        { source: 'ACC-56789', target: 'ACC-99345', type: 'transaction', label: '$3,200' },
        // Shared device
        { source: 'DEV-SHARED', target: accountId, type: 'uses' },
        { source: 'DEV-SHARED', target: 'ACC-91456', type: 'uses' },
    ]
    
    return { nodes, edges }
}

const nodeColors: Record<NodeType, { bg: string, border: string, icon: string }> = {
    account: { bg: '#3b82f6', border: '#1d4ed8', icon: '#ffffff' },
    user: { bg: '#8b5cf6', border: '#6d28d9', icon: '#ffffff' },
    device: { bg: '#06b6d4', border: '#0891b2', icon: '#ffffff' },
    ip: { bg: '#64748b', border: '#475569', icon: '#ffffff' },
    transaction: { bg: '#22c55e', border: '#16a34a', icon: '#ffffff' },
}

const riskColors = {
    high: { bg: '#ef4444', border: '#dc2626' },
    medium: { bg: '#f59e0b', border: '#d97706' },
    low: { bg: '#22c55e', border: '#16a34a' },
}

const GraphVisualization = ({ accountId }: Props) => {
    const svgRef = useRef<SVGSVGElement>(null)
    const [nodes, setNodes] = useState<GraphNode[]>([])
    const [edges, setEdges] = useState<GraphEdge[]>([])
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
    const [draggedNode, setDraggedNode] = useState<string | null>(null)
    const [zoom, setZoom] = useState(1)
    const [pan, setPan] = useState({ x: 0, y: 0 })
    const [isPanning, setIsPanning] = useState(false)
    const [panStart, setPanStart] = useState({ x: 0, y: 0 })

    useEffect(() => {
        const data = generateMockGraphData(accountId)
        setNodes(data.nodes)
        setEdges(data.edges)
    }, [accountId])

    const handleMouseDown = useCallback((e: React.MouseEvent, nodeId?: string) => {
        if (nodeId) {
            setDraggedNode(nodeId)
        } else {
            setIsPanning(true)
            setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
        }
    }, [pan])

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (draggedNode) {
            const svg = svgRef.current
            if (!svg) return
            
            const rect = svg.getBoundingClientRect()
            const x = (e.clientX - rect.left - pan.x) / zoom
            const y = (e.clientY - rect.top - pan.y) / zoom
            
            setNodes(prev => prev.map(node => 
                node.id === draggedNode ? { ...node, x, y } : node
            ))
        } else if (isPanning) {
            setPan({
                x: e.clientX - panStart.x,
                y: e.clientY - panStart.y
            })
        }
    }, [draggedNode, isPanning, panStart, pan, zoom])

    const handleMouseUp = useCallback(() => {
        setDraggedNode(null)
        setIsPanning(false)
    }, [])

    const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.2, 2))
    const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.2, 0.5))
    const handleReset = () => {
        setZoom(1)
        setPan({ x: 0, y: 0 })
        const data = generateMockGraphData(accountId)
        setNodes(data.nodes)
        setEdges(data.edges)
    }

    const getNodePosition = (nodeId: string) => {
        const node = nodes.find(n => n.id === nodeId)
        return node ? { x: node.x, y: node.y } : { x: 0, y: 0 }
    }

    const getNodeIcon = (type: NodeType) => {
        switch (type) {
            case 'account': return CreditCard
            case 'user': return User
            case 'device': return Smartphone
            case 'ip': return Globe
            default: return CreditCard
        }
    }

    const getEdgeColor = (type?: string) => {
        switch (type) {
            case 'transaction': return '#ef4444'
            case 'owns': return '#8b5cf6'
            case 'uses': return '#06b6d4'
            default: return '#94a3b8'
        }
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Network className="h-5 w-5" />
                            Connection Graph
                        </CardTitle>
                        <CardDescription>
                            Interactive visualization of account connections (2 hops)
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="icon" onClick={handleZoomOut}>
                            <ZoomOut className="h-4 w-4" />
                        </Button>
                        <span className="text-sm text-muted-foreground w-12 text-center">
                            {Math.round(zoom * 100)}%
                        </span>
                        <Button variant="outline" size="icon" onClick={handleZoomIn}>
                            <ZoomIn className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="icon" onClick={handleReset}>
                            <RotateCcw className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="relative">
                    {/* Legend */}
                    <div className="absolute top-2 left-2 z-10 bg-background/95 backdrop-blur border rounded-lg p-3 text-xs space-y-2">
                        <p className="font-medium text-sm">Legend</p>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: nodeColors.account.bg }} />
                            <span>Account</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: nodeColors.user.bg }} />
                            <span>User</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: nodeColors.device.bg }} />
                            <span>Device</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: nodeColors.ip.bg }} />
                            <span>IP Address</span>
                        </div>
                        <div className="border-t pt-2 mt-2">
                            <div className="flex items-center gap-2">
                                <div className="w-4 h-4 rounded border-2 border-red-500 bg-red-500/20" />
                                <span>High Risk</span>
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                                <div className="w-4 h-4 rounded border-2 border-amber-500 bg-amber-500/20" />
                                <span>Medium Risk</span>
                            </div>
                        </div>
                        <div className="border-t pt-2 mt-2">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-0.5 bg-red-500" />
                                <span>Transaction</span>
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                                <div className="w-8 h-0.5 bg-cyan-500" />
                                <span>Uses</span>
                            </div>
                        </div>
                    </div>

                    {/* Selected Node Details */}
                    {selectedNode && (
                        <div className="absolute top-2 right-2 z-10 bg-background/95 backdrop-blur border rounded-lg p-4 w-64">
                            <div className="flex items-center justify-between mb-3">
                                <h4 className="font-semibold flex items-center gap-2">
                                    {selectedNode.isFlagged && <AlertTriangle className="h-4 w-4 text-red-500" />}
                                    {selectedNode.type.charAt(0).toUpperCase() + selectedNode.type.slice(1)}
                                </h4>
                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setSelectedNode(null)}>
                                    <X className="h-4 w-4" />
                                </Button>
                            </div>
                            <div className="space-y-2 text-sm">
                                {selectedNode.details && Object.entries(selectedNode.details).map(([key, value]) => (
                                    <div key={key} className="flex justify-between">
                                        <span className="text-muted-foreground">{key}</span>
                                        <span className="font-medium">{value}</span>
                                    </div>
                                ))}
                                {selectedNode.risk && (
                                    <div className="flex justify-between pt-2 border-t">
                                        <span className="text-muted-foreground">Risk Level</span>
                                        <span className={`font-medium ${
                                            selectedNode.risk === 'high' ? 'text-red-500' :
                                            selectedNode.risk === 'medium' ? 'text-amber-500' : 'text-green-500'
                                        }`}>
                                            {selectedNode.risk.toUpperCase()}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* SVG Graph */}
                    <svg
                        ref={svgRef}
                        width="100%"
                        height="500"
                        className="border rounded-lg bg-muted/20 cursor-grab active:cursor-grabbing"
                        onMouseDown={(e) => handleMouseDown(e)}
                        onMouseMove={handleMouseMove}
                        onMouseUp={handleMouseUp}
                        onMouseLeave={handleMouseUp}
                    >
                        <defs>
                            {/* Arrow marker for edges */}
                            <marker
                                id="arrowhead"
                                markerWidth="10"
                                markerHeight="7"
                                refX="9"
                                refY="3.5"
                                orient="auto"
                            >
                                <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" />
                            </marker>
                            <marker
                                id="arrowhead-red"
                                markerWidth="10"
                                markerHeight="7"
                                refX="9"
                                refY="3.5"
                                orient="auto"
                            >
                                <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444" />
                            </marker>
                            {/* Glow filter for flagged nodes */}
                            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                                <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                                <feMerge>
                                    <feMergeNode in="coloredBlur"/>
                                    <feMergeNode in="SourceGraphic"/>
                                </feMerge>
                            </filter>
                        </defs>
                        
                        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                            {/* Edges */}
                            {edges.map((edge, idx) => {
                                const source = getNodePosition(edge.source)
                                const target = getNodePosition(edge.target)
                                const midX = (source.x + target.x) / 2
                                const midY = (source.y + target.y) / 2
                                const color = getEdgeColor(edge.type)
                                
                                return (
                                    <g key={idx}>
                                        <line
                                            x1={source.x}
                                            y1={source.y}
                                            x2={target.x}
                                            y2={target.y}
                                            stroke={color}
                                            strokeWidth={edge.type === 'transaction' ? 2.5 : 1.5}
                                            strokeDasharray={edge.type === 'connected' ? '5,5' : undefined}
                                            opacity={0.7}
                                            markerEnd={edge.type === 'transaction' ? 'url(#arrowhead-red)' : 'url(#arrowhead)'}
                                        />
                                        {edge.label && (
                                            <text
                                                x={midX}
                                                y={midY - 5}
                                                textAnchor="middle"
                                                className="text-[10px] fill-muted-foreground font-medium"
                                            >
                                                {edge.label}
                                            </text>
                                        )}
                                    </g>
                                )
                            })}
                            
                            {/* Nodes */}
                            {nodes.map((node) => {
                                const colors = node.risk ? riskColors[node.risk] : nodeColors[node.type]
                                const Icon = getNodeIcon(node.type)
                                const isSelected = selectedNode?.id === node.id
                                
                                return (
                                    <g
                                        key={node.id}
                                        transform={`translate(${node.x}, ${node.y})`}
                                        onMouseDown={(e) => {
                                            e.stopPropagation()
                                            handleMouseDown(e, node.id)
                                        }}
                                        onClick={() => setSelectedNode(node)}
                                        className="cursor-pointer"
                                        filter={node.isFlagged ? 'url(#glow)' : undefined}
                                    >
                                        {/* Node circle */}
                                        <circle
                                            r={node.isFlagged ? 28 : 24}
                                            fill={node.risk ? colors.bg : nodeColors[node.type].bg}
                                            stroke={isSelected ? '#ffffff' : (node.risk ? colors.border : nodeColors[node.type].border)}
                                            strokeWidth={isSelected ? 4 : node.isFlagged ? 3 : 2}
                                            className="transition-all duration-150"
                                        />
                                        
                                        {/* Flagged indicator ring */}
                                        {node.isFlagged && (
                                            <circle
                                                r={34}
                                                fill="none"
                                                stroke="#ef4444"
                                                strokeWidth={2}
                                                strokeDasharray="4,4"
                                                className="animate-spin"
                                                style={{ animationDuration: '10s' }}
                                            />
                                        )}
                                        
                                        {/* Icon */}
                                        <foreignObject x="-12" y="-12" width="24" height="24">
                                            <div className="flex items-center justify-center w-full h-full">
                                                <Icon className="h-5 w-5 text-white" />
                                            </div>
                                        </foreignObject>
                                        
                                        {/* Label */}
                                        <text
                                            y={node.isFlagged ? 48 : 42}
                                            textAnchor="middle"
                                            className="text-[11px] fill-foreground font-medium"
                                        >
                                            {node.label.split('\n').map((line, i) => (
                                                <tspan key={i} x="0" dy={i === 0 ? 0 : 14}>
                                                    {line}
                                                </tspan>
                                            ))}
                                        </text>
                                        
                                        {/* Risk indicator */}
                                        {node.risk && !node.isFlagged && (
                                            <circle
                                                cx={18}
                                                cy={-18}
                                                r={8}
                                                fill={riskColors[node.risk].bg}
                                                stroke="#ffffff"
                                                strokeWidth={2}
                                            />
                                        )}
                                    </g>
                                )
                            })}
                        </g>
                    </svg>

                    {/* Instructions */}
                    <div className="mt-3 flex items-center justify-center gap-4 text-xs text-muted-foreground">
                        <span>🖱️ Drag nodes to rearrange</span>
                        <span>•</span>
                        <span>👆 Click node for details</span>
                        <span>•</span>
                        <span>✋ Drag canvas to pan</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}

export default GraphVisualization

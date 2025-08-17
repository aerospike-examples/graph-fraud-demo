'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Search, User, Mail, MapPin, Calendar, Shield, ChevronLeft, ChevronRight, Loader2, X, CreditCard, DollarSign, Clock, ArrowRight, Eye } from 'lucide-react'
import { api } from '@/lib/api'
import Link from 'next/link'

interface User {
  id: string
  name: string
  email: string
  age: number
  signup_date: string
  location: string
  risk_score: number
  is_flagged: boolean
}

interface UserSummary {
  user: User
  accounts: Array<{
    id: string
    account_type: string
    balance: number
    created_date: string
  }>
  recent_transactions: Array<{
    id: string
    amount: number
    currency: string
    timestamp: string
    status: string
    fraud_score: number
  }>
  total_transactions: number
  total_amount_sent: number
  total_amount_received: number
  fraud_risk_level: string
  connected_users: string[]
}

interface PaginatedUsers {
  users: User[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export default function UsersPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalUsers, setTotalUsers] = useState(0)
  const [pageSize] = useState(20) // Increased page size for list view
  const [sortBy, setSortBy] = useState<'name' | 'risk_score' | 'signup_date'>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  // Load all users on component mount
  useEffect(() => {
    loadAllUsers()
  }, [currentPage, sortBy, sortOrder])

  const loadAllUsers = async () => {
    setLoading(true)
    try {
      const response = await api.get(`/users?page=${currentPage}&page_size=${pageSize}`)
      const data: PaginatedUsers = response.data
      let filteredUsers = data.users || []
      
      // Apply sorting
      filteredUsers.sort((a, b) => {
        let aValue: any = a[sortBy]
        let bValue: any = b[sortBy]
        
        if (sortBy === 'name') {
          aValue = aValue.toLowerCase()
          bValue = bValue.toLowerCase()
        }
        
        if (sortOrder === 'asc') {
          return aValue > bValue ? 1 : -1
        } else {
          return aValue < bValue ? 1 : -1
        }
      })
      
      setUsers(filteredUsers)
      setTotalPages(data.total_pages || 1)
      setTotalUsers(data.total || 0)
    } catch (error) {
      console.error('Failed to load users:', error)
      setUsers([])
    } finally {
      setLoading(false)
    }
  }

  const searchUsers = async () => {
    if (!searchQuery.trim()) {
      setCurrentPage(1)
      loadAllUsers()
      return
    }
    
    setSearchLoading(true)
    try {
      const response = await api.get(`/users/search?query=${searchQuery}&page=${currentPage}&page_size=${pageSize}`)
      const data: PaginatedUsers = response.data
      setUsers(data.users || [])
      setTotalPages(data.total_pages || 1)
      setTotalUsers(data.total || 0)
    } catch (error) {
      console.error('Failed to search users:', error)
      setUsers([])
    } finally {
      setSearchLoading(false)
    }
  }

  const handleSearch = () => {
    setCurrentPage(1)
    searchUsers()
  }

  const handleDirectUserLookup = () => {
    if (!searchQuery.trim()) return
    
    const userId = searchQuery.trim()
    // Navigate directly to the user profile
    window.location.href = `/users/${userId}`
  }

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage)
  }

  const getRiskLevel = (score: number) => {
    if (score < 25) return { level: 'Low', color: 'success' }
    if (score < 50) return { level: 'Medium', color: 'warning' }
    if (score < 75) return { level: 'High', color: 'destructive' }
    return { level: 'Critical', color: 'destructive' }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const handleSort = (field: 'name' | 'risk_score' | 'signup_date') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  const getSortIcon = (field: 'name' | 'risk_score' | 'signup_date') => {
    if (sortBy !== field) return null
    return sortOrder === 'asc' ? '↑' : '↓'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">User Explorer</h1>
        <p className="text-muted-foreground">
          Browse and search user profiles with detailed information
        </p>
      </div>

      {/* Quick User Lookup */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Quick User Lookup
          </CardTitle>
          <CardDescription>
            Enter a user ID to directly view their profile
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Enter user ID (e.g., U0006)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleDirectUserLookup()}
              className="flex-1"
            />
            <Button onClick={handleDirectUserLookup} disabled={searchLoading || !searchQuery.trim()}>
              {searchLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4 mr-2" />
              )}
              {searchLoading ? 'Loading...' : 'View Profile'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Users</p>
                <p className="text-2xl font-bold">{totalUsers}</p>
              </div>
              <User className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">High Risk</p>
                <p className="text-2xl font-bold text-destructive">
                  {users.filter(u => u.risk_score >= 70).length}
                </p>
              </div>
              <Shield className="h-8 w-8 text-destructive" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Medium Risk</p>
                <p className="text-2xl font-bold text-warning">
                  {users.filter(u => u.risk_score >= 25 && u.risk_score < 70).length}
                </p>
              </div>
              <Shield className="h-8 w-8 text-warning" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Low Risk</p>
                <p className="text-2xl font-bold text-green-600">
                  {users.filter(u => u.risk_score < 25).length}
                </p>
              </div>
              <Shield className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Users List */}
      {loading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="flex items-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span>Loading users...</span>
            </div>
          </CardContent>
        </Card>
      ) : users.length > 0 ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Users List</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-3 font-medium cursor-pointer hover:bg-muted/50" onClick={() => handleSort('name')}>
                        Name {getSortIcon('name')}
                      </th>
                      <th className="text-left p-3 font-medium">ID</th>
                      <th className="text-left p-3 font-medium">Email</th>
                      <th className="text-left p-3 font-medium">Location</th>
                      <th className="text-left p-3 font-medium">Age</th>
                      <th className="text-left p-3 font-medium cursor-pointer hover:bg-muted/50" onClick={() => handleSort('risk_score')}>
                        Risk Score {getSortIcon('risk_score')}
                      </th>
                      <th className="text-left p-3 font-medium cursor-pointer hover:bg-muted/50" onClick={() => handleSort('signup_date')}>
                        Signup Date {getSortIcon('signup_date')}
                      </th>
                      <th className="text-left p-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => {
                      const risk = getRiskLevel(user.risk_score)
                      return (
                        <tr key={user.id} className="border-b hover:bg-muted/30">
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <User className="h-4 w-4 text-muted-foreground" />
                              <span className="font-medium">{user.name}</span>
                            </div>
                          </td>
                          <td className="p-3 text-sm text-muted-foreground">{user.id}</td>
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <Mail className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm">{user.email}</span>
                            </div>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <MapPin className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm">{user.location}</span>
                            </div>
                          </td>
                          <td className="p-3 text-sm">{user.age}</td>
                          <td className="p-3">
                            <Badge variant={risk.color as any} className="text-xs">
                              {risk.level} ({user.risk_score.toFixed(1)})
                            </Badge>
                          </td>
                          <td className="p-3 text-sm text-muted-foreground">
                            <div className="flex items-center gap-2">
                              <Calendar className="h-4 w-4" />
                              {formatDate(user.signup_date)}
                            </div>
                          </td>
                          <td className="p-3">
                            <Link href={`/users/${user.id}`}>
                              <Button variant="outline" size="sm" className="flex items-center gap-2">
                                <Eye className="h-4 w-4" />
                                View Details
                              </Button>
                            </Link>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Pagination */}
          {totalPages > 1 && (
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalUsers)} of {totalUsers} users
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <div className="flex items-center gap-1">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum
                        if (totalPages <= 5) {
                          pageNum = i + 1
                        } else if (currentPage <= 3) {
                          pageNum = i + 1
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i
                        } else {
                          pageNum = currentPage - 2 + i
                        }
                        
                        return (
                          <Button
                            key={pageNum}
                            variant={currentPage === pageNum ? "default" : "outline"}
                            size="sm"
                            onClick={() => handlePageChange(pageNum)}
                            className="w-8 h-8 p-0"
                          >
                            {pageNum}
                          </Button>
                        )
                      })}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-center">
              <User className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">
                {searchQuery ? 'No users found matching your search' : 'No users available'}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 
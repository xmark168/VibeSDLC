import { createFileRoute, Link } from "@tanstack/react-router"
import { requireRole } from "@/utils/auth"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Users, Server, Settings, Activity } from "lucide-react"

export const Route = createFileRoute("/admin/")({
  beforeLoad: async () => {
    await requireRole('admin')
  },
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to the admin panel. Manage and monitor the system from here.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Link to="/admin/agents">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Server className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg">Agent Management</CardTitle>
                  <CardDescription>
                    Monitor and manage agent pools, health, and executions
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• View and manage agent pools</li>
                <li>• Monitor agent health status</li>
                <li>• Track execution metrics</li>
                <li>• View system alerts</li>
              </ul>
            </CardContent>
          </Card>
        </Link>

        <Card className="opacity-50">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-muted rounded-lg">
                <Users className="w-6 h-6 text-muted-foreground" />
              </div>
              <div>
                <CardTitle className="text-lg">User Management</CardTitle>
                <CardDescription>
                  Manage users, roles, and permissions
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Coming soon...</p>
          </CardContent>
        </Card>

        <Card className="opacity-50">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-muted rounded-lg">
                <Activity className="w-6 h-6 text-muted-foreground" />
              </div>
              <div>
                <CardTitle className="text-lg">System Metrics</CardTitle>
                <CardDescription>
                  View detailed system performance metrics
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Coming soon...</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

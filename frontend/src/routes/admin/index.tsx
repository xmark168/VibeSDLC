import { createFileRoute, Link } from "@tanstack/react-router"
import { CreditCard, Layers, Server, UserCircle, Users } from "lucide-react"
import { AdminLayout } from "@/components/admin/AdminLayout"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { requireRole } from "@/utils/auth"

export const Route = createFileRoute("/admin/")({
  beforeLoad: async () => {
    await requireRole("admin")
  },
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <AdminLayout>
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

          <Link to="/admin/plans">
            <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <CreditCard className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Plan Management</CardTitle>
                    <CardDescription>
                      Manage subscription plans and pricing
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Create and edit pricing plans</li>
                  <li>• Set credit allocations</li>
                  <li>• Configure plan features</li>
                  <li>• View subscription analytics</li>
                </ul>
              </CardContent>
            </Card>
          </Link>

          <Link to="/admin/users">
            <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <Users className="w-6 h-6 text-primary" />
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
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Create and manage user accounts</li>
                  <li>• Assign roles (Admin/User)</li>
                  <li>• Lock/unlock accounts</li>
                  <li>• Bulk user operations</li>
                </ul>
              </CardContent>
            </Card>
          </Link>

          <Link to="/admin/stacks">
            <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <Layers className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Stack Management</CardTitle>
                    <CardDescription>
                      Manage technology stacks and skills
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Create and configure tech stacks</li>
                  <li>• Define stack configurations</li>
                  <li>• Manage skill files with Monaco editor</li>
                  <li>• Organize stack templates</li>
                </ul>
              </CardContent>
            </Card>
          </Link>

          <Link to="/admin/personas">
            <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <UserCircle className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">
                      Persona Management
                    </CardTitle>
                    <CardDescription>
                      Manage agent personality templates
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Create and edit personas</li>
                  <li>• Configure personality traits</li>
                  <li>• Set communication styles</li>
                  <li>• Track persona usage stats</li>
                </ul>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>
    </AdminLayout>
  )
}

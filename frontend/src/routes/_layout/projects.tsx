import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState, useMemo } from 'react'

import { isLoggedIn } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import useAuth from '@/hooks/useAuth'
import { useProjects } from '@/queries/projects'
import CreateProjectDialog from '@/components/projects/CreateProjectDialog'
import type { Project } from '@/types/project'
import { number } from 'framer-motion'

// Temporary UI type until backend Projects API is available
// Use backend types. Status/tags/members are not in backend yet.

export const Route = createFileRoute('/_layout/projects')({
  beforeLoad: () => {
    if (!isLoggedIn()) {
      throw redirect({ to: '/login' })
    }
  },
  component: ProjectsPage,
})

function ProjectsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<'all'>('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [openCreate, setOpenCreate] = useState(false)

  const { logout } = useAuth()

  const { data, isLoading, isError, refetch } = useProjects({ search, page, pageSize })

  const totalPages = useMemo(() => {
    const total = data?.count ?? 0
    return Math.max(1, Math.ceil(total / pageSize))
  }, [data?.count, pageSize])

  return (
    <div className="max-w-[1200px] mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Projects</h1>
          <p className="text-sm text-muted-foreground">Manage and track all your projects.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={logout}>Logout</Button>
          <Button onClick={() => setOpenCreate(true)}>New Project</Button>
        </div>
      </div>

      <div className="flex gap-3 mb-4">
        <Input
          placeholder="Search projects..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        {/* Status filter removed until backend supports it */}
      </div>

      {isError && (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Failed to load projects</AlertTitle>
          <AlertDescription>
            Please try again. <Button variant="outline" size="sm" className="ml-2" onClick={() => refetch()}>Retry</Button>
          </AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : (
        <ProjectsTable
          items={data?.data ?? []}
          onCreate={() => setOpenCreate(true)}
          onOpenProject={(id) => navigate({ to: '/workspace/$workspaceId', params: { workspaceId: id } })}
        />
      )}

      <div className="mt-4 flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Page {page} of {totalPages}
        </div>
        <div className="flex gap-2 items-center">
          <Button variant="outline" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Prev</Button>
          <Button variant="outline" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>Next</Button>
          <Select value={String(pageSize)} onValueChange={(v) => { setPageSize(Number(v)); setPage(1) }}>
            <SelectTrigger className="w-[100px]">
              <SelectValue placeholder="Page size" />
            </SelectTrigger>
            <SelectContent>
              {[10, 20, 50].map((s) => (
                <SelectItem key={s} value={String(s)}>{s} / page</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <CreateProjectDialog open={openCreate} onOpenChange={setOpenCreate} />
    </div>
  )
}

function ProjectsTable({ items, onCreate, onOpenProject }: { items: Project[]; onCreate: () => void; onOpenProject: (id: string) => void }) {
  if (items.length === 0) {
    return (
      <div className="border rounded-md p-10 text-center">
        <p className="text-sm text-muted-foreground">No projects found.</p>
        <Button className="mt-3" onClick={onCreate}>Create your first project</Button>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[80px]">STT</TableHead>
          <TableHead>Tên</TableHead>
          <TableHead>Ngày tạo</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((p, idx) => (
          <TableRow key={p.id} className="cursor-pointer" onClick={() => onOpenProject(p.id)}>
            <TableCell className="text-muted-foreground">{idx + 1}</TableCell>
            <TableCell className="font-medium">{p.name}</TableCell>
            <TableCell>{(p.created_at ?? p.updated_at) ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(p.created_at ?? p.updated_at!)) : '-'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

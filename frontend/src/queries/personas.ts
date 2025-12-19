import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { personasApi } from "@/apis/personas"
import type { PersonaCreate, PersonaUpdate } from "@/types/persona"
import { toast } from "@/lib/toast"

export const personaQueryKeys = {
  all: ["personas"] as const,
  lists: () => [...personaQueryKeys.all, "list"] as const,
  list: (filters?: { role_type?: string; is_active?: boolean }) =>
    [...personaQueryKeys.lists(), filters] as const,
  byRole: (roleType: string) => [...personaQueryKeys.all, "by-role", roleType] as const,
  withStats: (roleType?: string) => [...personaQueryKeys.all, "with-stats", roleType] as const,
  detail: (id: string) => [...personaQueryKeys.all, "detail", id] as const,
}

export function usePersonas(params?: {
  role_type?: string
  is_active?: boolean
  skip?: number
  limit?: number
}) {
  return useQuery({
    queryKey: personaQueryKeys.list(params),
    queryFn: () => personasApi.listPersonas(params),
    staleTime: 60000, // 1 minute
  })
}

export function usePersonasByRole(roleType: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: personaQueryKeys.byRole(roleType),
    queryFn: () => personasApi.getPersonasByRole(roleType),
    enabled: (options?.enabled ?? true) && !!roleType,
    staleTime: 60000,
  })
}

export function usePersonasWithStats(roleType?: string) {
  return useQuery({
    queryKey: personaQueryKeys.withStats(roleType),
    queryFn: () => personasApi.listPersonasWithStats(roleType),
    staleTime: 30000, // 30 seconds for stats
  })
}

export function usePersona(personaId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: personaQueryKeys.detail(personaId),
    queryFn: () => personasApi.getPersona(personaId),
    enabled: (options?.enabled ?? true) && !!personaId,
    staleTime: 60000,
  })
}

export function useCreatePersona() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PersonaCreate) => personasApi.createPersona(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.withStats() })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.byRole(data.role_type) })
      toast.success(`Persona "${data.name}" created successfully`)
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to create persona")
    },
  })
}

export function useUpdatePersona() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ personaId, data }: { personaId: string; data: PersonaUpdate }) =>
      personasApi.updatePersona(personaId, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.withStats() })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.byRole(data.role_type) })
      toast.success(`Persona "${data.name}" updated successfully`)
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to update persona")
    },
  })
}

export function useDeletePersona() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ personaId, hardDelete }: { personaId: string; hardDelete?: boolean }) =>
      personasApi.deletePersona(personaId, hardDelete),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.withStats() })
      toast.success("Persona deleted successfully")
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to delete persona")
    },
  })
}

export function useActivatePersona() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (personaId: string) => personasApi.activatePersona(personaId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.withStats() })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: personaQueryKeys.byRole(data.role_type) })
      toast.success(`Persona "${data.name}" activated`)
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to activate persona")
    },
  })
}

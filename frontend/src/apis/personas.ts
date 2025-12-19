import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type { PersonaTemplate, PersonaCreate, PersonaUpdate, PersonaWithUsageStats } from "@/types/persona"

export const personasApi = {
  listPersonas: async (params?: {
    role_type?: string
    is_active?: boolean
    skip?: number
    limit?: number
  }): Promise<PersonaTemplate[]> => {
    return __request<PersonaTemplate[]>(OpenAPI, {
      method: "GET",
      url: "/api/v1/personas",
      query: params,
    })
  },

  getPersonasByRole: async (roleType: string, isActive: boolean = true): Promise<PersonaTemplate[]> => {
    return __request<PersonaTemplate[]>(OpenAPI, {
      method: "GET",
      url: `/api/v1/personas/by-role/${roleType}`,
      query: { is_active: isActive },
    })
  },

  listPersonasWithStats: async (roleType?: string): Promise<PersonaWithUsageStats[]> => {
    return __request<PersonaWithUsageStats[]>(OpenAPI, {
      method: "GET",
      url: "/api/v1/personas/with-stats",
      query: roleType ? { role_type: roleType } : undefined,
    })
  },

  getPersona: async (personaId: string): Promise<PersonaTemplate> => {
    return __request<PersonaTemplate>(OpenAPI, {
      method: "GET",
      url: `/api/v1/personas/${personaId}`,
    })
  },

  createPersona: async (data: PersonaCreate): Promise<PersonaTemplate> => {
    return __request<PersonaTemplate>(OpenAPI, {
      method: "POST",
      url: "/api/v1/personas",
      body: data,
    })
  },

  updatePersona: async (personaId: string, data: PersonaUpdate): Promise<PersonaTemplate> => {
    return __request<PersonaTemplate>(OpenAPI, {
      method: "PUT",
      url: `/api/v1/personas/${personaId}`,
      body: data,
    })
  },

  deletePersona: async (personaId: string, hardDelete: boolean = false): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/personas/${personaId}`,
      query: { hard_delete: hardDelete },
    })
  },

  activatePersona: async (personaId: string): Promise<PersonaTemplate> => {
    return __request<PersonaTemplate>(OpenAPI, {
      method: "POST",
      url: `/api/v1/personas/${personaId}/activate`,
    })
  },
}

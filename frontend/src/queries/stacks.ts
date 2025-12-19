import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "@/lib/toast"
import { parseApiError } from "@/lib/api-error"
import { stacksApi } from "@/apis/stacks"
import type { TechStackCreate, TechStackUpdate } from "@/types/stack"

export const stackQueryKeys = {
  all: ["stacks"] as const,
  lists: () => [...stackQueryKeys.all, "list"] as const,
  list: (params?: Record<string, unknown>) => [...stackQueryKeys.lists(), params] as const,
  details: () => [...stackQueryKeys.all, "detail"] as const,
  detail: (id: string) => [...stackQueryKeys.details(), id] as const,
  byCode: (code: string) => [...stackQueryKeys.all, "code", code] as const,
  availableSkills: () => [...stackQueryKeys.all, "available-skills"] as const,
  skillTree: (code: string) => [...stackQueryKeys.all, "skill-tree", code] as const,
  skillFile: (code: string, path: string) => [...stackQueryKeys.all, "skill-file", code, path] as const,
  boilerplateTree: (code: string) => [...stackQueryKeys.all, "boilerplate-tree", code] as const,
  boilerplateFile: (code: string, path: string) => [...stackQueryKeys.all, "boilerplate-file", code, path] as const,
}

export function useStacks(params?: {
  skip?: number
  limit?: number
  search?: string
  is_active?: boolean
}) {
  return useQuery({
    queryKey: stackQueryKeys.list(params),
    queryFn: () => stacksApi.listStacks(params),
  })
}

export function useStack(stackId: string) {
  return useQuery({
    queryKey: stackQueryKeys.detail(stackId),
    queryFn: () => stacksApi.getStack(stackId),
    enabled: !!stackId,
  })
}

export function useStackByCode(code: string) {
  return useQuery({
    queryKey: stackQueryKeys.byCode(code),
    queryFn: () => stacksApi.getStackByCode(code),
    enabled: !!code,
  })
}

export function useAvailableSkills() {
  return useQuery({
    queryKey: stackQueryKeys.availableSkills(),
    queryFn: () => stacksApi.getAvailableSkills(),
  })
}

export function useCreateStack() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: TechStackCreate) => stacksApi.createStack(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.lists() })
      toast.success(`Stack "${data.name}" created successfully`)
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useUpdateStack() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ stackId, data }: { stackId: string; data: TechStackUpdate }) =>
      stacksApi.updateStack(stackId, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.detail(data.id) })
      toast.success(`Stack "${data.name}" updated successfully`)
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useDeleteStack() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ stackId, deleteFiles }: { stackId: string; deleteFiles?: boolean }) =>
      stacksApi.deleteStack(stackId, deleteFiles),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.lists() })
      toast.success("Stack deleted successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

// Skill File Queries
export function useSkillTree(code: string) {
  return useQuery({
    queryKey: stackQueryKeys.skillTree(code),
    queryFn: () => stacksApi.getSkillTree(code),
    enabled: !!code,
  })
}

export function useSkillFile(code: string, path: string) {
  return useQuery({
    queryKey: stackQueryKeys.skillFile(code, path),
    queryFn: () => stacksApi.readSkillFile(code, path),
    enabled: !!code && !!path,
  })
}

export function useCreateSkillFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path, content }: { code: string; path: string; content?: string }) =>
      stacksApi.createSkillFile(code, path, content),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.skillTree(variables.code) })
      toast.success("File created successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useUpdateSkillFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path, content }: { code: string; path: string; content: string }) =>
      stacksApi.updateSkillFile(code, path, content),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.skillFile(variables.code, variables.path) })
      toast.success("File saved successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useDeleteSkillFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path }: { code: string; path: string }) =>
      stacksApi.deleteSkillFile(code, path),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.skillTree(variables.code) })
      toast.success("File deleted successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useCreateSkillFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path }: { code: string; path: string }) =>
      stacksApi.createSkillFolder(code, path),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.skillTree(variables.code) })
      toast.success("Folder created successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useDeleteSkillFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path }: { code: string; path: string }) =>
      stacksApi.deleteSkillFolder(code, path),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.skillTree(variables.code) })
      toast.success("Folder deleted successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

// Boilerplate File Queries
export function useBoilerplateTree(code: string) {
  return useQuery({
    queryKey: stackQueryKeys.boilerplateTree(code),
    queryFn: () => stacksApi.getBoilerplateTree(code),
    enabled: !!code,
  })
}

export function useBoilerplateFile(code: string, path: string) {
  return useQuery({
    queryKey: stackQueryKeys.boilerplateFile(code, path),
    queryFn: () => stacksApi.readBoilerplateFile(code, path),
    enabled: !!code && !!path,
  })
}

export function useCreateBoilerplateFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path, content }: { code: string; path: string; content?: string }) =>
      stacksApi.createBoilerplateFile(code, path, content),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.boilerplateTree(variables.code) })
      toast.success("File created successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useUpdateBoilerplateFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path, content }: { code: string; path: string; content: string }) =>
      stacksApi.updateBoilerplateFile(code, path, content),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.boilerplateFile(variables.code, variables.path) })
      toast.success("File saved successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useDeleteBoilerplateFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path }: { code: string; path: string }) =>
      stacksApi.deleteBoilerplateFile(code, path),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.boilerplateTree(variables.code) })
      toast.success("File deleted successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useCreateBoilerplateFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path }: { code: string; path: string }) =>
      stacksApi.createBoilerplateFolder(code, path),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.boilerplateTree(variables.code) })
      toast.success("Folder created successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useDeleteBoilerplateFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, path }: { code: string; path: string }) =>
      stacksApi.deleteBoilerplateFolder(code, path),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.boilerplateTree(variables.code) })
      toast.success("Folder deleted successfully")
    },
    onError: (error: any) => {
      toast.error(parseApiError(error))
    },
  })
}

export function useUploadBoilerplateFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      code,
      files,
      paths,
      clearExisting,
    }: {
      code: string
      files: File[]
      paths: string[]
      clearExisting?: boolean
    }) => stacksApi.uploadBoilerplateFolder(code, files, paths, clearExisting),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: stackQueryKeys.boilerplateTree(variables.code) })
      toast.success(`Uploaded ${data.uploaded} files (${data.skipped} skipped)`)
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to upload folder")
    },
  })
}

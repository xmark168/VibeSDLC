import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import {
  Settings,
  Loader2,
  RotateCcw,
  Info,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Slider } from "@/components/ui/slider"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { toast } from "@/lib/toast"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { agentsApi } from "@/apis/agents"

const configSchema = z.object({
  temperature: z.number().min(0).max(2),
  max_tokens: z.number().min(100).max(32000),
  top_p: z.number().min(0).max(1),
  model_name: z.string().optional().nullable(),
  system_prompt_override: z.string().optional().nullable(),
  timeout_seconds: z.number().min(30).max(3600),
  retry_count: z.number().min(0).max(10),
})

type ConfigFormData = z.infer<typeof configSchema>

interface AgentConfigDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  agentId: string
  agentName: string
  roleType: string
}

export function AgentConfigDialog({
  open,
  onOpenChange,
  agentId,
  agentName,
  roleType,
}: AgentConfigDialogProps) {
  const queryClient = useQueryClient()

  const { data: configData, isLoading: configLoading } = useQuery({
    queryKey: ["agent-config", agentId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/agents/config/${agentId}`, {
        credentials: "include",
      })
      if (!response.ok) throw new Error("Failed to fetch config")
      return response.json()
    },
    enabled: open && !!agentId,
  })

  const { data: defaultsData } = useQuery({
    queryKey: ["agent-config-defaults", roleType],
    queryFn: async () => {
      const response = await fetch(`/api/v1/agents/config/defaults/${roleType}`, {
        credentials: "include",
      })
      if (!response.ok) throw new Error("Failed to fetch defaults")
      return response.json()
    },
    enabled: open && !!roleType,
  })

  const form = useForm<ConfigFormData>({
    resolver: zodResolver(configSchema),
    defaultValues: {
      temperature: 0.7,
      max_tokens: 4096,
      top_p: 1.0,
      model_name: null,
      system_prompt_override: null,
      timeout_seconds: 300,
      retry_count: 3,
    },
  })

  useEffect(() => {
    if (configData?.config) {
      form.reset({
        temperature: configData.config.temperature,
        max_tokens: configData.config.max_tokens,
        top_p: configData.config.top_p,
        model_name: configData.config.model_name,
        system_prompt_override: configData.config.system_prompt_override,
        timeout_seconds: configData.config.timeout_seconds,
        retry_count: configData.config.retry_count,
      })
    }
  }, [configData, form])

  const updateConfig = useMutation({
    mutationFn: async (data: ConfigFormData) => {
      const response = await fetch(`/api/v1/agents/config/${agentId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error("Failed to update config")
      return response.json()
    },
    onSuccess: () => {
      toast.success("Agent configuration updated")
      queryClient.invalidateQueries({ queryKey: ["agent-config", agentId] })
      onOpenChange(false)
    },
    onError: (error) => {
      toast.error(`Failed to update: ${error.message}`)
    },
  })

  const resetConfig = useMutation({
    mutationFn: async () => {
      const response = await fetch(`/api/v1/agents/config/${agentId}/reset`, {
        method: "POST",
        credentials: "include",
      })
      if (!response.ok) throw new Error("Failed to reset config")
      return response.json()
    },
    onSuccess: () => {
      toast.success("Configuration reset to defaults")
      queryClient.invalidateQueries({ queryKey: ["agent-config", agentId] })
      if (defaultsData?.defaults) {
        form.reset({
          temperature: defaultsData.defaults.temperature,
          max_tokens: defaultsData.defaults.max_tokens,
          top_p: defaultsData.defaults.top_p,
          timeout_seconds: defaultsData.defaults.timeout_seconds,
          retry_count: defaultsData.defaults.retry_count,
          model_name: null,
          system_prompt_override: null,
        })
      }
    },
    onError: (error) => {
      toast.error(`Failed to reset: ${error.message}`)
    },
  })

  const onSubmit = (data: ConfigFormData) => {
    updateConfig.mutate(data)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Configure Agent: {agentName}
          </DialogTitle>
          <DialogDescription>
            Customize LLM parameters and behavior for this agent.
            {defaultsData?.defaults?.description && (
              <span className="block mt-1 text-xs">
                Role default: {defaultsData.defaults.description}
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        {configLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="temperature"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-2">
                        Temperature
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <Info className="w-3 h-3 text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent>
                              <p className="max-w-xs">
                                Controls randomness. Lower = more focused, higher = more creative
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </FormLabel>
                      <FormControl>
                        <div className="space-y-2">
                          <Slider
                            value={[field.value]}
                            onValueChange={([v]) => field.onChange(v)}
                            min={0}
                            max={2}
                            step={0.1}
                          />
                          <div className="text-right text-sm text-muted-foreground">
                            {field.value.toFixed(1)}
                          </div>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="top_p"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-2">
                        Top P
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <Info className="w-3 h-3 text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent>
                              <p className="max-w-xs">
                                Nucleus sampling. Consider tokens with top_p probability mass
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </FormLabel>
                      <FormControl>
                        <div className="space-y-2">
                          <Slider
                            value={[field.value]}
                            onValueChange={([v]) => field.onChange(v)}
                            min={0}
                            max={1}
                            step={0.05}
                          />
                          <div className="text-right text-sm text-muted-foreground">
                            {field.value.toFixed(2)}
                          </div>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="max_tokens"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Tokens</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>Maximum response length</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="timeout_seconds"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Timeout (seconds)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>Max execution time</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="retry_count"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Retry Count</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>Retries on failure</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="model_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Model Override (optional)</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="e.g., gpt-4-turbo"
                          {...field}
                          value={field.value || ""}
                          onChange={(e) => field.onChange(e.target.value || null)}
                        />
                      </FormControl>
                      <FormDescription>Leave empty for default</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="system_prompt_override"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>System Prompt Override (optional)</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Custom system prompt for this agent..."
                        className="min-h-[100px]"
                        {...field}
                        value={field.value || ""}
                        onChange={(e) => field.onChange(e.target.value || null)}
                      />
                    </FormControl>
                    <FormDescription>
                      Override the default system prompt. Leave empty to use role default.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter className="gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => resetConfig.mutate()}
                  disabled={resetConfig.isPending}
                >
                  {resetConfig.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <RotateCcw className="w-4 h-4 mr-2" />
                  )}
                  Reset to Defaults
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => onOpenChange(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={updateConfig.isPending}>
                  {updateConfig.isPending && (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  )}
                  Save Configuration
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  )
}

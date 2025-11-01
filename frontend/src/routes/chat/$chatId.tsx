import { createFileRoute, redirect } from '@tanstack/react-router'

// Legacy route: redirect /chat/$chatId -> /workspace/$workspaceId
export const Route = createFileRoute('/chat/$chatId')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/workspace/$workspaceId', params: { workspaceId: params.chatId } })
  },
  component: () => null,
})

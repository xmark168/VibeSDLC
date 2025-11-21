import ChatInterface from "./bento/chat-interface"
import EasyDeployment from "./bento/easy-deployment"
import kanbanBento from "./bento/kanban"
import MultiAgentTeam from "./bento/multi-agent-ai-team"
import ParallelCodingAgents from "./bento/parallel-agents"
import TestingQA from "./bento/testing-qa"

interface BentoCardProps {
  title: string
  description: string
  Component: React.ComponentType
}
const BentoCard = ({ title, description, Component }: BentoCardProps) => (
  <div className="overflow-hidden rounded-2xl border border-white/20 flex flex-col justify-start items-start relative">
    {/* Background with blur effect */}
    <div
      className="absolute inset-0 rounded-2xl"
      style={{
        background: "rgba(231, 236, 235, 0.08)",
        backdropFilter: "blur(4px)",
        WebkitBackdropFilter: "blur(4px)",
      }}
    />
    {/* Additional subtle gradient overlay */}
    <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent rounded-2xl" />

    <div className="self-stretch p-6 flex flex-col justify-start items-start gap-2 relative z-10">
      <div className="self-stretch flex flex-col justify-start items-start gap-1.5">
        <p className="self-stretch text-foreground text-lg font-normal leading-7">
          {title} <br />
          <span className="text-muted-foreground">{description}</span>
        </p>
      </div>
    </div>
    <div className="self-stretch h-72 relative -mt-0.5 z-10">
      <Component />
    </div>
  </div>
)

export function BentoSection() {
  const cards = [
    {
      title: "Multi-Agent AI Team",
      description:
        "Complete development team with Business Analyst, Team Leader, Developer, and Tester agents working in harmony.",
      Component: MultiAgentTeam,
    },
    {
      title: "Interactive Chat Interface",
      description:
        "Direct conversation with each agent for context, approvals, and real-time collaboration.",
      Component: ChatInterface,
    },
    {
      title: "Visual Kanban Board",
      description:
        "Track agent progress transparently with real-time status updates and WIP limits.",
      Component: kanbanBento,
    },
    {
      title: "Automated Testing & QA",
      description:
        "Quality gates, automated tests, and merge policies ensure production-ready code.",
      Component: TestingQA,
    },
    {
      title: "Full SDLC Automation",
      description: "Solve complex problems faster with multiple AI agents.",
      Component: ParallelCodingAgents,
    },
    {
      title: "Production-Ready Output",
      description:
        "Scalable, maintainable code with complete traceability and CI/CD integration.",
      Component: EasyDeployment,
    },
  ]

  return (
    <section className="w-full px-5 flex flex-col justify-center items-center overflow-visible bg-transparent">
      <div className="w-full py-8 md:py-16 relative flex flex-col justify-start items-start gap-6">
        <div className="w-[547px] h-[938px] absolute top-[614px] left-[80px] origin-top-left rotate-[-33.39deg] bg-primary/10 blur-[130px] z-0" />

        <div className="self-stretch grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 z-10 mt-96">
          {cards.map((card) => (
            <BentoCard key={card.title} {...card} />
          ))}
        </div>
      </div>
    </section>
  )
}

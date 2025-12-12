import { createFileRoute } from "@tanstack/react-router"
import { HeroSection } from "@/components/landing/hero-section"
import { AnimatedSection } from "@/components/landing/animated-section"
import { GlowingEffect } from "@/components/ui/glow-effect-card"
import { StaggerTestimonials } from "@/components/ui/stagger-testitermonials"
import { Footer } from "@/components/ui/footer"
import {
  Users, Code, FileText, Shield, ArrowRight, Sparkles,
  Workflow, MessageSquare, BarChart3, Zap, GitBranch, CheckCircle2, Quote
} from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"
import { Header } from "@/components/landing/header"

export const Route = createFileRoute("/")({
  component: RouteComponent,
})

// Features for GlowingEffect cards
const features = [
  {
    icon: <Workflow className="h-4 w-4 text-primary" />,
    title: "Kanban Workflow",
    description: "Manage tasks using Kanban model with WIP limits, helping teams focus and avoid overload.",
    area: "md:[grid-area:1/1/2/7] xl:[grid-area:1/1/2/5]",
  },
  {
    icon: <MessageSquare className="h-4 w-4 text-primary" />,
    title: "Natural Language Chat",
    description: "Communicate with AI agents like real colleagues, no complex syntax to learn.",
    area: "md:[grid-area:1/7/2/13] xl:[grid-area:2/1/3/5]",
  },
  {
    icon: <GitBranch className="h-4 w-4 text-primary" />,
    title: "Smart Task Routing",
    description: "Team Leader automatically analyzes requests and routes to the most suitable agent for optimal efficiency.",
    area: "md:[grid-area:2/1/3/7] xl:[grid-area:1/5/3/8]",
  },
  {
    icon: <BarChart3 className="h-4 w-4 text-primary" />,
    title: "Flow Metrics & Analytics",
    description: "Track cycle time, throughput and bottlenecks to continuously improve processes.",
    area: "md:[grid-area:2/7/3/13] xl:[grid-area:1/8/2/13]",
  },
  {
    icon: <Zap className="h-4 w-4 text-primary" />,
    title: "10x Development Speed",
    description: "From idea to PRD, User Stories, Code and Test - all supported by AI in parallel.",
    area: "md:[grid-area:3/1/4/13] xl:[grid-area:2/8/3/13]",
  },
]

interface GridItemProps {
  area: string
  icon: React.ReactNode
  title: string
  description: React.ReactNode
}

const GridItem = ({ area, icon, title, description }: GridItemProps) => {
  return (
    <li className={cn("min-h-[14rem] list-none", area)}>
      <div className="relative h-full rounded-2xl border border-border p-2 md:rounded-3xl md:p-3">
        <GlowingEffect
          spread={40}
          glow={true}
          disabled={false}
          proximity={64}
          inactiveZone={0.01}
          borderWidth={3}
        />
        <div className="relative flex h-full flex-col justify-between gap-6 overflow-hidden rounded-xl border border-border/50 bg-background p-6 shadow-sm dark:shadow-[0px_0px_27px_0px_rgba(45,45,45,0.3)]">
          <div className="relative flex flex-1 flex-col justify-between gap-3">
            <div className="w-fit rounded-lg border border-border bg-muted p-2.5">
              {icon}
            </div>
            <div className="space-y-3">
              <h3 className="text-xl font-semibold tracking-tight text-foreground md:text-2xl">
                {title}
              </h3>
              <p className="text-sm leading-relaxed text-muted-foreground md:text-base">
                {description}
              </p>
            </div>
          </div>
        </div>
      </div>
    </li>
  )
}

const agents = [
  {
    icon: Users,
    title: "Team Leader",
    subtitle: "Routing Coordinator",
    description: "Coordinate work and provide Agile/Kanban consulting for the team",
    image: "/assets/images/agent/1.webp",
    gradient: "from-amber-500 to-orange-600",
    bgGradient: "from-amber-500/10 to-orange-500/5",
    features: ["Smart Routing", "WIP Management", "Agile Coaching", "Flow Metrics"],
  },
  {
    icon: Code,
    title: "Developer",
    subtitle: "Software Engineer",
    description: "Implement features, code review and technical solutions",
    image: "/assets/images/agent/2.png",
    gradient: "from-violet-500 to-purple-600",
    bgGradient: "from-violet-500/10 to-purple-500/5",
    features: ["Code Generation", "Bug Fixing", "Architecture", "Code Review"],
  },
  {
    icon: FileText,
    title: "Business Analyst",
    subtitle: "Requirements Specialist",
    description: "Analyze requirements, create PRD and write user stories",
    image: "/assets/images/agent/3.png",
    gradient: "from-cyan-500 to-blue-600",
    bgGradient: "from-cyan-500/10 to-blue-500/5",
    features: ["PRD Creation", "User Stories", "Requirements", "Domain Analysis"],
  },
  {
    icon: Shield,
    title: "Tester",
    subtitle: "QA Engineer",
    description: "Create test plans, perform QA and ensure quality",
    image: "/assets/images/agent/4.webp",
    gradient: "from-rose-500 to-red-600",
    bgGradient: "from-rose-500/10 to-red-500/5",
    features: ["Test Planning", "QA Automation", "Bug Reporting", "Quality Gates"],
  },
]

function AgentFlipCard({ agent }: { agent: typeof agents[0] }) {
  const [isFlipped, setIsFlipped] = useState(false)
  const Icon = agent.icon

  return (
    <div
      className="relative w-full max-w-[300px] h-[380px] group [perspective:2000px] cursor-pointer"
      onMouseEnter={() => setIsFlipped(true)}
      onMouseLeave={() => setIsFlipped(false)}
    >
      <div
        className={cn(
          "relative w-full h-full [transform-style:preserve-3d] transition-all duration-700",
          isFlipped ? "[transform:rotateY(180deg)]" : "[transform:rotateY(0deg)]"
        )}
      >
        {/* Front */}
        <div
          className={cn(
            "absolute inset-0 w-full h-full [backface-visibility:hidden]",
            "overflow-hidden rounded-3xl",
            "bg-gradient-to-b dark:from-zinc-900 dark:to-zinc-950 from-white to-zinc-50",
            "border border-zinc-200 dark:border-zinc-800",
            "shadow-xl"
          )}
        >
          <div className={`absolute inset-0 bg-gradient-to-br ${agent.bgGradient} opacity-50`} />

          <div className="relative h-full flex flex-col">
            <div className="flex-1 flex items-center justify-center pt-6">
              <div className="relative">
                <div className={`absolute inset-0 bg-gradient-to-br ${agent.gradient} rounded-full blur-2xl opacity-30 scale-150`} />
                <img
                  src={agent.image}
                  alt={agent.title}
                  className="w-40 h-40 rounded-full object-cover border-4 border-white/20 shadow-2xl relative z-10"
                />
                <div className={`absolute -bottom-2 -right-2 p-2.5 rounded-xl bg-gradient-to-br ${agent.gradient} shadow-lg z-20`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
              </div>
            </div>

            <div className="p-6 text-center space-y-2">
              <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gradient-to-r ${agent.gradient} text-white text-xs font-medium`}>
                <Sparkles className="w-3 h-3" />
                AI Agent
              </div>
              <h3 className="text-xl font-bold text-zinc-900 dark:text-white">{agent.title}</h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">{agent.subtitle}</p>
            </div>
          </div>
        </div>

        {/* Back */}
        <div
          className={cn(
            "absolute inset-0 w-full h-full [backface-visibility:hidden] [transform:rotateY(180deg)]",
            "overflow-hidden rounded-3xl p-6",
            "bg-gradient-to-b dark:from-zinc-900 dark:to-zinc-950 from-white to-zinc-50",
            "border border-zinc-200 dark:border-zinc-800",
            "shadow-xl flex flex-col"
          )}
        >
          <div className={`absolute inset-0 bg-gradient-to-br ${agent.bgGradient} opacity-30`} />

          <div className="relative flex-1 flex flex-col">
            <div className="flex items-center gap-3 mb-4">
              <div className={`p-2.5 rounded-xl bg-gradient-to-br ${agent.gradient}`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-zinc-900 dark:text-white">{agent.title}</h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">{agent.subtitle}</p>
              </div>
            </div>

            <p className="text-sm text-zinc-600 dark:text-zinc-300 mb-6 leading-relaxed">
              {agent.description}
            </p>

            <div className="space-y-2.5 flex-1">
              <p className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">Capabilities</p>
              {agent.features.map((feature, idx) => (
                <div
                  key={feature}
                  className="flex items-center gap-2.5 text-sm text-zinc-700 dark:text-zinc-300"
                  style={{
                    transform: isFlipped ? "translateX(0)" : "translateX(-10px)",
                    opacity: isFlipped ? 1 : 0,
                    transition: `all 0.4s ease ${idx * 80 + 150}ms`,
                  }}
                >
                  <div className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${agent.gradient}`} />
                  {feature}
                </div>
              ))}
            </div>

            <div className={cn(
              "mt-4 flex items-center justify-between p-3 -mx-1 rounded-xl",
              "bg-zinc-100 dark:bg-zinc-800/50",
              "hover:bg-gradient-to-r hover:from-zinc-100 hover:to-transparent",
              "dark:hover:from-zinc-800 dark:hover:to-transparent",
              "transition-all duration-300 cursor-pointer group/cta"
            )}>
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-200 group-hover/cta:text-zinc-900 dark:group-hover/cta:text-white transition-colors">
                Chat with {agent.title}
              </span>
              <ArrowRight className={`w-4 h-4 text-zinc-400 group-hover/cta:translate-x-1 transition-all bg-gradient-to-r ${agent.gradient} bg-clip-text`} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function RouteComponent() {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden pb-0">
      <div className="relative z-10">
        <main className="max-w-[1320px] mx-auto relative">
          <Header />
          <HeroSection
            badge={{
              text: "AI-Powered Software Development",
              action: {
                text: "Explore Agents",
                href: "#agents",
              },
            }}
            title="VibeSDLC - Vibe coding with AI Agents"
            description="Intelligent multi-agent system with Kanban workflow. Team Leader, Developer, Business Analyst and Tester - ready to support you throughout the entire software development lifecycle."
            actions={[
              {
                text: "Get started",
                href: "/login",
                variant: "glow",
              },
            ]}
            image={{
              light: "https://www.launchuicomponents.com/app-light.png",
              dark: "https://www.launchuicomponents.com/app-dark.png",
              alt: "VibeSDLC Dashboard Preview",
            }}
          />

          {/* Agents Section */}
          <AnimatedSection>
            <section id="agents" className="py-12 relative">
              <div className="text-center mb-10 px-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
                  <Sparkles className="w-4 h-4" />
                  AI-Powered Team
                </div>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
                  Meet the AI Agents Team
                </h2>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                  4 specialized AI agents, working seamlessly with Kanban model
                  to take your project from idea to finished product.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 px-4 justify-items-center">
                {agents.map((agent, index) => (
                  <AgentFlipCard key={index} agent={agent} />
                ))}
              </div>

              <div className="flex flex-wrap justify-center gap-8 mt-10 px-4">
                <div className="flex items-center gap-3 text-muted-foreground">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <Users className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">Smart Routing</p>
                    <p className="text-sm">Auto assignment</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-muted-foreground">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <Shield className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">WIP Limits</p>
                    <p className="text-sm">Workflow control</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-muted-foreground">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <Code className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">Conversational</p>
                    <p className="text-sm">Natural language</p>
                  </div>
                </div>
              </div>
            </section>
          </AnimatedSection>

          {/* Features Section with Glow Effect */}
          <AnimatedSection delay={0.1}>
            <section id="features" className="py-12 relative px-4">
              <div className="text-center mb-10">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
                  <CheckCircle2 className="w-4 h-4" />
                  Key Features
                </div>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
                  Why choose VibeSDLC?
                </h2>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                  Combining AI power with Agile/Kanban processes to optimize
                  the entire software development lifecycle.
                </p>
              </div>

              <ul className="grid grid-cols-1 grid-rows-none gap-4 md:grid-cols-12 md:grid-rows-3 lg:gap-4 xl:max-h-[34rem] xl:grid-rows-2">
                {features.map((feature, index) => (
                  <GridItem
                    key={index}
                    area={feature.area}
                    icon={feature.icon}
                    title={feature.title}
                    description={feature.description}
                  />
                ))}
              </ul>
            </section>
          </AnimatedSection>

          {/* Testimonials Section */}
          <AnimatedSection delay={0.2}>
            <section id="testimonials" className="py-12 relative">
              <div className="text-center mb-10 px-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
                  <Quote className="w-4 h-4" />
                  Community Reviews
                </div>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
                  What developers say about VibeSDLC?
                </h2>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                  Feedback from beta testers and early adopters in the tech community.
                </p>
              </div>
              <StaggerTestimonials />
            </section>
          </AnimatedSection>

        </main>
        
        <Footer />
      </div>
    </div>
  )
}

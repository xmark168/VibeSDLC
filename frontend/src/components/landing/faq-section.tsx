import type React from "react"
import { useState } from "react"
import { ChevronDown } from "lucide-react"

const faqData = [
    {
        question: "What is VibeSDLC and who is it for?",
        answer:
            "VibeSDLC is a Multi-Agent AI platform that automates 60-80% of the Software Development Lifecycle. It's designed for startups seeking faster time-to-market, outsourcing firms managing multiple projects, and enterprise teams wanting to maintain production-ready code quality while accelerating delivery. Unlike traditional code assistants, VibeSDLC simulates an entire Scrum team.",
    },
    {
        question: "How does VibeSDLC differ from tools like GitHub Copilot or Cursor?",
        answer:
            "While code assistants focus on generating snippets, VibeSDLC covers the entire SDLC. Our AI Product Owner clarifies requirements, Scrum Master coordinates workflow, Developer agents implement features incrementally, and Tester agents ensure quality. You get production-ready software with proper documentation, testing, and architecture—not just code snippets that accumulate technical debt.",
    },
    {
        question: "What is the Scrumban board and how does it work?",
        answer:
            "The Scrumban board provides complete visibility into your AI agents' work. You can see each agent's tasks, progress, and status in real-time. It manages sprint planning, backlog prioritization, and task assignments automatically while allowing human intervention at critical decision points. This transparency ensures you stay in control throughout the development process.",
    },
    {
        question: "How does human-in-the-loop work?",
        answer:
            "You can interact with each AI agent through a chat interface to provide context, approve/reject pull requests, adjust sprint scope, reorder the backlog, or escalate blockers. High-risk decisions, architectural changes, and scope trade-offs require your explicit confirmation. You can also skip AI-assigned tasks and delegate new ones directly to agents.",
    },
    {
        question: "What makes VibeSDLC production-ready vs just a prototype generator?",
        answer:
            "VibeSDLC implements incremental development with quality gates at every stage. Our agents follow Definition of Ready and Definition of Done, run automated tests, enforce code coverage thresholds, conduct security scans, and maintain full traceability of all decisions and changes. The output is maintainable, scalable code designed for long-term production use.",
    },
    {
        question: "Can VibeSDLC integrate with my existing DevOps tools?",
        answer:
            "Yes! VibeSDLC is designed for deep integration with your DevOps ecosystem including GitHub Actions for CI/CD, common source control platforms, and monitoring tools like Prometheus. All pull requests, test runs, and deployments are automatically tracked and linked on the Scrum board with full audit trails for compliance.",
    },
]

interface FAQItemProps {
    question: string
    answer: string
    isOpen: boolean
    onToggle: () => void
}

const FAQItem = ({ question, answer, isOpen, onToggle }: FAQItemProps) => {
    const handleClick = (e: React.MouseEvent) => {
        e.preventDefault()
        onToggle()
    }
    return (
        <div
            className={`w-full bg-[rgba(231,236,235,0.08)] shadow-[0px_2px_4px_rgba(0,0,0,0.16)] overflow-hidden rounded-[10px] outline outline-1 outline-border outline-offset-[-1px] transition-all duration-500 ease-out cursor-pointer`}
            onClick={handleClick}
        >
            <div className="w-full px-5 py-[18px] pr-4 flex justify-between items-center gap-5 text-left transition-all duration-300 ease-out">
                <div className="flex-1 text-foreground text-base font-medium leading-6 break-words">{question}</div>
                <div className="flex justify-center items-center">
                    <ChevronDown
                        className={`w-6 h-6 text-muted-foreground-dark transition-all duration-500 ease-out ${isOpen ? "rotate-180 scale-110" : "rotate-0 scale-100"}`}
                    />
                </div>
            </div>
            <div
                className={`overflow-hidden transition-all duration-500 ease-out ${isOpen ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"}`}
                style={{
                    transitionProperty: "max-height, opacity, padding",
                    transitionTimingFunction: "cubic-bezier(0.4, 0, 0.2, 1)",
                }}
            >
                <div
                    className={`px-5 transition-all duration-500 ease-out ${isOpen ? "pb-[18px] pt-2 translate-y-0" : "pb-0 pt-0 -translate-y-2"}`}
                >
                    <div className="text-foreground/80 text-sm font-normal leading-6 break-words">{answer}</div>
                </div>
            </div>
        </div>
    )
}

export function FAQSection() {
    const [openItems, setOpenItems] = useState<Set<number>>(new Set())
    const toggleItem = (index: number) => {
        const newOpenItems = new Set(openItems)
        if (newOpenItems.has(index)) {
            newOpenItems.delete(index)
        } else {
            newOpenItems.add(index)
        }
        setOpenItems(newOpenItems)
    }
    return (
        <section className="w-full pt-[66px] pb-20 md:pb-40 px-5 relative flex flex-col justify-center items-center">
            <div className="w-[300px] h-[500px] absolute top-[150px] left-1/2 -translate-x-1/2 origin-top-left rotate-[-33.39deg] bg-primary/10 blur-[100px] z-0" />
            <div className="self-stretch pt-8 pb-8 md:pt-14 md:pb-14 flex flex-col justify-center items-center gap-2 relative z-10">
                <div className="flex flex-col justify-start items-center gap-4">
                    <h2 className="w-full max-w-[435px] text-center text-foreground text-4xl font-semibold leading-10 break-words">
                        Frequently Asked Questions
                    </h2>
                    <p className="self-stretch text-center text-muted-foreground text-sm font-medium leading-[18.20px] break-words">
                        Everything you need to know about VibeSDLC and how it can transform your development workflow
                    </p>
                </div>
            </div>
            <div className="w-full max-w-[600px] pt-0.5 pb-10 flex flex-col justify-start items-start gap-4 relative z-10">
                {faqData.map((faq, index) => (
                    <FAQItem key={index} {...faq} isOpen={openItems.has(index)} onToggle={() => toggleItem(index)} />
                ))}
            </div>
        </section>
    )
}

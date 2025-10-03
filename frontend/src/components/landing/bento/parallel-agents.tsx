import type React from "react"

interface ParallelCodingAgentsProps {
    className?: string
}

const ParallelCodingAgents: React.FC<ParallelCodingAgentsProps> = ({ className = "" }) => {
    const agents = [
        {
            icon: <CheckmarkIcon />,
            title: "Update buttons",
            tokens: "12k tokens",
            model: "o3",
            branch: "pointer/update-pain...",
        },
        {
            icon: <RefreshIcon />,
            title: "Fix sanity issue",
            tokens: "12k tokens",
            model: "claude-sonnet-4",
            branch: "pointer/update-pain...",
        },
        {
            icon: <SparklesIcon />,
            title: "Plan for seamless toast",
            tokens: "30k tokens",
            model: "o3",
            branch: "pointer/update-pain...",
        },
    ]

    return (
        <div
            className={`${className} bg-[#2a2b2a]/80 backdrop-blur-xl border border-[#3a3b3a] rounded-2xl overflow-hidden`}
            style={{
                width: "100%",
                height: "100%",
                position: "relative",
            }}
            role="img"
            aria-label="Parallel coding agents working on different tasks simultaneously"
        >
            {/* Inner content area */}
            <div
                className="p-6 h-full flex flex-col gap-4"
            >
                {agents.map((agent, index) => (
                    <div
                        key={index}
                        className="bg-[#2a2b2a]/60 backdrop-blur-md border border-[#3a3b3a] rounded-xl p-4 "
                        style={{
                            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
                        }}
                    >
                        <div className="flex items-start gap-3">
                            {/* Icon container */}
                            <div className="w-8 h-8 rounded-lg bg-[#3a3b3a] border border-[#4a4b4a] flex items-center justify-center flex-shrink-0">
                                <div className="w-4 h-4 text-white">
                                    {agent.icon}
                                </div>
                            </div>

                            {/* Content container */}
                            <div className="flex-1 min-w-0">
                                <div className="text-white font-medium text-sm mb-1">
                                    {agent.title}
                                </div>
                                <div className="text-[#9ca3af] text-xs truncate">
                                    {`${agent.tokens} • ${agent.model} • ${agent.branch}`}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// Icon components (giữ nguyên từ code gốc)
const CheckmarkIcon = () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20 6L9 17l-5-5" />
    </svg>
)

const RefreshIcon = () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M23 4v6h-6M1 20v-6h6" />
        <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
    </svg>
)

const SparklesIcon = () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
)

export default ParallelCodingAgents
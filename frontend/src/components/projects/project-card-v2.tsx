import { useState } from "react";
import { ExternalLink, Github, MoreHorizontal, Clock, Zap, GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProjectCardProps {
    title: string;
    code: string;
    status: "in-progress" | "completed" | "planning" | "on-hold";
    techStack: string[];
    agents: string[];
    lastUpdated: string;
    href?: string;
    githubUrl?: string;
}

const statusConfig = {
    "in-progress": {
        label: "In Progress",
        color: "bg-primary/10 text-primary border-primary/20",
        dot: "bg-primary",
        gradient: "from-primary/20 via-primary/5 to-transparent",
    },
    completed: {
        label: "Completed",
        color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
        dot: "bg-emerald-500",
        gradient: "from-emerald-500/20 via-emerald-500/5 to-transparent",
    },
    planning: {
        label: "Planning",
        color: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
        dot: "bg-amber-500",
        gradient: "from-amber-500/20 via-amber-500/5 to-transparent",
    },
    "on-hold": {
        label: "On Hold",
        color: "bg-muted/50 text-muted-foreground border-muted",
        dot: "bg-muted-foreground",
        gradient: "from-muted/20 via-muted/5 to-transparent",
    },
};

const techIcons: Record<string, string> = {
    "Next.js": "▲",
    React: "⚛",
    TypeScript: "TS",
    Tailwind: "🎨",
    Supabase: "⚡",
    Node: "🟢",
    Python: "🐍",
    AI: "🤖",
    LangChain: "🔗",
    OpenAI: "✨",
};

export function ProjectCard({
    title,
    code,
    status,
    techStack,
    agents,
    lastUpdated,
    href,
    githubUrl,
}: ProjectCardProps) {
    const [isHovered, setIsHovered] = useState(false);
    const statusInfo = statusConfig[status];

    return (
        <div
            className={cn(
                "group relative flex flex-col overflow-hidden rounded-2xl border border-border bg-card transition-all duration-500",
                "hover:border-primary/40 hover:shadow-2xl hover:shadow-primary/10",
                isHovered && "scale-[1.02] -translate-y-1",
            )}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            {/* Gradient Background Header */}
            <div className="relative h-20 overflow-hidden">
                <div className={cn(
                    "absolute inset-0 bg-gradient-to-br transition-opacity duration-500",
                    statusInfo.gradient,
                    isHovered ? "opacity-100" : "opacity-60"
                )} />

                {/* Animated particles effect */}
                <div className="absolute inset-0 overflow-hidden">
                    <div className={cn(
                        "absolute -inset-[100%] opacity-30 transition-transform duration-[3000ms]",
                        isHovered && "rotate-180"
                    )}>
                        <div className="absolute top-1/4 left-1/4 h-32 w-32 rounded-full bg-primary/20 blur-3xl" />
                        <div className="absolute bottom-1/4 right-1/4 h-40 w-40 rounded-full bg-accent/20 blur-3xl" />
                    </div>
                </div>

                {/* Icon */}
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="relative">
                        <div className={cn(
                            "absolute -inset-8 rounded-full blur-2xl transition-all duration-500",
                            statusInfo.dot.replace('bg-', 'bg-') + '/30',
                            isHovered && "scale-150"
                        )} />
                        <GitBranch className={cn(
                            "relative h-8 w-8 transition-all duration-500",
                            isHovered && "scale-110 rotate-12",
                            status === "completed" ? "text-emerald-500" : "text-primary"
                        )} />
                    </div>
                </div>

                {/* Project Code Badge */}
                <div className="absolute left-3 top-3">
                    <span
                        className={cn(
                            "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold backdrop-blur-md uppercase tracking-wide",
                            statusInfo.color,
                        )}
                    >
                        <span className={cn("h-1.5 w-1.5 rounded-full animate-pulse", statusInfo.dot)} />
                        {code}
                    </span>
                </div>

                {/* Quick Actions */}
                <div
                    className={cn(
                        "absolute right-3 top-3 flex items-center gap-1.5 transition-all duration-300",
                        isHovered ? "translate-y-0 opacity-100" : "-translate-y-2 opacity-0",
                    )}
                >
                    {githubUrl && (
                        <a
                            href={githubUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded-lg bg-background/90 p-1.5 backdrop-blur-md transition-all hover:bg-background hover:scale-110"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <Github className="h-3.5 w-3.5" />
                        </a>
                    )}
                    {href && (
                        <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded-lg bg-background/90 p-1.5 backdrop-blur-md transition-all hover:bg-background hover:scale-110"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                    )}
                    <button className="rounded-lg bg-background/90 p-1.5 backdrop-blur-md transition-all hover:bg-background hover:scale-110">
                        <MoreHorizontal className="h-3.5 w-3.5" />
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex flex-1 flex-col gap-3 p-4">
                {/* Title */}
                <h3 className="text-base font-bold leading-tight text-foreground transition-colors group-hover:text-primary line-clamp-1">
                    {title}
                </h3>

                {/* Tech Stack */}
                <div className="flex flex-wrap gap-1.5">
                    {techStack.slice(0, 4).map((tech) => (
                        <span
                            key={tech}
                            className="inline-flex items-center gap-1 rounded-md bg-secondary/60 px-2 py-1 text-[10px] font-medium text-secondary-foreground transition-colors hover:bg-secondary"
                        >
                            <span className="text-xs">{techIcons[tech] || "•"}</span>
                            {tech}
                        </span>
                    ))}
                    {techStack.length > 4 && (
                        <span className="inline-flex items-center rounded-md bg-secondary/40 px-2 py-1 text-[10px] font-medium text-muted-foreground">
                            +{techStack.length - 4}
                        </span>
                    )}
                </div>

                {/* Agents */}
                <div className="space-y-1.5">
                    <div className="text-[10px] font-medium text-muted-foreground">Agents</div>
                    <div className="flex flex-wrap gap-1.5">
                        {agents.map((agent, index) => (
                            <div
                                key={index}
                                className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-[10px] font-medium text-primary border border-primary/20"
                            >
                                <span className="text-xs">🤖</span>
                                {agent}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Last Updated */}
                <div className="mt-auto flex items-center gap-1.5 border-t border-border pt-3 text-[10px] text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>Updated {lastUpdated}</span>
                </div>
            </div>

            {/* Hover border glow */}
            <div
                className={cn(
                    "pointer-events-none absolute inset-0 rounded-2xl transition-opacity duration-500",
                    "ring-1 ring-inset ring-primary/0",
                    isHovered && "ring-primary/20",
                )}
            />
        </div>
    );
}

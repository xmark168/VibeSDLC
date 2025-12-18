import type React from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useEffect, useRef, useState } from "react";
import { CornerDownLeft } from "lucide-react";
export interface Agent {
    id: string;
    name: string;
    role: string;
    color: string;
    icon: string;
    persona_avatar?: string | null;
}
interface MentionDropdownProps {
    agents: Agent[];
    onSelect: (agent: Agent) => void;
    onClose: () => void;
    excludeRef?: React.RefObject<HTMLElement>;
}

export const MentionDropdown = ({ agents, onSelect, onClose, excludeRef }: MentionDropdownProps) => {
    const dropdownRef = useRef<HTMLDivElement>(null);
    const [selectedIndex, setSelectedIndex] = useState(0);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            // Don't close if clicking inside dropdown
            if (dropdownRef.current?.contains(target)) return;
            // Don't close if clicking inside excluded element (textarea)
            if (excludeRef?.current?.contains(target)) return;
            // Don't close if clicking on textarea or input (for typing)
            if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') return;
            onClose();
        };

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "ArrowDown") {
                event.preventDefault();
                setSelectedIndex((prev) => (prev + 1) % agents.length);
            } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setSelectedIndex((prev) => (prev - 1 + agents.length) % agents.length);
            } else if (event.key === "Tab") {
                event.preventDefault();
                setSelectedIndex((prev) => (prev + 1) % agents.length);
            } else if (event.key === "Enter") {
                event.preventDefault();
                onSelect(agents[selectedIndex]);
            } else if (event.key === "Escape") {
                event.preventDefault();
                onClose();
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        document.addEventListener("keydown", handleKeyDown);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [onClose, agents, selectedIndex, onSelect, excludeRef]);

    if (agents.length === 0) {
        return null;
    }

    return (
        <Card
            ref={dropdownRef}
            className="absolute bottom-full left-0 mb-2 w-full max-w-sm z-50 p-0 shadow-2xl border border-border bg-card overflow-hidden"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <h3 className="text-sm font-semibold text-foreground">Group Members</h3>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <CornerDownLeft className="h-3 w-3" />
                    <span>Tab to select</span>
                </div>
            </div>

            {/* Agent List */}
            <div className="p-2 max-h-[240px] overflow-y-auto">
                {agents.map((agent, index) => (
                    <button
                        key={agent.id}
                        onClick={() => onSelect(agent)}
                        onMouseEnter={() => setSelectedIndex(index)}
                        className={cn(
                            "w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors text-left",
                            "focus:outline-none",
                            selectedIndex === index
                                ? "bg-accent"
                                : "hover:bg-accent/50"
                        )}
                    >
                        {/* Avatar */}
                        <div
                            className="h-10 w-10 rounded-full flex items-center justify-center text-lg shrink-0 overflow-hidden"
                            style={{ backgroundColor: agent.persona_avatar ? 'transparent' : agent.color }}
                        >
                            {agent.persona_avatar ? (
                                <img 
                                    src={agent.persona_avatar} 
                                    alt={agent.name}
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                agent.icon
                            )}
                        </div>

                        {/* Name and Role */}
                        <div className="flex-1 min-w-0">
                            <div className="font-medium text-foreground text-sm">{agent.name}</div>
                        </div>

                        {/* Role on the right */}
                        <div className="text-xs text-muted-foreground font-medium">
                            {agent.role}
                        </div>
                    </button>
                ))}
            </div>
        </Card>
    );
};

import React, { useState } from "react";
import {
    motion,
    useTransform,
    AnimatePresence,
    useMotionValue,
    useSpring,
} from "framer-motion";
import { cn } from "@/lib/utils";

export const AnimatedTooltip = ({
    items,
    className,
}: {
    items: {
        id: number | string;
        name: string;
        designation: string;
        image: string;
        status?: string;  // Agent status: idle, busy, running, error, etc.
        onClick?: () => void;
    }[];
    className?: string;
}) => {
    const [hoveredIndex, setHoveredIndex] = useState<number | string | null>(null);
    const springConfig = { stiffness: 100, damping: 5 };
    const x = useMotionValue(0);
    const rotate = useSpring(
        useTransform(x, [-100, 100], [-45, 45]),
        springConfig
    );
    const translateX = useSpring(
        useTransform(x, [-100, 100], [-50, 50]),
        springConfig
    );
    const handleMouseMove = (event: any) => {
        const halfWidth = event.target.offsetWidth / 2;
        x.set(event.nativeEvent.offsetX - halfWidth);
    };

    // Get status indicator color
    const getStatusColor = (status?: string) => {
        switch (status) {
            case 'idle':
                return 'bg-green-500';
            case 'busy':
            case 'running':
                return 'bg-yellow-500';
            case 'error':
            case 'terminated':
                return 'bg-red-500';
            case 'starting':
                return 'bg-blue-500';
            case 'stopped':
            case 'stopping':
                return 'bg-gray-500';
            default:
                return 'bg-gray-400';
        }
    };

    return (
        <div className={cn("flex items-center gap-2", className)}>
            {items.map((item) => (
                <div
                    className="-mr-4 relative group"
                    key={item.id}
                    onMouseEnter={() => setHoveredIndex(item.id)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    onClick={() => item.onClick?.()}
                    style={{ cursor: item.onClick ? 'pointer' : 'default' }}
                >
                    <AnimatePresence mode="popLayout">
                        {hoveredIndex === item.id && (
                            <motion.div
                                initial={{ opacity: 0, y: -20, scale: 0.6 }}
                                animate={{
                                    opacity: 1,
                                    y: 0,
                                    scale: 1,
                                    transition: {
                                        type: "spring",
                                        stiffness: 260,
                                        damping: 10,
                                    },
                                }}
                                exit={{ opacity: 0, y: -20, scale: 0.6 }}
                                style={{
                                    translateX: translateX,
                                    rotate: rotate,
                                    whiteSpace: "nowrap",
                                }}
                                className="absolute top-full mt-2 left-1/2 -translate-x-1/2 flex text-xs flex-col items-center justify-center rounded-md bg-foreground z-50 shadow-xl px-2 py-1"
                            >
                                <div className="absolute inset-x-10 z-30 w-[20%] -top-px bg-gradient-to-r from-transparent via-emerald-500 to-transparent h-px" />
                                <div className="absolute left-10 w-[40%] z-30 -top-px bg-gradient-to-r from-transparent via-sky-500 to-transparent h-px" />
                                <div className="font-bold text-background relative z-30 text-base">
                                    {item.name}
                                </div>
                                <div className="text-muted-foreground text-xs">
                                    {item.designation}
                                </div>
                                {item.status && (
                                    <div className="text-muted-foreground text-xs mt-0.5 capitalize">
                                        {item.status}
                                    </div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <div className="relative">
                        <img
                            onMouseMove={handleMouseMove}
                            src={item.image}
                            alt={item.name}
                            className="object-cover !m-0 !p-0 object-top rounded-full h-9 w-9 border-2 group-hover:scale-105 group-hover:z-30 border-background relative transition duration-500"
                        />
                        {/* Status indicator dot */}
                        {item.status && (
                            <div className={cn(
                                "absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-background",
                                getStatusColor(item.status)
                            )} />
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
};
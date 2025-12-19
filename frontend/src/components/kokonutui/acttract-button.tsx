import { cn } from "@/lib/utils";
import { motion, useAnimation } from "motion/react";
import { Magnet, Crown } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";

interface AttractButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    particleCount?: number;
    attractRadius?: number;
    content?: string;
    icon?: "magnet" | "crown";
}

interface Particle {
    id: number;
    x: number;
    y: number;
}

export default function AttractButton({
    className,
    particleCount = 12,
    attractRadius = 50,
    content,
    icon = "magnet",
    ...props
}: AttractButtonProps) {
    const [isAttracting, setIsAttracting] = useState(false);
    const [particles, setParticles] = useState<Particle[]>([]);
    const particlesControl = useAnimation();

    useEffect(() => {
        const newParticles = Array.from({ length: particleCount }, (_, i) => ({
            id: i,
            x: Math.random() * 360 - 180,
            y: Math.random() * 360 - 180,
        }));
        setParticles(newParticles);
    }, [particleCount]);

    const handleInteractionStart = useCallback(async () => {
        setIsAttracting(true);
        await particlesControl.start({
            x: 0,
            y: 0,
            transition: {
                type: "spring",
                stiffness: 50,
                damping: 10,
            },
        });
    }, [particlesControl]);

    const handleInteractionEnd = useCallback(async () => {
        setIsAttracting(false);
        await particlesControl.start((i) => ({
            x: particles[i].x,
            y: particles[i].y,
            transition: {
                type: "spring",
                stiffness: 100,
                damping: 15,
            },
        }));
    }, [particlesControl, particles]);

    return (
        <Button
            className={cn(
                "min-w-40 relative touch-none",
                "bg-primary/10 dark:bg-primary/20",
                "hover:bg-primary/20 dark:hover:bg-primary/30",
                "text-primary dark:text-primary",
                "border border-primary/30 dark:border-primary/40",
                "transition-all duration-300",
                className
            )}
            onMouseEnter={handleInteractionStart}
            onMouseLeave={handleInteractionEnd}
            onTouchStart={handleInteractionStart}
            onTouchEnd={handleInteractionEnd}
            {...props}
        >
            {particles.map((_, index) => (
                <motion.div
                    key={index}
                    custom={index}
                    initial={{ x: particles[index].x, y: particles[index].y }}
                    animate={particlesControl}
                    className={cn(
                        "absolute w-1.5 h-1.5 rounded-full",
                        "bg-primary/60 dark:bg-primary/50",
                        "transition-opacity duration-300",
                        isAttracting ? "opacity-100" : "opacity-40"
                    )}
                />
            ))}
            <span className="relative w-full flex items-center justify-center gap-2">
                {icon === "crown" ? (
                    <Crown
                        className={cn(
                            "w-4 h-4 transition-transform duration-300",
                            isAttracting && "scale-110"
                        )}
                    />
                ) : (
                    <Magnet
                        className={cn(
                            "w-4 h-4 transition-transform duration-300",
                            isAttracting && "scale-110"
                        )}
                    />
                )}
                {content || (isAttracting ? "Attracting" : "Hover me")}
            </span>
        </Button>
    );
}

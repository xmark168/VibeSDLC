import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const SQRT_5000 = Math.sqrt(5000);

const defaultTestimonials = [
    {
        tempId: 0,
        testimonial: "AI agents help our team write PRD and User Stories 5x faster. No more brainstorming all day!",
        by: "Minh Tuan, Tech Lead at FPT Software",
        imgSrc: "https://i.pravatar.cc/150?img=52"
    },
    {
        tempId: 1,
        testimonial: "Team Leader agent really understands Kanban. It automatically balances WIP and alerts when there's a bottleneck.",
        by: "Hong Nhung, Scrum Master at VNG",
        imgSrc: "https://i.pravatar.cc/150?img=44"
    },
    {
        tempId: 2,
        testimonial: "First time I've seen AI communicate so naturally. It's like chatting with a real colleague!",
        by: "Duc Anh, Senior Developer at Tiki",
        imgSrc: "https://i.pravatar.cc/150?img=12"
    },
    {
        tempId: 3,
        testimonial: "Developer agent generates pretty accurate code, just need a quick review and tweak before deploying.",
        by: "Thanh Ha, Full-stack Developer",
        imgSrc: "https://i.pravatar.cc/150?img=45"
    },
    {
        tempId: 4,
        testimonial: "Tester agent creates very detailed test cases, covering many edge cases I didn't think of.",
        by: "Quoc Bao, QA Engineer at Shopee",
        imgSrc: "https://i.pravatar.cc/150?img=15"
    },
    {
        tempId: 5,
        testimonial: "Since using VibeSDLC, cycle time reduced by 40%. Flow metrics dashboard is very intuitive!",
        by: "Phuong Linh, Product Owner at MoMo",
        imgSrc: "https://i.pravatar.cc/150?img=47"
    },
    {
        tempId: 6,
        testimonial: "BA agent analyzes requirements thoroughly, asking the right questions I hadn't thought of.",
        by: "Van Hung, Business Analyst at VNPAY",
        imgSrc: "https://i.pravatar.cc/150?img=18"
    },
    {
        tempId: 7,
        testimonial: "This multi-agent system is truly game-changing. Each agent specializes in one thing, coordinating seamlessly.",
        by: "Khanh Vy, CTO at Startup ABC",
        imgSrc: "https://i.pravatar.cc/150?img=48"
    },
    {
        tempId: 8,
        testimonial: "Finally an AI tool that understands project context. No more translating back and forth!",
        by: "Hoang Nam, Engineering Manager",
        imgSrc: "https://i.pravatar.cc/150?img=53"
    },
    {
        tempId: 9,
        testimonial: "Smart routing is very intelligent, knows how to route tasks to the right agent. Saves significant time.",
        by: "Thuy Duong, Project Manager at NashTech",
        imgSrc: "https://i.pravatar.cc/150?img=43"
    },
    {
        tempId: 10,
        testimonial: "Personas feature is great! Each agent has its own personality, much more fun than other AI tools.",
        by: "Minh Khoi, Junior Developer",
        imgSrc: "https://i.pravatar.cc/150?img=57"
    },
    {
        tempId: 11,
        testimonial: "Very effective for onboarding new members. AI explains codebase and processes clearly.",
        by: "Ngoc Anh, HR Tech at KMS Technology",
        imgSrc: "https://i.pravatar.cc/150?img=49"
    }
];

interface TestimonialCardProps {
    position: number;
    testimonial: typeof defaultTestimonials[0];
    handleMove: (steps: number) => void;
    cardSize: number;
}

const TestimonialCard: React.FC<TestimonialCardProps> = ({
    position,
    testimonial,
    handleMove,
    cardSize
}) => {
    const isCenter = position === 0;

    return (
        <div
            onClick={() => handleMove(position)}
            className={cn(
                "absolute left-1/2 top-1/2 cursor-pointer border-2 p-8 transition-all duration-500 ease-in-out",
                isCenter
                    ? "z-10 bg-primary text-primary-foreground border-primary"
                    : "z-0 bg-card text-card-foreground border-border hover:border-primary/50"
            )}
            style={{
                width: cardSize,
                height: cardSize,
                clipPath: `polygon(50px 0%, calc(100% - 50px) 0%, 100% 50px, 100% 100%, calc(100% - 50px) 100%, 50px 100%, 0 100%, 0 0)`,
                transform: `
          translate(-50%, -50%) 
          translateX(${(cardSize / 1.5) * position}px)
          translateY(${isCenter ? -65 : position % 2 ? 15 : -15}px)
          rotate(${isCenter ? 0 : position % 2 ? 2.5 : -2.5}deg)
        `,
                boxShadow: isCenter ? "0px 8px 0px 4px hsl(var(--border))" : "0px 0px 0px 0px transparent"
            }}
        >
            <span
                className="absolute block origin-top-right rotate-45 bg-border"
                style={{
                    right: -2,
                    top: 48,
                    width: SQRT_5000,
                    height: 2
                }}
            />
            <img
                src={testimonial.imgSrc}
                alt={`${testimonial.by.split(',')[0]}`}
                className="mb-4 h-14 w-12 bg-muted object-cover object-top"
                style={{
                    boxShadow: "3px 3px 0px hsl(var(--background))"
                }}
            />
            <h3 className={cn(
                "text-base sm:text-xl font-medium",
                isCenter ? "text-primary-foreground" : "text-foreground"
            )}>
                "{testimonial.testimonial}"
            </h3>
            <p className={cn(
                "absolute bottom-8 left-8 right-8 mt-2 text-sm italic",
                isCenter ? "text-primary-foreground/80" : "text-muted-foreground"
            )}>
                - {testimonial.by}
            </p>
        </div>
    );
};

export const StaggerTestimonials: React.FC = () => {
    const [cardSize, setCardSize] = useState(365);
    const [testimonialsList, setTestimonialsList] = useState(defaultTestimonials);

    const handleMove = (steps: number) => {
        const newList = [...testimonialsList];
        if (steps > 0) {
            for (let i = steps; i > 0; i--) {
                const item = newList.shift();
                if (!item) return;
                newList.push({ ...item, tempId: Math.random() });
            }
        } else {
            for (let i = steps; i < 0; i++) {
                const item = newList.pop();
                if (!item) return;
                newList.unshift({ ...item, tempId: Math.random() });
            }
        }
        setTestimonialsList(newList);
    };

    useEffect(() => {
        const updateSize = () => {
            const { matches } = window.matchMedia("(min-width: 640px)");
            setCardSize(matches ? 365 : 290);
        };

        updateSize();
        window.addEventListener("resize", updateSize);
        return () => window.removeEventListener("resize", updateSize);
    }, []);

    return (
        <div
            className="relative w-full overflow-hidden bg-muted/30"
            style={{ height: 600 }}
        >
            {testimonialsList.map((testimonial, index) => {
                const position = testimonialsList.length % 2
                    ? index - (testimonialsList.length + 1) / 2
                    : index - testimonialsList.length / 2;
                return (
                    <TestimonialCard
                        key={testimonial.tempId}
                        testimonial={testimonial}
                        handleMove={handleMove}
                        position={position}
                        cardSize={cardSize}
                    />
                );
            })}
            <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
                <button
                    onClick={() => handleMove(-1)}
                    className={cn(
                        "flex h-14 w-14 items-center justify-center text-2xl transition-colors",
                        "bg-background border-2 border-border hover:bg-primary hover:text-primary-foreground",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    )}
                    aria-label="Previous testimonial"
                >
                    <ChevronLeft />
                </button>
                <button
                    onClick={() => handleMove(1)}
                    className={cn(
                        "flex h-14 w-14 items-center justify-center text-2xl transition-colors",
                        "bg-background border-2 border-border hover:bg-primary hover:text-primary-foreground",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    )}
                    aria-label="Next testimonial"
                >
                    <ChevronRight />
                </button>
            </div>
        </div>
    );
};
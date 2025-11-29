import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const SQRT_5000 = Math.sqrt(5000);

const defaultTestimonials = [
    {
        tempId: 0,
        testimonial: "AI agents giúp team mình viết PRD và User Stories nhanh gấp 5 lần. Không còn phải ngồi brainstorm cả ngày nữa!",
        by: "Minh Tuấn, Tech Lead tại FPT Software",
        imgSrc: "https://i.pravatar.cc/150?img=52"
    },
    {
        tempId: 1,
        testimonial: "Team Leader agent thực sự hiểu Kanban. Nó tự động cân bằng WIP và nhắc nhở khi có bottleneck.",
        by: "Hồng Nhung, Scrum Master tại VNG",
        imgSrc: "https://i.pravatar.cc/150?img=44"
    },
    {
        tempId: 2,
        testimonial: "Lần đầu tiên mình thấy AI có thể giao tiếp bằng tiếng Việt tự nhiên đến vậy. Như chat với đồng nghiệp thật!",
        by: "Đức Anh, Senior Developer tại Tiki",
        imgSrc: "https://i.pravatar.cc/150?img=12"
    },
    {
        tempId: 3,
        testimonial: "Developer agent generate code khá chuẩn, chỉ cần review và tweak một chút là deploy được luôn.",
        by: "Thanh Hà, Full-stack Developer",
        imgSrc: "https://i.pravatar.cc/150?img=45"
    },
    {
        tempId: 4,
        testimonial: "Tester agent tạo test cases rất chi tiết, cover được nhiều edge cases mà mình không nghĩ tới.",
        by: "Quốc Bảo, QA Engineer tại Shopee",
        imgSrc: "https://i.pravatar.cc/150?img=15"
    },
    {
        tempId: 5,
        testimonial: "Từ khi dùng VibeSDLC, cycle time giảm 40%. Flow metrics dashboard rất trực quan!",
        by: "Phương Linh, Product Owner tại MoMo",
        imgSrc: "https://i.pravatar.cc/150?img=47"
    },
    {
        tempId: 6,
        testimonial: "BA agent phân tích requirements rất kỹ, hỏi đúng những câu hỏi mà mình chưa nghĩ tới.",
        by: "Văn Hùng, Business Analyst tại VNPAY",
        imgSrc: "https://i.pravatar.cc/150?img=18"
    },
    {
        tempId: 7,
        testimonial: "Multi-agent system này thực sự game-changing. Mỗi agent chuyên môn hóa một việc, phối hợp rất nhịp nhàng.",
        by: "Khánh Vy, CTO tại Startup ABC",
        imgSrc: "https://i.pravatar.cc/150?img=48"
    },
    {
        tempId: 8,
        testimonial: "Cuối cùng cũng có tool AI hiểu context dự án Việt Nam. Không còn phải translate qua lại nữa!",
        by: "Hoàng Nam, Engineering Manager",
        imgSrc: "https://i.pravatar.cc/150?img=53"
    },
    {
        tempId: 9,
        testimonial: "Smart routing rất thông minh, tự biết chuyển task đến đúng agent. Tiết kiệm thời gian đáng kể.",
        by: "Thùy Dương, Project Manager tại NashTech",
        imgSrc: "https://i.pravatar.cc/150?img=43"
    },
    {
        tempId: 10,
        testimonial: "Personas feature rất hay! Mỗi agent có tính cách riêng, chat vui hơn hẳn các tool AI khác.",
        by: "Minh Khôi, Junior Developer",
        imgSrc: "https://i.pravatar.cc/150?img=57"
    },
    {
        tempId: 11,
        testimonial: "Dùng để onboard member mới rất hiệu quả. AI giải thích codebase và quy trình rõ ràng.",
        by: "Ngọc Ánh, HR Tech tại KMS Technology",
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
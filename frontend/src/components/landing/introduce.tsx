import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import ScrollStack, { ScrollStackItem } from '../ScrollStack';
import { StickyScroll } from '../ui/sticky-scroll-reveal';
const content = [
    {
        title: "Collaborative Editing",
        description:
            "Work together in real time with your team, clients, and stakeholders. Collaborate on documents, share ideas, and make decisions quickly. With our platform, you can streamline your workflow and increase productivity.",
        content: (
            <div className="flex h-full w-full items-center justify-center bg-[linear-gradient(to_bottom_right,var(--cyan-500),var(--emerald-500))] text-white">
                Collaborative Editing
            </div>
        ),
    },
    {
        title: "Real time changes",
        description:
            "See changes as they happen. With our platform, you can track every modification in real time. No more confusion about the latest version of your project. Say goodbye to the chaos of version control and embrace the simplicity of real-time updates.",
        content: (
            <div className="flex h-full w-full items-center justify-center text-white">
                <img
                    src="/assets/images/rong.png"
                    width={300}
                    height={300}
                    className="h-full w-full object-cover"
                    alt="linear board demo"
                />
            </div>
        ),
    },
    {
        title: "Version control",
        description:
            "Experience real-time updates and never stress about version control again. Our platform ensures that you're always working on the most recent version of your project, eliminating the need for constant manual updates. Stay in the loop, keep your team aligned, and maintain the flow of your work without any interruptions.",
        content: (
            <div className="flex h-full w-full items-center justify-center bg-[linear-gradient(to_bottom_right,var(--orange-500),var(--yellow-500))] text-white">
                Version control
            </div>
        ),
    },
    {
        title: "Running out of content",
        description:
            "Experience real-time updates and never stress about version control again. Our platform ensures that you're always working on the most recent version of your project, eliminating the need for constant manual updates. Stay in the loop, keep your team aligned, and maintain the flow of your work without any interruptions.",
        content: (
            <div className="flex h-full w-full items-center justify-center bg-[linear-gradient(to_bottom_right,var(--cyan-500),var(--emerald-500))] text-white">
                Running out of content
            </div>
        ),
    },
];
export default function IntroduceAgents() {

    // Component Section với hiệu ứng scroll 2 chiều
    const ScrollSection = ({
        title,
        content,
        imageSide = "right",
    }: {
        title: string;
        content: string;
        imageSide?: "left" | "right";
    }) => {
        const sectionRef = useRef(null);
        const { scrollYProgress } = useScroll({
            target: sectionRef,
            offset: ["start end", "end start"],
        });

        const isLeft = imageSide === "left";

        const imageX = useTransform(scrollYProgress, [0, 0.5, 1], [isLeft ? -300 : 300, 0, isLeft ? 300 : -300]);
        const imageOpacity = useTransform(scrollYProgress, [0, 0.4, 0.6, 1], [0, 1, 1, 0]);


        const textX = useTransform(scrollYProgress, [0, 0.5, 1], [isLeft ? 300 : -300, 0, isLeft ? -300 : 300]);
        const textOpacity = useTransform(scrollYProgress, [0, 0.4, 0.6, 1], [0, 1, 1, 0]);

        return (
            <section
                ref={sectionRef}
                className="min-h-screen flex items-center py-32"
            >
                <div className="container mx-auto px-6 lg:px-20">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        {/* Ảnh */}
                        <motion.div
                            style={{ x: imageX, opacity: imageOpacity }}
                            className={isLeft ? 'order-1' : 'order-2'}
                        >
                            <img
                                src="/assets/images/rong.png"
                                alt={title}
                                className="w-full"
                            />
                        </motion.div>

                        {/* Nội dung */}
                        <motion.div
                            style={{ x: textX, opacity: textOpacity }}
                            className={`space-y-8 ${isLeft ? 'order-2 lg:pr-16' : 'order-1 lg:pl-16'}`}
                        >
                            <h2 className="text-5xl lg:text-7xl font-bold text-gray-900 leading-tight">
                                {title}
                            </h2>
                            <p className="text-lg lg:text-xl text-gray-600 leading-relaxed max-w-lg">
                                {content}
                            </p>

                        </motion.div>
                    </div>
                </div>
            </section>
        );
    };

    return (
        <div>
            {/* Hero */}
            <section
                className="h-screen flex items-center justify-center bg-gradient-to-br from-purple-900 via-pink-800 to-rose-900"
            >
                <motion.h1
                    initial={{ y: 100, opacity: 0 }}
                    whileInView={{ y: 0, opacity: 1 }}
                    transition={{ duration: 1.2 }}
                    className="text-6xl lg:text-9xl font-black text-white text-center tracking-tighter"
                >
                    CÁC AGENT HUYỀN THOẠI
                </motion.h1>
            </section>

            <ScrollSection
                title="Rồng Lửa"
                content="Ngọn lửa bất diệt – sức mạnh hủy diệt mọi kẻ thù. Biểu tượng của quyền lực tối cao trong truyền thuyết."
                imageSide="right"
            />

            <ScrollSection
                title="Băng Giá Vĩnh Cửu"
                content="Làm chủ băng tuyết, đóng băng thời gian. Sự lạnh lùng và chính xác là vũ khí đáng sợ nhất."
                imageSide="left"
            />

            <ScrollSection
                title="Thần Sấm Sét"
                content="Tốc độ ánh sáng, sức mạnh từ trời cao. Không kẻ nào thoát khỏi cơn thịnh nộ của thiên lôi."
                imageSide="right"
            />
            <div className="w-full py-4">
                <StickyScroll content={content} />
            </div>
        </div>
    );
}
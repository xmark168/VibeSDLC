
import { Header } from "./header"
import AIChat from "./ai-chat"
import { BGPattern } from "./bg-parten"


export function HeroSection() {
    return (
        <section
            className="flex flex-col items-center text-center relative mx-auto rounded-2xl overflow-hidden my-6 py-0 px-4
         w-full h-[450px] md:w-[1220px] md:h-[600px] lg:h-[810px] md:px-0"
        >
            {/* SVG Background */}
            <div className="absolute inset-0 z-0">
                <div className="relative flex aspect-video flex-col items-center justify-center rounded-2xl ">
                    <BGPattern variant="grid" mask="fade-edges" />
                </div>
            </div>

            {/* Header positioned at top of hero container */}
            <div className="absolute top-0 left-0 right-0 z-20">
                <Header />
            </div>

            <div className="relative space-y-4 md:space-y-5 lg:space-y-6 mb-6 md:mb-7 lg:mb-9 mt-16 md:mt-[120px] lg:mt-[160px] px-4 w-full max-w-4xl mx-auto">
                <AIChat />
            </div>
        </section>
    )
}

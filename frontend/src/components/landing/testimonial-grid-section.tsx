
const testimonials: TestimonialCardProps[] = [
    {
        quote:
            "VibeSDLC's multi-agent approach transformed how we build software. Having AI agents handle the entire SDLC from requirements to deployment reduced our time-to-market by 40% while maintaining production-ready quality.",
        name: "Annette Black",
        company: "Sony",
        avatar: "assets/images/avt.jpg",
        type: "large-teal",
    },
    {
        quote:
            "The AI Product Owner clarified our vague ideas into clear requirements in hours, not weeks. No more endless requirement meetings.",
        name: "Dianne Russell",
        company: "McDonald's",
        avatar: "assets/images/avt.jpg",
        type: "small-dark",
    },
    {
        quote:
            "Finally, an AI coding solution that doesn't create technical debt. VibeSDLC's incremental approach keeps our codebase maintainable and scalable.",
        name: "Cameron Williamson",
        company: "IBM",
        avatar: "assets/images/avt.jpg",
        type: "small-dark",
    },
    {
        quote:
            "The Scrumban board gives us complete visibility into what each AI agent is doing. It's like managing a real team, but 10x faster.",
        name: "Robert Fox",
        company: "MasterCard",
        avatar: "assets/images/avt.jpg",
        type: "small-dark",
    },
    {
        quote:
            "We went from idea to production-ready MVP in days instead of months. VibeSDLC automated 70% of our development cycle without sacrificing quality.",
        name: "Darlene Robertson",
        company: "Ferrari",
        avatar: "assets/images/avt.jpg",
        type: "small-dark",
    },
    {
        quote:
            "The human-in-the-loop approach is brilliant. We stay in control at critical decision points while the AI agents handle the heavy lifting.",
        name: "Cody Fisher",
        company: "Apple",
        avatar: "assets/images/avt.jpg",
        type: "small-dark",
    },
    {
        quote:
            "Unlike other AI code generators, VibeSDLC understands our business goals and architectural needs. It's not just generating code—it's building a complete, scalable system with proper documentation and testing.",
        name: "Albert Flores",
        company: "Louis Vuitton",
        avatar: "assets/images/avt.jpg",
        type: "large-light",
    },
]
interface TestimonialCardProps {
    quote: string
    name: string
    company: string
    avatar: string  // hoặc React.ReactNode nếu có thể là component
    type: 'large-teal' | 'small-dark' | 'small-light' | 'large-light'  // hoặc string nếu có nhiều type khác
}
const TestimonialCard = ({ quote, name, company, avatar, type }: TestimonialCardProps) => {
    const isLargeCard = type.startsWith("large")
    const avatarSize = isLargeCard ? 48 : 36
    const avatarBorderRadius = isLargeCard ? "rounded-[41px]" : "rounded-[30.75px]"
    const padding = isLargeCard ? "p-6" : "p-[30px]"

    let cardClasses = `flex flex-col justify-between items-start overflow-hidden rounded-[10px] shadow-[0px_2px_4px_rgba(0,0,0,0.08)] relative ${padding}`
    let quoteClasses = ""
    let nameClasses = ""
    let companyClasses = ""
    let backgroundElements = null
    let cardHeight = ""
    const cardWidth = "w-full md:w-[384px]"

    if (type === "large-teal") {
        cardClasses += " bg-primary"
        quoteClasses += " text-primary-foreground text-2xl font-medium leading-8"
        nameClasses += " text-primary-foreground text-base font-normal leading-6"
        companyClasses += " text-primary-foreground/60 text-base font-normal leading-6"
        cardHeight = "h-[502px]"
        backgroundElements = (
            <div
                className="absolute inset-0 w-full h-full bg-cover bg-center bg-no-repeat"
                style={{ backgroundImage: "url('/images/large-card-background.svg')", zIndex: 0 }}
            />
        )
    } else if (type === "large-light") {
        cardClasses += " bg-[rgba(231,236,235,0.12)]"
        quoteClasses += " text-foreground text-2xl font-medium leading-8"
        nameClasses += " text-foreground text-base font-normal leading-6"
        companyClasses += " text-muted-foreground text-base font-normal leading-6"
        cardHeight = "h-[502px]"
        backgroundElements = (
            <div
                className="absolute inset-0 w-full h-full bg-cover bg-center bg-no-repeat opacity-20"
                style={{ backgroundImage: "url('/images/large-card-background.svg')", zIndex: 0 }}
            />
        )
    } else {
        cardClasses += " bg-card outline outline-1 outline-border outline-offset-[-1px]"
        quoteClasses += " text-foreground/80 text-[17px] font-normal leading-6"
        nameClasses += " text-foreground text-sm font-normal leading-[22px]"
        companyClasses += " text-muted-foreground text-sm font-normal leading-[22px]"
        cardHeight = "h-[244px]"
    }

    return (
        <div className={`${cardClasses} ${cardWidth} ${cardHeight}`}>
            {backgroundElements}
            <div className={`relative z-10 font-normal break-words ${quoteClasses}`}>{quote}</div>
            <div className="relative z-10 flex justify-start items-center gap-3">
                <img
                    src={avatar || "/placeholder.svg"}
                    alt={`${name} avatar`}
                    width={avatarSize}
                    height={avatarSize}
                    className={`w-${avatarSize / 4} h-${avatarSize / 4} ${avatarBorderRadius}`}
                    style={{ border: "1px solid rgba(255, 255, 255, 0.08)" }}
                />
                <div className="flex flex-col justify-start items-start gap-0.5">
                    <div className={nameClasses}>{name}</div>
                    <div className={companyClasses}>{company}</div>
                </div>
            </div>
        </div>
    )
}

export function TestimonialGridSection() {
    return (
        <section className="w-full px-5 overflow-hidden flex flex-col justify-start py-6 md:py-8 lg:py-14">
            <div className="self-stretch py-6 md:py-8 lg:py-14 flex flex-col justify-center items-center gap-2">
                <div className="flex flex-col justify-start items-center gap-4">
                    <h2 className="text-center text-foreground text-3xl md:text-4xl lg:text-[40px] font-semibold leading-tight md:leading-tight lg:leading-[40px]">
                        Coding made effortless
                    </h2>
                    <p className="self-stretch text-center text-muted-foreground text-sm md:text-sm lg:text-base font-medium leading-[18.20px] md:leading-relaxed lg:leading-relaxed">
                        {"Hear how developers ship products faster, collaborate seamlessly,"} <br />{" "}
                        {"and build with confidence using VibeSDLC's powerful AI tools"}
                    </p>
                </div>
            </div>
            <div className="w-full pt-0.5 pb-4 md:pb-6 lg:pb-10 flex flex-col md:flex-row justify-center items-start gap-4 md:gap-4 lg:gap-6 max-w-[1100px] mx-auto">
                <div className="flex-1 flex flex-col justify-start items-start gap-4 md:gap-4 lg:gap-6">
                    <TestimonialCard {...testimonials[0]} />
                    <TestimonialCard {...testimonials[1]} />
                </div>
                <div className="flex-1 flex flex-col justify-start items-start gap-4 md:gap-4 lg:gap-6">
                    <TestimonialCard {...testimonials[2]} />
                    <TestimonialCard {...testimonials[3]} />
                    <TestimonialCard {...testimonials[4]} />
                </div>
                <div className="flex-1 flex flex-col justify-start items-start gap-4 md:gap-4 lg:gap-6">
                    <TestimonialCard {...testimonials[5]} />
                    <TestimonialCard {...testimonials[6]} />
                </div>
            </div>
        </section>
    )
}

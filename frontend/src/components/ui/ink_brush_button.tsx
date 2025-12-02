import type React from "react"
import { type ButtonHTMLAttributes, forwardRef } from "react"
import { cn } from "@/lib/utils"

interface InkBrushButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    children: React.ReactNode
}

const InkBrushButton = forwardRef<HTMLButtonElement, InkBrushButtonProps>(({ children, className, ...props }, ref) => {
    return (
        <button
            ref={ref}
            className={cn(
                "relative px-16 py-6 text-stone-100 font-medium tracking-widest uppercase transition-transform hover:scale-105 active:scale-95 overflow-visible",
                className,
            )}
            {...props}
        >
            {/* Ink brush stroke background using asset */}
            <img
                src="/assets/images/brush/1.png"
                alt=""
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-auto h-[200%] max-w-none object-contain pointer-events-none rotate-[-29deg]"
                aria-hidden="true"
            />

            {/* Text content */}
            <span className="relative z-10">{children}</span>
        </button>
    )
})

InkBrushButton.displayName = "InkBrushButton"

export { InkBrushButton }

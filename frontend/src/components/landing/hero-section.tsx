import BlurText from "../BlurText"
import { Button } from "../ui/button"
import { InkBrushButton } from "../ui/ink_brush_button"
import { AnimatedSection } from "./animated-section"
import { Header } from "./header"

export function HeroSection() {
  return (
    <>
      <div className="z-20"><Header /></div>

      <div className="relative w-full mt-7 overflow-hidden">

        {/* BG mountains */}
        <div className="absolute inset-0 pointer-events-none">

          <AnimatedSection className="absolute inset-0" delay={0.1}>
            <img
              src="/assets/images/mountain/6.png"
              className="absolute top-0 left-1/2 -translate-x-1/2 
              w-[300px] sm:w-[400px] md:w-[500px] opacity-60"
            />
          </AnimatedSection>

          <AnimatedSection className="absolute inset-0" delay={0.2}>
            <img
              src="/assets/images/mountain/1.png"
              className="absolute right-5 sm:right-10 top-10 
              w-[250px] sm:w-[350px] md:w-[600px] opacity-80"
            />
          </AnimatedSection>

          <AnimatedSection className="absolute inset-0" delay={0.3}>
            <img
              src="/assets/images/mountain/4.png"
              className="absolute left-5 bottom-0
              w-[220px] sm:w-[300px] md:w-[450px] opacity-80"
            />
          </AnimatedSection>

          <AnimatedSection className="absolute inset-0" delay={0.4}>
            <img
              src="/assets/images/cloud/6.png"
              className="absolute right-5 bottom-0
              w-[200px] sm:w-[280px] md:w-[450px] opacity-80 z-50"
            />
          </AnimatedSection>

          <AnimatedSection className="absolute inset-0" delay={0.5}>
            <img
              src="/assets/images/cloud/8.png"
              className="absolute left-5 top-5
              w-[120px] sm:w-[200px] md:w-[250px] opacity-30"
            />
          </AnimatedSection>
        </div>

        {/* MAIN CONTENT */}
        <div className="
          relative z-20 flex flex-col-reverse md:flex-row 
          items-center gap-8 md:gap-0 px-4 sm:px-8
        ">

          {/* Left text */}
          <div className="max-w-[600px] text-center md:text-left">

            <BlurText
              text="Isn't this so cool?!"
              delay={150}
              animateBy="words"
              direction="top"
              className="text-3xl sm:text-4xl md:text-6xl mb-2 md:mb-4 font-bold"
            />

            <BlurText
              text="This is the second line"
              delay={300}
              animateBy="words"
              direction="top"
              className="text-3xl sm:text-4xl md:text-6xl mb-2 md:mb-4 font-bold"
            />

            <p className="mt-4 text-sm sm:text-base md:text-lg">
              Lorem ipsum dolor sit amet consectetur adipisicing elit.
            </p>
            <InkBrushButton>
              Let start
            </InkBrushButton>
            {/* <Button className="mt-4 text-sm sm:text-base px-6 py-3">
              Let start
            </Button> */}
          </div>

          {/* Dragon */}
          <AnimatedSection delay={0.6}>
            <div className="z-30">
              <img
                src="/assets/images/rong.png"
                className="w-[220px] sm:w-[350px] md:w-[600px]"
                alt="shenlong"
              />
            </div>
          </AnimatedSection>
        </div>
      </div>
    </>
  )
}

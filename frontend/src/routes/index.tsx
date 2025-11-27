import { createFileRoute } from "@tanstack/react-router"
import { AIAgentsSection } from "@/components/landing/ai-agents-section"
import { AnimatedSection } from "@/components/landing/animated-section"
import { BentoSection } from "@/components/landing/bento-section"
import { DashboardPreview } from "@/components/landing/dashboard-preview"
import { FAQSection } from "@/components/landing/faq-section"
import { FooterSection } from "@/components/landing/footer-section"
import { HeroSection } from "@/components/landing/hero-section"
import { LargeTestimonial } from "@/components/landing/large-testimonial"
import { PricingSection } from "@/components/landing/pricing-section"
import IntroduceAgents from "@/components/landing/introduce"

export const Route = createFileRoute("/")({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden pb-0">
      <div className="relative z-10">
        <main className="max-w-[1320px] mx-auto relative">
          <HeroSection />

          {/* Dashboard Preview Wrapper */}

        </main>
        <IntroduceAgents />
      </div>
    </div>
  )
}

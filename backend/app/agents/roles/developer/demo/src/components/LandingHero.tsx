"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { ArrowRight, Play } from "lucide-react";
import Link from "next/link";
import type { HeroSection } from "@/types/course.types";

interface LandingHeroProps {
  heroData: HeroSection;
  className?: string;
}

export function LandingHero({ heroData, className }: LandingHeroProps) {
  return (
    <section className={`relative py-20 md:py-32 overflow-hidden ${className || ""}`.trim()}>
      <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-background" />
      <div className="relative container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="text-center lg:text-left">
            <div className="mb-8">
              <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-foreground mb-4">
                <span className="block text-primary">{heroData.title}</span>
                <span className="block mt-2">{heroData.subtitle}</span>
              </h1>
              <p className="text-lg md:text-xl text-muted-foreground leading-relaxed max-w-2xl">
                {heroData.description}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Button
                size="lg"
                className="gap-2 text-base"
                asChild
              >
                <Link href="/courses">
                  {heroData.ctaText} <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="gap-2 text-base"
                asChild
              >
                <Link href="/about">
                  How It Works <Play className="size-4" />
                </Link>
              </Button>
            </div>

            <div className="mt-8 flex flex-col sm:flex-row gap-6 justify-center lg:justify-start text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full" />
                <span>Trusted by 50,000+ learners</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full" />
                <span>4.9/5 average rating</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full" />
                <span>Industry expert instructors</span>
              </div>
            </div>
          </div>

          <div className="relative">
            <div className="relative mx-auto w-[400px] h-[300px] lg:w-[500px] lg:h-[400px]">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20 rounded-2xl transform rotate-2" />
              <div className="absolute inset-0 bg-gradient-to-br from-secondary/20 to-primary/20 rounded-2xl transform -rotate-1" />
              <div className="relative bg-card rounded-2xl p-8 shadow-lg flex items-center justify-center">
                <div className="text-center">
                  <div className="text-6xl mb-4" aria-hidden="true">
                    💻
                  </div>
                  <h3 className="text-2xl font-semibold text-foreground mb-2">
                    Start Learning
                  </h3>
                  <p className="text-muted-foreground">
                    Your tech career begins here
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
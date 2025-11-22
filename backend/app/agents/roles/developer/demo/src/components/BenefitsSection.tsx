"use client";

import * as React from "react";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import type { Benefit } from "@/types/course.types";

interface BenefitsSectionProps {
  benefits: Benefit[];
  title?: string;
  className?: string;
}

export function BenefitsSection({ benefits, title = "Why Learn With Us", className }: BenefitsSectionProps) {
  return (
    <section className={`py-16 bg-gradient-to-br from-background to-muted/50 ${className || ""}`.trim()}>
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {title}
          </h2>
          <p className="mt-4 text-lg text-muted-foreground max-w-3xl mx-auto">
            Everything you need to succeed in your tech career, all in one place.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {benefits.map((benefit) => (
            <Card
              key={benefit.id}
              className="text-center group hover:shadow-lg transition-all duration-300 border-0"
            >
              <CardContent className="p-8">
                <div className="text-4xl mb-4" aria-hidden="true">
                  {benefit.icon}
                </div>
                <CardTitle className="text-xl font-semibold mb-2 group-hover:text-primary transition-colors">
                  {benefit.title}
                </CardTitle>
                <CardDescription className="text-sm text-muted-foreground leading-relaxed">
                  {benefit.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
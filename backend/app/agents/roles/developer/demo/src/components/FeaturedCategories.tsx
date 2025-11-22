"use client";

import * as React from "react";
import { CategoryCard } from "@/components/CategoryCard";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import type { CourseCategory } from "@/types/course.types";

interface FeaturedCategoriesProps {
  categories: CourseCategory[];
  title?: string;
  subtitle?: string;
  className?: string;
}

export function FeaturedCategories({ 
  categories, 
  title = "Popular Categories",
  subtitle = "Explore our most popular course categories and start learning today",
  className 
}: FeaturedCategoriesProps) {
  const featuredCategories = categories.filter(cat => cat.featured);

  return (
    <section className={`py-16 ${className || ""}`.trim()}>
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12 max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl mb-4">
            {title}
          </h2>
          <p className="text-lg text-muted-foreground">
            {subtitle}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
          {featuredCategories.map((category) => (
            <CategoryCard
              key={category.id}
              category={category}
            />
          ))}
        </div>

        <div className="text-center">
          <Button
            asChild
            size="lg"
            className="gap-2"
          >
            <Link href="/courses">
              View All Courses <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
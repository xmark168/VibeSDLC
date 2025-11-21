"use client";

import * as React from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import type { CourseCategory } from "@/types/course.types";

interface CategoryCardProps {
  category: CourseCategory;
  onClick?: () => void;
}

export function CategoryCard({ category, onClick }: CategoryCardProps) {
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  return (
    <Card
      className="group cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105"
      onClick={handleClick}
    >
      <div
        className={`h-48 bg-gradient-to-br ${category.color} rounded-t-xl overflow-hidden relative flex items-end justify-center p-6`}
      >
        <div className="text-6xl mb-4" aria-hidden="true">
          {category.icon}
        </div>
        <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition-colors" />
      </div>
      
      <CardContent className="p-6">
        <CardTitle className="text-xl font-semibold mb-2 group-hover:text-primary transition-colors">
          {category.title}
        </CardTitle>
        <CardDescription className="text-sm text-muted-foreground mb-4 line-clamp-2">
          {category.description}
        </CardDescription>
        
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-primary">
            {category.courseCount} courses
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1"
            asChild
          >
            <Link href={`/categories/${category.slug}`}>Explore <ArrowRight className="size-3" /></Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
// "use client";

import * as React from "react";
import { notFound } from "next/navigation";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { Metadata } from "next";

interface CategoryPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: CategoryPageProps): Promise<Metadata> {
  const { slug } = await params;

  const categoryNames: Record<string, string> = {
    "web-development": "Web Development",
    "mobile-apps": "Mobile Apps",
    "data-science": "Data Science",
    "cybersecurity": "Cybersecurity",
    "cloud-computing": "Cloud Computing",
    "artificial-intelligence": "Artificial Intelligence",
  };

  const categoryName = categoryNames[slug] || slug;

  return {
    title: `${categoryName} Courses | LearnTech`,
    description: `Explore our ${categoryName.toLowerCase()} courses and start learning today.`,
  };
}

export default async function CategoryPage({ params }: CategoryPageProps) {
  const { slug } = await params;

  const categoryNames: Record<string, string> = {
    "web-development": "Web Development",
    "mobile-apps": "Mobile Apps",
    "data-science": "Data Science",
    "cybersecurity": "Cybersecurity",
    "cloud-computing": "Cloud Computing",
    "artificial-intelligence": "Artificial Intelligence",
  };

  const categoryName = categoryNames[slug];

  if (!categoryName) {
    notFound();
  }

  return (
    <div className="min-h-screen py-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <Button
              variant="ghost"
              className="gap-2 mb-4"
              asChild
            >
              <Link href="/courses">
                <ArrowLeft className="size-4" />
                Back to Courses
              </Link>
            </Button>

            <h1 className="text-4xl font-bold text-foreground mb-4">
              {categoryName} Courses
            </h1>
            <p className="text-lg text-muted-foreground">
              Explore our comprehensive {categoryName.toLowerCase()} courses designed to help you master in-demand tech skills.
            </p>
          </div>

          <Card className="border-0 shadow-lg">
            <CardContent className="p-8">
              <div className="text-center py-12">
                <div className="text-8xl mb-6" aria-hidden="true">
                  {slug === "web-development" && "💻"}
                  {slug === "mobile-apps" && "📱"}
                  {slug === "data-science" && "📊"}
                  {slug === "cybersecurity" && "🔒"}
                  {slug === "cloud-computing" && "☁️"}
                  {slug === "artificial-intelligence" && "🤖"}
                </div>
                <CardTitle className="text-2xl font-semibold mb-4">
                  {categoryName} Coming Soon
                </CardTitle>
                <CardDescription className="mb-6 max-w-2xl mx-auto">
                  We're currently developing comprehensive courses for {categoryName.toLowerCase()}. Our expert instructors are working hard to create the best learning experience for you.
                </CardDescription>

                <div className="space-y-4 text-sm text-muted-foreground">
                  <p>In the meantime, you can:</p>
                  <ul className="list-disc list-inside space-y-2">
                    <li>Explore our other available courses</li>
                    <li>Join our newsletter to get notified when these courses launch</li>
                    <li>Contact us if you have specific learning needs</li>
                  </ul>
                </div>

                <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
                  <Button
                    asChild
                    className="gap-2"
                  >
                    <Link href="/courses">
                      Browse All Courses
                    </Link>
                  </Button>
                  <Button
                    variant="outline"
                    className="gap-2"
                    asChild
                  >
                    <Link href="/contact">
                      Get Notified
                    </Link>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
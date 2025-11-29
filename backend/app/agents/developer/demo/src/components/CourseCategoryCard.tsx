"use client";

import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";

interface CourseCategoryCardProps {
  title: string;
  description: string;
  imageUrl: string;
  link: string;
}

export function CourseCategoryCard({
  title,
  description,
  imageUrl,
  link,
}: CourseCategoryCardProps) {
  return (
    <Card
      className="group hover:shadow-md transition-all duration-300 overflow-hidden h-full"
    >
      <div className="relative h-48 w-full bg-gradient-to-br from-primary/10 to-secondary/10">
        <Image
          src={imageUrl}
          alt={title}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-300"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
      </div>
      
      <CardContent className="p-6">
        <CardTitle className="text-xl font-semibold mb-2 line-clamp-2">
          {title}
        </CardTitle>
        <CardDescription className="text-sm text-muted-foreground mb-4 line-clamp-3">
          {description}
        </CardDescription>
        
        <Button
          asChild
          className="w-full group-hover:bg-primary/90 transition-colors"
        >
          <Link href={link}>View Details</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

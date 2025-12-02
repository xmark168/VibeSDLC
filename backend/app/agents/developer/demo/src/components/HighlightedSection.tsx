"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";

interface HighlightedSectionProps {
  title: string;
  description: string;
  icon: string;
}

export function HighlightedSection({
  title,
  description,
  icon,
}: HighlightedSectionProps) {
  return (
    <Card className="group hover:shadow-lg transition-all duration-300 border-none bg-gradient-to-br from-background to-muted/50">
      <CardContent className="p-6">
        <div className="flex items-center justify-center w-12 h-12 bg-primary/10 rounded-full mb-4 group-hover:bg-primary/20 transition-colors duration-300">
          <span className="text-2xl" aria-hidden="true">
            {icon === "clock" && "⏰"}
            {icon === "users" && "👥"}
            {icon === "laptop" && "💻"}
            {icon === "briefcase" && "💼"}
          </span>
        </div>
        
        <CardTitle className="text-lg font-semibold mb-2">
          {title}
        </CardTitle>
        <CardDescription className="text-sm text-muted-foreground">
          {description}
        </CardDescription>
      </CardContent>
    </Card>
  );
}

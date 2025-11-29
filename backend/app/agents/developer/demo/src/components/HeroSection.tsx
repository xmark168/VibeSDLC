import { Button } from "@/components/ui/button";
import Link from "next/link";

export function HeroSection() {
  return (
    <section className="w-full py-16 md:py-24 lg:py-28 bg-gradient-to-br from-primary/5 via-background to-secondary/5">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row items-center justify-between gap-12">
          <div className="flex-1 space-y-8 text-center lg:text-left">
            <div className="space-y-6">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground">
                Master Tech Skills
                <span className="text-primary"> Your Way</span>
              </h1>
              <p className="text-lg sm:text-xl lg:text-2xl text-muted-foreground max-w-2xl leading-relaxed">
                Join thousands of learners building in-demand tech skills with
                hands-on courses, expert instructors, and real-world projects.
              </p>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Button asChild size="lg" className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-3 text-base font-semibold rounded-full transition-all duration-300 hover:shadow-lg">
                <Link href="/categories">Explore Courses</Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="border-2 border-border text-foreground hover:bg-accent hover:text-accent-foreground px-8 py-3 text-base font-semibold rounded-full transition-all duration-300">
                <Link href="#featured">View Features</Link>
              </Button>
            </div>
            
            <div className="flex items-center justify-center lg:justify-start gap-8 text-sm text-muted-foreground pt-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full" />
                <span>10k+ Students</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-secondary rounded-full" />
                <span>500+ Courses</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-accent rounded-full" />
                <span>98% Satisfaction</span>
              </div>
            </div>
          </div>
          
          <div className="flex-1 relative hidden lg:block">
            <div className="relative w-full max-w-md mx-auto">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20 rounded-2xl transform rotate-2"></div>
              <div className="relative bg-background rounded-2xl p-8 shadow-lg border border-border/50">
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-gradient-to-br from-primary to-secondary rounded-xl flex items-center justify-center">
                      <span className="text-2xl">💻</span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground">Web Development</h3>
                      <p className="text-sm text-muted-foreground">React, Vue, Node.js</p>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Progress</span>
                      <span className="text-sm font-medium">68%</span>
                    </div>
                    <div className="w-full bg-border rounded-full h-2">
                      <div className="bg-primary rounded-full h-2 w-[68%]" />
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Next Lesson</span>
                    <Button size="sm" variant="outline" className="text-xs">React Hooks</Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

import { notFound } from "next/navigation";
import { courseCategories } from "@/lib/data/homepage";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface CategoryPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function CategoryPage({ params }: CategoryPageProps) {
  const { id } = await params;
  const category = courseCategories.find(cat => cat.id === id);

  if (!category) {
    notFound();
  }

  return (
    <div className="min-h-screen py-16 md:py-20 lg:py-24 bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <Link href="/" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6">
              ← Back to Homepage
            </Link>

            <div className="w-24 h-24 bg-gradient-to-br from-primary to-secondary rounded-full mx-auto mb-6 flex items-center justify-center text-4xl">
              {category.id === "web-development" && "🌐"}
              {category.id === "mobile-apps" && "📱"}
              {category.id === "data-science" && "📊"}
              {category.id === "design" && "🎨"}
              {category.id === "cloud-devops" && "☁️"}
              {category.id === "cybersecurity" && "🔒"}
            </div>

            <h1 className="text-4xl sm:text-5xl font-bold text-foreground mb-4">
              {category.title}
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
              {category.description}
            </p>
          </div>

          <div className="bg-card rounded-2xl p-8 shadow-sm border border-border/50">
            <div className="text-center mb-8">
              <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-4">
                Coming Soon
              </h2>
              <p className="text-base text-muted-foreground mb-6">
                We're working on creating comprehensive courses for {category.title.toLowerCase()}.
                Stay tuned for our upcoming course offerings!
              </p>

              <div className="space-y-4 text-left max-w-md mx-auto">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-primary rounded-full" />
                  <span>Expert instructors</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-secondary rounded-full" />
                  <span>Hands-on projects</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-accent rounded-full" />
                  <span>Flexible learning</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-success rounded-full" />
                  <span>Career support</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-3 text-base font-semibold rounded-full transition-all duration-300">
                <Link href="/">Browse Other Categories</Link>
              </Button>
              <Button asChild variant="outline" className="border-2 border-border text-foreground hover:bg-accent hover:text-accent-foreground px-8 py-3 text-base font-semibold rounded-full transition-all duration-300">
                <Link href="/signup">Get Notified</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export async function generateStaticParams() {
  return courseCategories.map((category) => ({
    id: category.id,
  }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const category = courseCategories.find(cat => cat.id === id);

  if (!category) {
    return {
      title: "Category Not Found | LearnTech",
      description: "The requested category could not be found."
    };
  }

  return {
    title: `${category.title} Courses | LearnTech`,
    description: `Learn ${category.title.toLowerCase()} with our comprehensive course offerings. ${category.description}`,
  };
}

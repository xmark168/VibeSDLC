import { CourseCategoryCard } from "@/components/CourseCategoryCard";
import { HighlightedSection } from "@/components/HighlightedSection";
import { HeroSection } from "@/components/HeroSection";
import { courseCategories, highlightedSections } from "@/lib/data/homepage";

export function HomepageContent() {
  return (
    <div className="min-h-screen">
      {/* Meta tags for SEO */}
      <head>
        <title>LearnTech - Master Tech Skills Your Way</title>
        <meta name="description" content="Join thousands of learners building in-demand tech skills with hands-on courses, expert instructors, and real-world projects." />
        <meta name="keywords" content="online courses, tech education, programming, web development, data science" />
      </head>

      {/* Hero Section */}
      <HeroSection />

      {/* Course Categories Section */}
      <section id="courses" className="py-16 md:py-20 lg:py-24 bg-background">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4 mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground">
              Popular Course Categories
            </h2>
            <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
              Explore our most popular courses and start your journey to mastering
              in-demand tech skills. Each course includes hands-on projects and expert instruction.
            </p>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {courseCategories.map((category) => (
              <CourseCategoryCard
                key={category.id}
                title={category.title}
                description={category.description}
                imageUrl={category.imageUrl}
                link={category.link}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Highlighted Features Section */}
      <section id="featured" className="py-16 md:py-20 lg:py-24 bg-gradient-to-br from-background to-muted/20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4 mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground">
              Why Learn With Us
            </h2>
            <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
              We're committed to providing the best learning experience with
              flexible pacing, expert instructors, and real-world projects.
            </p>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {highlightedSections.map((section) => (
              <HighlightedSection
                key={section.id}
                title={section.title}
                description={section.description}
                icon={section.icon}
              />
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 md:py-20 lg:py-24 bg-primary text-primary-foreground">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-8">
            <div className="space-y-4">
              <h2 className="text-3xl sm:text-4xl font-bold">
                Ready to Start Your Journey?
              </h2>
              <p className="text-lg max-w-2xl mx-auto opacity-90">
                Join our community of learners and start building the skills
                you need for a successful tech career.
              </p>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/categories"
                className="bg-white text-primary px-8 py-3 rounded-full font-semibold hover:bg-white/90 transition-colors duration-300"
              >
                Browse All Courses
              </a>
              <a
                href="/signup"
                className="border-2 border-white text-white px-8 py-3 rounded-full font-semibold hover:bg-white hover:text-primary transition-colors duration-300"
              >
                Create Free Account
              </a>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

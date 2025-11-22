import { LandingHero } from "@/components/LandingHero";
import { FeaturedCategories } from "@/components/FeaturedCategories";
import { BenefitsSection } from "@/components/BenefitsSection";
import { mockCourseCategories, platformBenefits, heroSectionData } from "@/lib/mock-courses";

export function HomepageContent() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <LandingHero heroData={heroSectionData} />

      {/* Featured Categories Section */}
      <FeaturedCategories categories={mockCourseCategories} />

      {/* Benefits Section */}
      <BenefitsSection benefits={platformBenefits} />
    </div>
  );
}

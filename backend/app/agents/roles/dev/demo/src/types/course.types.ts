/**
 * Course-related TypeScript interfaces and types
 */

/**
 * Course category interface
 */
export interface CourseCategory {
  id: string;
  title: string;
  description: string;
  imageUrl: string;
  slug: string;
  color: string;
  icon: string;
  featured: boolean;
  courseCount: number;
}

/**
 * Platform benefit interface
 */
export interface Benefit {
  id: string;
  title: string;
  description: string;
  icon: string;
}

/**
 * Hero section interface
 */
export interface HeroSection {
  title: string;
  subtitle: string;
  description: string;
  ctaText: string;
  ctaLink: string;
}

import * as React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { FeaturedCategories } from "@/components/FeaturedCategories";
import { mockCourseCategories } from "@/lib/mock-courses";


// Mock Link component
jest.mock("next/link", () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => {
    return <a href={href}>{children}</a>;
  };
});

// Mock CategoryCard component
jest.mock("@/components/CategoryCard", () => {
  return ({ category, onClick }: any) => {
    return (
      <div data-testid="category-card" onClick={onClick}>
        <span>{category.title}</span>
        <button>Explore</button>
      </div>
    );
  };
});

describe("FeaturedCategories", () => {
  it("renders section with default title and subtitle", () => {
    render(<FeaturedCategories categories={mockCourseCategories} />);
    
    expect(screen.getByText("Popular Categories")).toBeInTheDocument();
    expect(screen.getByText("Explore our most popular course categories and start learning today")).toBeInTheDocument();
  });

  it("renders section with custom title and subtitle", () => {
    render(
      <FeaturedCategories 
        categories={mockCourseCategories}
        title="Featured Course Categories"
        subtitle="Discover amazing courses to boost your career"
      />
    );
    
    expect(screen.getByText("Featured Course Categories")).toBeInTheDocument();
    expect(screen.getByText("Discover amazing courses to boost your career")).toBeInTheDocument();
    expect(screen.queryByText("Popular Categories")).not.toBeInTheDocument();
  });

  it("displays only featured categories", () => {
    render(<FeaturedCategories categories={mockCourseCategories} />);
    
    // Count featured categories
    const featuredCount = mockCourseCategories.filter(cat => cat.featured).length;
    const categoryCards = screen.getAllByTestId("category-card");
    expect(categoryCards.length).toBe(featuredCount);
    
    // Verify only featured categories are shown
    mockCourseCategories.forEach((category) => {
      const card = screen.queryByText(category.title);
      if (category.featured) {
        expect(card).toBeInTheDocument();
      } else {
        expect(card).not.toBeInTheDocument();
      }
    });
  });

  it("renders view all courses button", () => {
    render(<FeaturedCategories categories={mockCourseCategories} />);
    
    const button = screen.getByRole("link", { name: /view all courses/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute("href", "/courses");
  });

  it("has proper semantic structure", () => {
    render(<FeaturedCategories categories={mockCourseCategories} />);
    
    // Check for proper heading hierarchy
    const h2 = screen.getByRole("heading", { level: 2 });
    expect(h2).toBeInTheDocument();
    expect(h2).toHaveTextContent("Popular Categories");
  });

  it("applies correct CSS classes", () => {
    render(<FeaturedCategories categories={mockCourseCategories} />);
    
    const section = screen.getByRole("region");
    expect(section).toHaveClass("py-16");
  });

  it("handles empty categories array", () => {
    render(<FeaturedCategories categories={[]} />);
    
    expect(screen.getByText("Popular Categories")).toBeInTheDocument();
    expect(screen.getByText("Explore our most popular course categories and start learning today")).toBeInTheDocument();
    
    // Should not display any category cards
    expect(screen.queryByTestId("category-card")).not.toBeInTheDocument();
    
    // Button should still be present
    expect(screen.getByRole("link", { name: /view all courses/i })).toBeInTheDocument();
  });

  it("handles categories array with no featured items", () => {
    const categoriesWithoutFeatured = mockCourseCategories.map(cat => ({
      ...cat,
      featured: false
    }));
    
    render(<FeaturedCategories categories={categoriesWithoutFeatured} />);
    
    expect(screen.getByText("Popular Categories")).toBeInTheDocument();
    
    // Should not display any category cards
    expect(screen.queryByTestId("category-card")).not.toBeInTheDocument();
  });

  it("passes correct props to CategoryCard", () => {
    render(<FeaturedCategories categories={mockCourseCategories} />);
    
    const featuredCategories = mockCourseCategories.filter(cat => cat.featured);
    const categoryCards = screen.getAllByTestId("category-card");
    
    featuredCategories.forEach((category, index) => {
      expect(categoryCards[index]).toHaveTextContent(category.title);
    });
  });
});
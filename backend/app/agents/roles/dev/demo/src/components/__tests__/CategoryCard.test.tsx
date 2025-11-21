import * as React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { CategoryCard } from "@/components/CategoryCard";
import { CourseCategory } from "@/types/course.types";
import { mockCourseCategories } from "@/lib/mock-courses";
import Link from "next/link";

// Mock Next.js router
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock Link component
jest.mock("next/link", () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => {
    return <a href={href}>{children}</a>;
  };
});

const mockCategory: CourseCategory = mockCourseCategories[0];

describe("CategoryCard", () => {
  it("renders category information correctly", () => {
    render(<CategoryCard category={mockCategory} />);
    
    expect(screen.getByText(mockCategory.title)).toBeInTheDocument();
    expect(screen.getByText(mockCategory.description)).toBeInTheDocument();
    expect(screen.getByText(`${mockCategory.courseCount} courses`)).toBeInTheDocument();
    expect(screen.getByText("Explore")).toBeInTheDocument();
  });

  it("displays the correct icon", () => {
    render(<CategoryCard category={mockCategory} />);
    expect(screen.getByText(mockCategory.icon)).toBeInTheDocument();
  });

  it("has correct navigation link", () => {
    render(<CategoryCard category={mockCategory} />);
    const link = screen.getByRole("link", { name: /explore/i });
    expect(link).toHaveAttribute("href", `/categories/${mockCategory.slug}`);
  });

  it("calls onClick when provided", () => {
    const mockOnClick = jest.fn();
    render(<CategoryCard category={mockCategory} onClick={mockOnClick} />);
    
    const card = screen.getByRole("button");
    fireEvent.click(card);
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it("applies correct CSS classes for styling", () => {
    render(<CategoryCard category={mockCategory} />);
    const card = screen.getByRole("button");
    expect(card).toHaveClass("group", "cursor-pointer", "transition-all", "duration-300");
  });

  it("has proper accessibility attributes", () => {
    render(<CategoryCard category={mockCategory} />);
    const icon = screen.getByText(mockCategory.icon);
    expect(icon).toHaveAttribute("aria-hidden", "true");
  });
});
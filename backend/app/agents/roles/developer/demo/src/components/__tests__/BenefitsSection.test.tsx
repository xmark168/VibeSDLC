import * as React from "react";
import { render, screen } from "@testing-library/react";
import { BenefitsSection } from "@/components/BenefitsSection";
import { platformBenefits } from "@/lib/mock-courses";
import type { Benefit } from "@/types/course.types";

const mockBenefits: Benefit[] = platformBenefits;

describe("BenefitsSection", () => {
  it("renders section with default title", () => {
    render(<BenefitsSection benefits={mockBenefits} />);
    
    expect(screen.getByText("Why Learn With Us")).toBeInTheDocument();
    expect(screen.getByText("Everything you need to succeed in your tech career, all in one place.")).toBeInTheDocument();
  });

  it("renders section with custom title", () => {
    render(<BenefitsSection benefits={mockBenefits} title="Our Platform Benefits" />);
    
    expect(screen.getByText("Our Platform Benefits")).toBeInTheDocument();
    expect(screen.queryByText("Why Learn With Us")).not.toBeInTheDocument();
  });

  it("displays all benefits correctly", () => {
    render(<BenefitsSection benefits={mockBenefits} />);
    
    mockBenefits.forEach((benefit) => {
      expect(screen.getByText(benefit.title)).toBeInTheDocument();
      expect(screen.getByText(benefit.description)).toBeInTheDocument();
      expect(screen.getByText(benefit.icon)).toBeInTheDocument();
    });
  });

  it("has proper semantic structure", () => {
    render(<BenefitsSection benefits={mockBenefits} />);
    
    const section = screen.getByRole("region");
    expect(section).toBeInTheDocument();
    
    // Check for proper heading hierarchy
    const h2 = screen.getByRole("heading", { level: 2 });
    expect(h2).toBeInTheDocument();
    expect(h2).toHaveTextContent("Why Learn With Us");
  });

  it("applies correct CSS classes", () => {
    render(<BenefitsSection benefits={mockBenefits} />);
    
    const section = screen.getByRole("region");
    expect(section).toHaveClass("py-16", "bg-gradient-to-br", "from-background", "to-muted/50");
  });

  it("has proper accessibility for icons", () => {
    render(<BenefitsSection benefits={mockBenefits} />);
    
    mockBenefits.forEach((benefit) => {
      const icon = screen.getByText(benefit.icon);
      expect(icon).toHaveAttribute("aria-hidden", "true");
    });
  });

  it("renders benefits in a grid layout", () => {
    render(<BenefitsSection benefits={mockBenefits} />);
    
    const cards = screen.getAllByRole("region");
    expect(cards.length).toBe(mockBenefits.length);
    
    cards.forEach((card) => {
      expect(card).toHaveClass("text-center", "group", "hover:shadow-lg", "transition-all", "duration-300", "border-0");
    });
  });

  it("handles empty benefits array", () => {
    render(<BenefitsSection benefits={[]} />);
    
    expect(screen.getByText("Why Learn With Us")).toBeInTheDocument();
    expect(screen.getByText("Everything you need to succeed in your tech career, all in one place.")).toBeInTheDocument();
    
    // Should not display any benefit cards
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });
});
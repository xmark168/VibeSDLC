import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import { useState } from "react";

const navItems = [
  { title: "Home", path: "#" },
  { title: "AI Agents", path: "#agents" },
  { title: "Features", path: "#features" },
  { title: "Testimonials", path: "#testimonials" },
];

const scrollToSection = (e: React.MouseEvent<HTMLAnchorElement>, path: string) => {
  e.preventDefault();
  if (path === "#") {
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else {
    const element = document.querySelector(path);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
};

export const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4 md:px-8">
        {/* Logo */}
        <a
          href="#"
          onClick={(e) => scrollToSection(e, "#")}
          className="flex items-center cursor-pointer"
        >
          <img src="/assets/images/logo.png" alt="VibeSDLC" className="h-36 w-36 object-contain" />
          {/* <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary">
            <span className="text-primary-foreground font-bold text-sm">VS</span>
          </div>
          <span className="ml-2 text-lg font-semibold text-foreground">VibeSDLC</span> */}
        </a>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-8">
          {navItems.map((item) => (
            <a
              key={item.path}
              href={item.path}
              onClick={(e) => scrollToSection(e, item.path)}
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground cursor-pointer"
            >
              {item.title}
            </a>
          ))}
        </nav>

        {/* Login Button - Desktop */}
        <div className="hidden md:block">
          <Button variant="default" size="sm" className="rounded-full px-6" asChild>
            <a href="/login">Sign in</a>
          </Button>
        </div>

        <button
          className="md:hidden inline-flex items-center justify-center p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {mobileMenuOpen && (
        <div className="md:hidden border-t bg-background">
          <nav className="container flex flex-col space-y-4 px-4 py-6">
            {navItems.map((item) => (
              <a
                key={item.path}
                href={item.path}
                onClick={(e) => {
                  scrollToSection(e, item.path);
                  setMobileMenuOpen(false);
                }}
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground cursor-pointer"
              >
                {item.title}
              </a>
            ))}
            <Button variant="default" size="sm" className="w-full" asChild>
              <a href="/login">Sign in</a>
            </Button>
          </nav>
        </div>
      )}
    </header>
  );
};

import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
  NavigationMenuTrigger,
  NavigationMenuContent,
  NavigationMenuLink,
} from "@/components/ui/navigation-menu";

export function Navigation() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur-sm">
      <nav className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-primary to-secondary rounded-lg flex items-center justify-center">
                <span className="text-sm font-bold text-primary-foreground">LT</span>
              </div>
              <span className="text-xl font-bold text-foreground">LearnTech</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-8">
            <NavigationMenu>
              <NavigationMenuList>
                <NavigationMenuItem>
                  <NavigationMenuTrigger className="text-foreground hover:text-primary">
                    Categories
                  </NavigationMenuTrigger>
                  <NavigationMenuContent className="md:w-[600px] lg:w-[800px]">
                    <ul className="grid grid-cols-2 md:grid-cols-3 gap-4 p-6">
                      <li>
                        <NavigationMenuLink href="/categories/web-development" className="flex flex-col gap-2">
                          <div className="w-12 h-12 bg-gradient-to-br from-primary to-secondary rounded-lg flex items-center justify-center text-white">🌐</div>
                          <div className="font-medium">Web Development</div>
                          <p className="text-sm text-muted-foreground">React, Vue, Node.js</p>
                        </NavigationMenuLink>
                      </li>
                      <li>
                        <NavigationMenuLink href="/categories/mobile-apps" className="flex flex-col gap-2">
                          <div className="w-12 h-12 bg-gradient-to-br from-secondary to-accent rounded-lg flex items-center justify-center text-white">📱</div>
                          <div className="font-medium">Mobile Apps</div>
                          <p className="text-sm text-muted-foreground">iOS, Android, React Native</p>
                        </NavigationMenuLink>
                      </li>
                      <li>
                        <NavigationMenuLink href="/categories/data-science" className="flex flex-col gap-2">
                          <div className="w-12 h-12 bg-gradient-to-br from-accent to-primary rounded-lg flex items-center justify-center text-white">📊</div>
                          <div className="font-medium">Data Science</div>
                          <p className="text-sm text-muted-foreground">ML, AI, Analytics</p>
                        </NavigationMenuLink>
                      </li>
                      <li>
                        <NavigationMenuLink href="/categories/design" className="flex flex-col gap-2">
                          <div className="w-12 h-12 bg-gradient-to-br from-success to-secondary rounded-lg flex items-center justify-center text-white">🎨</div>
                          <div className="font-medium">UI/UX Design</div>
                          <p className="text-sm text-muted-foreground">Figma, Prototyping</p>
                        </NavigationMenuLink>
                      </li>
                      <li>
                        <NavigationMenuLink href="/categories/cloud-devops" className="flex flex-col gap-2">
                          <div className="w-12 h-12 bg-gradient-to-br from-warning to-primary rounded-lg flex items-center justify-center text-white">☁️</div>
                          <div className="font-medium">Cloud & DevOps</div>
                          <p className="text-sm text-muted-foreground">AWS, Docker, Kubernetes</p>
                        </NavigationMenuLink>
                      </li>
                      <li>
                        <NavigationMenuLink href="/categories/cybersecurity" className="flex flex-col gap-2">
                          <div className="w-12 h-12 bg-gradient-to-br from-destructive to-primary rounded-lg flex items-center justify-center text-white">🔒</div>
                          <div className="font-medium">Cybersecurity</div>
                          <p className="text-sm text-muted-foreground">Security, Ethical Hacking</p>
                        </NavigationMenuLink>
                      </li>
                    </ul>
                  </NavigationMenuContent>
                </NavigationMenuItem>

                <NavigationMenuItem>
                  <NavigationMenuLink href="#featured" className="text-foreground hover:text-primary">
                    Features
                  </NavigationMenuLink>
                </NavigationMenuItem>

                <NavigationMenuItem>
                  <NavigationMenuLink href="#about" className="text-foreground hover:text-primary">
                    About
                  </NavigationMenuLink>
                </NavigationMenuItem>
              </NavigationMenuList>
            </NavigationMenu>
          </div>

          {/* CTA Buttons */}
          <div className="flex items-center gap-4">
            <Button asChild variant="ghost" className="hidden sm:inline-flex text-foreground hover:bg-accent">
              <Link href="/signin">Sign In</Link>
            </Button>
            <Button asChild className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2">
              <Link href="/signup">Get Started</Link>
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}

      </nav>
    </header>
  );
}
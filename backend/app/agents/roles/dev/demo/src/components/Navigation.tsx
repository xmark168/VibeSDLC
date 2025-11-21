"use client";

import * as React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";

export function Navigation() {
  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-8">
            <Link
              href="/"
              className="text-xl font-bold text-foreground"
            >
              LearnTech
            </Link>
            
            <NavigationMenu>
              <NavigationMenuList>
                <NavigationMenuItem>
                  <NavigationMenuTrigger className="text-sm font-medium">
                    Courses
                  </NavigationMenuTrigger>
                  <NavigationMenuContent>
                    <div className="space-y-2 p-4">
                      <NavigationMenuLink asChild>
                        <Link
                          href="/courses"
                          className="block rounded-md px-3 py-2 text-sm font-medium text-foreground hover:bg-accent"
                        >
                          All Courses
                        </Link>
                      </NavigationMenuLink>
                      <NavigationMenuLink asChild>
                        <Link
                          href="/categories"
                          className="block rounded-md px-3 py-2 text-sm font-medium text-foreground hover:bg-accent"
                        >
                          Categories
                        </Link>
                      </NavigationMenuLink>
                    </div>
                  </NavigationMenuContent>
                </NavigationMenuItem>
                
                <NavigationMenuItem>
                  <NavigationMenuLink asChild>
                    <Link
                      href="/about"
                      className="text-sm font-medium text-foreground hover:text-primary"
                    >
                      About
                    </Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
                
                <NavigationMenuItem>
                  <NavigationMenuLink asChild>
                    <Link
                      href="/contact"
                      className="text-sm font-medium text-foreground hover:text-primary"
                    >
                      Contact
                    </Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
              </NavigationMenuList>
            </NavigationMenu>
          </div>
          
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              asChild
            >
              <Link href="/login">Login</Link>
            </Button>
            <Button
              size="sm"
              asChild
            >
              <Link href="/signup">Sign Up</Link>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
}
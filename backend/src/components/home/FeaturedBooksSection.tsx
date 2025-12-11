'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BookCard } from '@/components/ui/BookCard';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ArrowRight, Sparkles } from 'lucide-react';
import Link from 'next/link';

interface Book {
  id: string;
  title: string;
  slug: string;
  price: number;
  originalPrice?: number | null;
  coverImage?: string | null;
  author?: {
    name: string;
  } | null;
  category?: {
    name: string;
  } | null;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  },
};

function BookCardSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="aspect-[3/4] w-full rounded-xl" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-1/2" />
      <Skeleton className="h-5 w-1/3" />
    </div>
  );
}

export function FeaturedBooksSection() {
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/books/featured')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch featured books');
        return res.json();
      })
      .then((data) => {
        if (data.success) {
          setBooks(data.data ?? []);
        } else {
          setError(data.error ?? 'Failed to load featured books');
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load featured books');
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <section className="relative py-16 md:py-24 overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-amber-200/20 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-rose-200/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12 md:mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-100 text-amber-800 text-sm font-medium mb-4">
            <Sparkles className="w-4 h-4" />
            <span>Curated Selection</span>
          </div>
          
          <h2 className="font-serif text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-4">
            Featured Books
          </h2>
          
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Discover our handpicked collection of exceptional reads, chosen by our literary experts for their brilliance and impact.
          </p>
        </motion.div>

        {/* Error State */}
        {error && (
          <Alert variant="destructive" className="max-w-md mx-auto mb-8">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6 lg:gap-8">
            {Array.from({ length: 8 }).map((_, i) => (
              <BookCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Books Grid */}
        {!isLoading && !error && books.length > 0 && (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: '-50px' }}
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6 lg:gap-8"
          >
            {books.slice(0, 12).map((book) => (
              <motion.div key={book.id} variants={itemVariants}>
                <BookCard book={book} variant="featured" />
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* Empty State */}
        {!isLoading && !error && books.length === 0 && (
          <div className="text-center py-12">
            <p className="text-muted-foreground text-lg">No featured books available at the moment.</p>
          </div>
        )}

        {/* View All Button */}
        {!isLoading && books.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="text-center mt-12"
          >
            <Button
              asChild
              size="lg"
              variant="outline"
              className="group rounded-full px-8 border-2 hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all duration-300"
            >
              <Link href="/books">
                Browse All Books
                <ArrowRight className="ml-2 w-4 h-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </Button>
          </motion.div>
        )}
      </div>
    </section>
  );
}
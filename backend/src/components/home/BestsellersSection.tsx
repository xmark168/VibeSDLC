'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BookCard } from '@/components/ui/BookCard';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, Flame } from 'lucide-react';

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

function BestsellersSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="space-y-3">
          <Skeleton className="aspect-[3/4] w-full rounded-xl" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-5 w-1/3" />
        </div>
      ))}
    </div>
  );
}

export function BestsellersSection() {
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/books?sortBy=bestselling&limit=10')
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setBooks(data.data ?? []);
        } else {
          setError(data.error ?? 'Failed to load bestsellers');
        }
      })
      .catch(() => setError('Failed to load bestsellers'))
      .finally(() => setIsLoading(false));
  }, []);

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
    hidden: { opacity: 0, y: 30, scale: 0.95 },
    show: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: {
        type: 'spring',
        stiffness: 100,
        damping: 15,
      },
    },
  };

  return (
    <section className="relative py-20 md:py-28 overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-gradient-to-b from-amber-50/30 via-transparent to-rose-50/20 pointer-events-none" />
      <div 
        className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-300/50 to-transparent" 
      />
      <div 
        className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-rose-300/50 to-transparent" 
      />
      
      {/* Decorative elements */}
      <div className="absolute top-20 left-10 w-72 h-72 bg-amber-200/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-rose-200/20 rounded-full blur-3xl pointer-events-none" />

      <div className="container mx-auto px-4 relative">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12 md:mb-16"
        >
          <div className="inline-flex items-center gap-2 mb-4">
            <Badge 
              variant="secondary" 
              className="bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 border-amber-200/50 px-4 py-1.5 text-sm font-medium"
            >
              <Flame className="w-4 h-4 mr-1.5 text-orange-500" />
              Hot Right Now
            </Badge>
          </div>
          
          <h2 className="font-serif text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-4">
            <span className="bg-gradient-to-r from-amber-700 via-orange-600 to-rose-600 bg-clip-text text-transparent">
              Bestsellers
            </span>
          </h2>
          
          <p className="text-muted-foreground text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
            Discover the books everyone&apos;s talking about. Our most loved titles, 
            handpicked by thousands of readers.
          </p>
          
          <div className="flex items-center justify-center gap-2 mt-6 text-sm text-muted-foreground">
            <TrendingUp className="w-4 h-4 text-green-500" />
            <span>Updated weekly based on sales</span>
          </div>
        </motion.div>

        {/* Content */}
        {error && (
          <Alert variant="destructive" className="max-w-md mx-auto mb-8">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <BestsellersSkeleton />
        ) : books.length > 0 ? (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: '-50px' }}
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6"
          >
            {books.map((book, index) => (
              <motion.div
                key={book.id}
                variants={itemVariants}
                className="relative"
              >
                {/* Rank badge for top 3 */}
                {index < 3 && (
                  <div 
                    className={`absolute -top-2 -left-2 z-10 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shadow-lg ${
                      index === 0 
                        ? 'bg-gradient-to-br from-yellow-400 to-amber-500 text-amber-900' 
                        : index === 1 
                          ? 'bg-gradient-to-br from-gray-300 to-gray-400 text-gray-700' 
                          : 'bg-gradient-to-br from-amber-600 to-amber-700 text-amber-100'
                    }`}
                  >
                    {index + 1}
                  </div>
                )}
                <BookCard book={book} variant="default" />
              </motion.div>
            ))}
          </motion.div>
        ) : (
          <div className="text-center py-16">
            <p className="text-muted-foreground text-lg">No bestsellers available at the moment.</p>
          </div>
        )}
      </div>
    </section>
  );
}
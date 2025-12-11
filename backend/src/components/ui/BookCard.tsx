'use client';

import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ShoppingCart, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface BookCardProps {
  book: {
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
  };
  variant?: 'default' | 'compact' | 'featured';
  className?: string;
}

export function BookCard({ book, variant = 'default', className }: BookCardProps) {
  const discountPercentage = book.originalPrice
    ? Math.round(((book.originalPrice - book.price) / book.originalPrice) * 100)
    : 0;

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(price);
  };

  if (variant === 'compact') {
    return (
      <Link href={`/books/${book.slug}`} className={cn('group block', className)}>
        <motion.div
          whileHover={{ y: -4 }}
          transition={{ duration: 0.2 }}
          className="flex gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors"
        >
          <div className="relative w-16 h-24 flex-shrink-0 rounded overflow-hidden bg-muted">
            {book.coverImage ? (
              <Image
                src={book.coverImage}
                alt={book.title}
                fill
                className="object-cover"
                sizes="64px"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-amber-100 to-orange-200">
                <span className="text-2xl font-serif text-amber-800">
                  {book.title.charAt(0)}
                </span>
              </div>
            )}
          </div>
          <div className="flex flex-col justify-center min-w-0">
            <h4 className="font-medium text-sm line-clamp-2 group-hover:text-primary transition-colors">
              {book.title}
            </h4>
            {book.author && (
              <p className="text-xs text-muted-foreground mt-0.5 truncate">
                {book.author.name}
              </p>
            )}
            <p className="text-sm font-semibold text-primary mt-1">
              {formatPrice(book.price)}
            </p>
          </div>
        </motion.div>
      </Link>
    );
  }

  if (variant === 'featured') {
    return (
      <Link href={`/books/${book.slug}`} className={cn('group block', className)}>
        <motion.div
          whileHover={{ y: -8 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        >
          <Card className="overflow-hidden border-0 shadow-lg hover:shadow-2xl transition-shadow duration-300 bg-gradient-to-b from-card to-card/80">
            <div className="relative aspect-[3/4] overflow-hidden">
              {book.coverImage ? (
                <Image
                  src={book.coverImage}
                  alt={book.title}
                  fill
                  className="object-cover transition-transform duration-500 group-hover:scale-110"
                  sizes="(max-width: 768px) 50vw, 25vw"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-amber-50 via-orange-100 to-rose-100">
                  <span className="text-6xl font-serif text-amber-700/60">
                    {book.title.charAt(0)}
                  </span>
                </div>
              )}
              
              {/* Overlay gradient */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              
              {/* Discount badge */}
              {discountPercentage > 0 && (
                <Badge className="absolute top-3 left-3 bg-rose-500 hover:bg-rose-600 text-white font-bold">
                  -{discountPercentage}%
                </Badge>
              )}
              
              {/* Category badge */}
              {book.category && (
                <Badge variant="secondary" className="absolute top-3 right-3 backdrop-blur-sm bg-white/80">
                  {book.category.name}
                </Badge>
              )}
              
              {/* Quick actions */}
              <div className="absolute bottom-3 left-3 right-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-2 group-hover:translate-y-0">
                <Button size="sm" className="flex-1 bg-white text-foreground hover:bg-white/90">
                  <ShoppingCart className="w-4 h-4 mr-1" />
                  Add to Cart
                </Button>
                <Button size="icon" variant="secondary" className="bg-white/80 hover:bg-white">
                  <Heart className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            <CardContent className="p-4">
              <h3 className="font-semibold text-lg line-clamp-1 group-hover:text-primary transition-colors">
                {book.title}
              </h3>
              {book.author && (
                <p className="text-sm text-muted-foreground mt-1">
                  by {book.author.name}
                </p>
              )}
              <div className="flex items-center gap-2 mt-3">
                <span className="text-xl font-bold text-primary">
                  {formatPrice(book.price)}
                </span>
                {book.originalPrice && book.originalPrice > book.price && (
                  <span className="text-sm text-muted-foreground line-through">
                    {formatPrice(book.originalPrice)}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </Link>
    );
  }

  // Default variant
  return (
    <Link href={`/books/${book.slug}`} className={cn('group block', className)}>
      <motion.div
        whileHover={{ y: -6 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
      >
        <Card className="overflow-hidden border hover:border-primary/30 transition-all duration-300 hover:shadow-xl">
          <div className="relative aspect-[2/3] overflow-hidden bg-muted">
            {book.coverImage ? (
              <Image
                src={book.coverImage}
                alt={book.title}
                fill
                className="object-cover transition-transform duration-400 group-hover:scale-105"
                sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-100 via-amber-50 to-orange-100">
                <div className="text-center">
                  <span className="text-5xl font-serif text-amber-700/50 block">
                    {book.title.charAt(0)}
                  </span>
                  <span className="text-xs text-muted-foreground mt-2 block px-4 line-clamp-2">
                    {book.title}
                  </span>
                </div>
              </div>
            )}
            
            {/* Discount badge */}
            {discountPercentage > 0 && (
              <Badge className="absolute top-2 left-2 bg-rose-500 hover:bg-rose-600 text-white text-xs font-bold px-2 py-0.5">
                {discountPercentage}% OFF
              </Badge>
            )}
            
            {/* Wishlist button */}
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              className="absolute top-2 right-2 w-8 h-8 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-md hover:bg-white"
              onClick={(e) => {
                e.preventDefault();
                // Wishlist functionality
              }}
            >
              <Heart className="w-4 h-4 text-muted-foreground hover:text-rose-500 transition-colors" />
            </motion.button>
          </div>
          
          <CardContent className="p-3">
            {book.category && (
              <span className="text-xs text-muted-foreground uppercase tracking-wide">
                {book.category.name}
              </span>
            )}
            <h3 className="font-medium text-sm mt-1 line-clamp-2 min-h-[2.5rem] group-hover:text-primary transition-colors">
              {book.title}
            </h3>
            {book.author && (
              <p className="text-xs text-muted-foreground mt-1 truncate">
                {book.author.name}
              </p>
            )}
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-lg font-bold text-primary">
                {formatPrice(book.price)}
              </span>
              {book.originalPrice && book.originalPrice > book.price && (
                <span className="text-xs text-muted-foreground line-through">
                  {formatPrice(book.originalPrice)}
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </Link>
  );
}
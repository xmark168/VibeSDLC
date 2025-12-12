'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Sparkles, Clock, ArrowRight, Percent, Gift, Zap } from 'lucide-react';
import Link from 'next/link';

interface Promotion {
  id: string;
  title: string;
  description: string;
  discountPercent: number;
  code: string | null;
  validFrom: string;
  validUntil: string;
  isActive: boolean;
}

const promotionIcons = [Sparkles, Percent, Gift, Zap];
const promotionGradients = [
  'from-amber-500/20 via-orange-500/10 to-red-500/20',
  'from-emerald-500/20 via-teal-500/10 to-cyan-500/20',
  'from-violet-500/20 via-purple-500/10 to-fuchsia-500/20',
  'from-rose-500/20 via-pink-500/10 to-red-500/20',
];

const accentColors = [
  'text-amber-600 dark:text-amber-400',
  'text-emerald-600 dark:text-emerald-400',
  'text-violet-600 dark:text-violet-400',
  'text-rose-600 dark:text-rose-400',
];

const badgeVariants = [
  'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300',
  'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300',
  'bg-violet-100 text-violet-800 dark:bg-violet-900/50 dark:text-violet-300',
  'bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300',
];

function formatTimeRemaining(validUntil: string): string {
  const now = new Date();
  const end = new Date(validUntil);
  const diff = end.getTime() - now.getTime();
  
  if (diff <= 0) return 'Expired';
  
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  
  if (days > 0) return `${days}d ${hours}h left`;
  if (hours > 0) return `${hours}h left`;
  return 'Ending soon';
}

function PromotionCardSkeleton() {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <Skeleton className="h-12 w-12 rounded-xl flex-shrink-0" />
          <div className="flex-1 space-y-3">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function PromotionsSection() {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/promotions?active=true&limit=4')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setPromotions(data.data ?? []);
        } else {
          setError(data.error ?? 'Failed to load promotions');
        }
      })
      .catch(() => setError('Failed to load promotions'))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <section className="py-16 md:py-24">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <Skeleton className="h-8 w-64 mx-auto mb-4" />
            <Skeleton className="h-5 w-96 mx-auto" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[...Array(4)].map((_, i) => (
              <PromotionCardSkeleton key={i} />
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="py-16 md:py-24">
        <div className="container mx-auto px-4">
          <Alert variant="destructive" className="max-w-md mx-auto">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      </section>
    );
  }

  if (promotions.length === 0) {
    return null;
  }

  return (
    <section className="py-16 md:py-24 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-gradient-to-b from-muted/30 via-transparent to-muted/30 pointer-events-none" />
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-3xl pointer-events-none" />
      
      <div className="container mx-auto px-4 relative">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary mb-4">
            <Sparkles className="h-4 w-4" />
            <span className="text-sm font-medium tracking-wide uppercase">Special Offers</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Don&apos;t Miss Out
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Exclusive deals and limited-time offers on your favorite books
          </p>
        </motion.div>

        {/* Promotions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {promotions.map((promotion, index) => {
            const IconComponent = promotionIcons[index % promotionIcons.length];
            const gradient = promotionGradients[index % promotionGradients.length];
            const accentColor = accentColors[index % accentColors.length];
            const badgeColor = badgeVariants[index % badgeVariants.length];
            
            return (
              <motion.div
                key={promotion.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className={`group relative overflow-hidden border-2 hover:border-primary/30 transition-all duration-300 bg-gradient-to-br ${gradient}`}>
                  {/* Hover effect overlay */}
                  <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  
                  <CardContent className="p-6 relative">
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className={`flex-shrink-0 p-3 rounded-xl bg-background/80 backdrop-blur-sm shadow-sm ${accentColor}`}>
                        <IconComponent className="h-6 w-6" />
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <h3 className="font-semibold text-lg leading-tight">
                            {promotion.title}
                          </h3>
                          <Badge className={`flex-shrink-0 ${badgeColor} border-0`}>
                            {promotion.discountPercent}% OFF
                          </Badge>
                        </div>
                        
                        <p className="text-muted-foreground text-sm mb-4 line-clamp-2">
                          {promotion.description}
                        </p>
                        
                        <div className="flex flex-wrap items-center gap-3">
                          {promotion.code && (
                            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-background/80 backdrop-blur-sm border border-dashed border-primary/30">
                              <span className="text-xs text-muted-foreground">Code:</span>
                              <span className="font-mono font-semibold text-sm">{promotion.code}</span>
                            </div>
                          )}
                          
                          <div className="inline-flex items-center gap-1.5 text-muted-foreground text-sm">
                            <Clock className="h-3.5 w-3.5" />
                            <span>{formatTimeRemaining(promotion.validUntil)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}n        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="text-center mt-10"
        >
          <Button asChild variant="outline" size="lg" className="group">
            <Link href="/books">
              Shop All Deals
              <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Link>
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
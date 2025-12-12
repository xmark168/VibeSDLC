import { HeroSection } from '@/components/home/HeroSection';
import { FeaturedBooksSection } from '@/components/home/FeaturedBooksSection';
import { PromotionsSection } from '@/components/home/PromotionsSection';
import { BestsellersSection } from '@/components/home/BestsellersSection';

export default function HomePage() {
  return (
    <main className="min-h-screen">
      {/* Hero Section - Full viewport height with atmospheric design */}
      <HeroSection />
      
      {/* Featured Books - Curated selection with elegant grid */}
      <FeaturedBooksSection />
      
      {/* Promotions - Active deals and special offers */}
      <PromotionsSection />
      
      {/* Bestsellers - Top selling books with trending indicators */}
      <BestsellersSection />
      
      {/* Newsletter Section */}
      <section className="relative py-20 md:py-28 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-amber-50 via-orange-50/50 to-rose-50" />
        
        {/* Decorative elements */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-300/30 to-transparent" />
        <div className="absolute -top-32 -right-32 w-96 h-96 bg-amber-200/30 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-rose-200/30 rounded-full blur-3xl pointer-events-none" />
        
        <div className="container mx-auto px-4 relative">
          <div className="max-w-2xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/70 backdrop-blur-sm border border-amber-200/50 text-amber-800 text-sm font-medium mb-6 shadow-sm">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span>Stay Updated</span>
            </div>
            
            <h2 className="font-serif text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-stone-900 mb-4">
              Join Our
              <span className="block bg-gradient-to-r from-amber-600 via-orange-500 to-rose-500 bg-clip-text text-transparent">
                Reading Community
              </span>
            </h2>
            
            <p className="text-stone-600 text-lg mb-8 leading-relaxed">
              Subscribe to receive personalized book recommendations, exclusive deals, 
              and early access to new releases delivered straight to your inbox.
            </p>
            
            <form className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-5 py-3.5 rounded-full border border-amber-200/50 bg-white/80 backdrop-blur-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400/50 focus:border-amber-300 transition-all shadow-sm"
              />
              <button
                type="submit"
                className="px-8 py-3.5 rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 text-white font-semibold hover:from-amber-600 hover:via-orange-600 hover:to-rose-600 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0"
              >
                Subscribe
              </button>
            </form>
            
            <p className="text-stone-500 text-sm mt-4">
              No spam, unsubscribe anytime. Read our{' '}
              <a href="/privacy" className="text-amber-600 hover:text-amber-700 underline underline-offset-2">
                Privacy Policy
              </a>
            </p>
          </div>
        </div>
      </section>
      
      {/* Footer spacer for visual balance */}
      <div className="h-8 bg-gradient-to-b from-rose-50/50 to-transparent" />
    </main>
  );
}
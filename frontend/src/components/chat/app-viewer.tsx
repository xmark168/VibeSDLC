
import { Button } from "@/components/ui/button"

export function AppViewer() {
  return (
    <div className="flex-1 overflow-auto bg-background">
      <div className="max-w-6xl mx-auto p-12">
        <div className="text-center space-y-6">
          <div className="flex justify-between items-start mb-8">
            <h1 className="text-3xl font-bold text-foreground">Costume T-Shirt Shop</h1>
            <Button variant="outline" className="text-sm bg-transparent">
              Browse Catalog
            </Button>
          </div>

          <div className="space-y-4">
            <h2 className="text-6xl font-bold text-primary leading-tight">Wear the character.</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Premium costume-themed T-shirts. Find your character and wear the look.
            </p>
          </div>

          <div className="flex gap-4 justify-center mt-8">
            <Button className="px-8 py-6 text-lg">Shop Now</Button>
            <Button variant="outline" className="px-8 py-6 text-lg bg-transparent">
              View Cart
            </Button>
          </div>

          <div className="mt-16">
            <h3 className="text-2xl font-bold text-foreground mb-8">Featured Tees</h3>
            <div className="bg-card rounded-lg overflow-hidden border">
              <img
                src="/assets/images/demo-app-viewer.jpg"
                alt="Featured design"
                className="w-full h-[400px] object-cover"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

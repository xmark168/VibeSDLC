import { createFileRoute } from '@tanstack/react-router'
import { Building2, Target, Users, Award } from 'lucide-react'

export const Route = createFileRoute('/_public/about-us')({
  component: AboutUs,
})

function AboutUs() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-16 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            About VibeSDLC
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Revolutionizing software development with AI-powered collaboration
          </p>
        </div>

        {/* Mission Section */}
        <div className="grid md:grid-cols-2 gap-8 mb-16">
          <div className="bg-card p-8 rounded-lg border shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Target className="w-8 h-8 text-primary" />
              <h2 className="text-2xl font-semibold">Our Mission</h2>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              We aim to transform the software development lifecycle by integrating intelligent AI agents that work seamlessly with development teams. Our platform empowers developers to focus on creativity and innovation while AI handles repetitive tasks and provides intelligent assistance.
            </p>
          </div>

          <div className="bg-card p-8 rounded-lg border shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Award className="w-8 h-8 text-primary" />
              <h2 className="text-2xl font-semibold">Our Vision</h2>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              To create a future where AI and human developers collaborate harmoniously, making software development more efficient, accessible, and enjoyable. We envision a world where technology barriers are lowered, enabling everyone to bring their ideas to life.
            </p>
          </div>
        </div>

        {/* Values */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center mb-12">Our Core Values</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-card p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <Users className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Collaboration</h3>
              <p className="text-muted-foreground">
                We believe in the power of teamwork between humans and AI to achieve extraordinary results.
              </p>
            </div>

            <div className="bg-card p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <Building2 className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Innovation</h3>
              <p className="text-muted-foreground">
                Constantly pushing boundaries to bring cutting-edge AI technology to software development.
              </p>
            </div>

            <div className="bg-card p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <Target className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Excellence</h3>
              <p className="text-muted-foreground">
                Committed to delivering high-quality solutions that exceed expectations.
              </p>
            </div>
          </div>
        </div>

        {/* Story */}
        <div className="bg-card p-8 rounded-lg border shadow-sm">
          <h2 className="text-3xl font-bold mb-6">Our Story</h2>
          <div className="space-y-4 text-muted-foreground leading-relaxed">
            <p>
              VibeSDLC was born from a simple observation: software development teams spend countless hours on repetitive tasks, 
              documentation, and coordination that could be automated or augmented with AI.
            </p>
            <p>
              Founded by a team of experienced software engineers and AI researchers, we set out to create a platform that 
              brings the best of both worlds together. Our AI agents are designed to understand context, learn from your team's 
              patterns, and provide intelligent assistance throughout the entire development lifecycle.
            </p>
            <p>
              Today, VibeSDLC serves development teams worldwide, helping them ship better software faster while maintaining 
              quality and fostering innovation. We continue to evolve our platform based on user feedback and the latest 
              advancements in AI technology.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { ChevronDown, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'

export const Route = createFileRoute('/_public/faqs')({
  component: FAQs,
})

const faqData = [
  {
    category: 'Getting Started',
    questions: [
      {
        q: 'What is VibeSDLC?',
        a: 'VibeSDLC is an AI-powered software development lifecycle platform that helps teams collaborate more efficiently by providing intelligent AI agents for various development roles including team leaders, developers, business analysts, and testers.',
      },
      {
        q: 'How do I create my first project?',
        a: 'After signing up and logging in, click on "New Project" button in your dashboard. Choose a tech stack, configure your AI agents, and you\'re ready to start! The platform will guide you through the setup process.',
      },
      {
        q: 'What tech stacks are supported?',
        a: 'VibeSDLC supports various tech stacks including Node.js with React, Next.js, Python with FastAPI, and more. You can select your preferred stack during project creation.',
      },
    ],
  },
  {
    category: 'AI Agents',
    questions: [
      {
        q: 'What are AI agents?',
        a: 'AI agents are intelligent assistants that take on specific roles in your development team. Each agent (Team Leader, Developer, Business Analyst, Tester) has specialized knowledge and can help with tasks related to their role.',
      },
      {
        q: 'Can I customize AI agent personas?',
        a: 'Yes! You can create custom personas for each agent role with specific communication styles, expertise levels, and behavior patterns to match your team\'s needs.',
      },
      {
        q: 'How many AI agents can I have per project?',
        a: 'The number of agents depends on your subscription plan. Free plan includes basic agents, while premium plans offer more agents and advanced features.',
      },
    ],
  },
  {
    category: 'Subscription & Billing',
    questions: [
      {
        q: 'What subscription plans are available?',
        a: 'We offer Free, Pro, and Enterprise plans. Free plan includes basic features and limited credits. Pro plan offers more projects, credits, and advanced features. Enterprise plan provides custom solutions for large teams.',
      },
      {
        q: 'How does the credit system work?',
        a: 'Credits are used for AI agent interactions and computations. Each plan comes with monthly credits. You can monitor your usage in the dashboard and upgrade your plan if needed.',
      },
      {
        q: 'Can I upgrade or downgrade my plan?',
        a: 'Yes, you can upgrade or downgrade your plan at any time from your account settings. Changes take effect immediately for upgrades, and at the end of the billing cycle for downgrades.',
      },
    ],
  },
  {
    category: 'Security & Privacy',
    questions: [
      {
        q: 'Is my code and data secure?',
        a: 'Yes, we take security seriously. All data is encrypted in transit and at rest. We use industry-standard security practices and never share your code or data with third parties.',
      },
      {
        q: 'Do you support two-factor authentication (2FA)?',
        a: 'Yes, we strongly recommend enabling 2FA for your account. You can set it up in your account security settings using any TOTP-compatible authenticator app.',
      },
      {
        q: 'Where is my data stored?',
        a: 'Your data is stored in secure cloud infrastructure with automatic backups. You maintain full ownership of your code and can export it at any time.',
      },
    ],
  },
  {
    category: 'Technical Support',
    questions: [
      {
        q: 'What if I encounter a bug or issue?',
        a: 'Please report any bugs through our support channel at vibesdlc@gmail.com or through the feedback form in your dashboard. Our team will investigate and respond promptly.',
      },
      {
        q: 'Do you provide integration support?',
        a: 'Yes, we provide documentation and support for integrating VibeSDLC with your existing tools and workflows. Enterprise plan includes dedicated integration support.',
      },
      {
        q: 'How can I get help if I\'m stuck?',
        a: 'You can access our documentation, watch tutorial videos, or contact our support team. Pro and Enterprise users get priority support with faster response times.',
      },
    ],
  },
]

function FAQs() {
  const [searchQuery, setSearchQuery] = useState('')
  const [openItems, setOpenItems] = useState<Record<string, boolean>>({})

  const toggleItem = (key: string) => {
    setOpenItems(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const filteredFaqs = faqData.map(category => ({
    ...category,
    questions: category.questions.filter(
      item =>
        item.q.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.a.toLowerCase().includes(searchQuery.toLowerCase())
    ),
  })).filter(category => category.questions.length > 0)

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-16 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Frequently Asked Questions
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
            Find answers to common questions about VibeSDLC
          </p>

          {/* Search */}
          <div className="relative max-w-md mx-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search questions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* FAQ Categories */}
        <div className="space-y-8">
          {filteredFaqs.map((category) => (
            <div key={category.category}>
              <h2 className="text-2xl font-semibold mb-4">{category.category}</h2>
              <div className="space-y-2">
                {category.questions.map((item, index) => {
                  const key = `${category.category}-${index}`
                  const isOpen = openItems[key]

                  return (
                    <div key={key} className="bg-card rounded-lg border shadow-sm overflow-hidden">
                      <button
                        onClick={() => toggleItem(key)}
                        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-muted/50 transition-colors"
                      >
                        <span className="font-medium pr-4">{item.q}</span>
                        <ChevronDown
                          className={`w-5 h-5 text-muted-foreground flex-shrink-0 transition-transform ${
                            isOpen ? 'rotate-180' : ''
                          }`}
                        />
                      </button>
                      {isOpen && (
                        <div className="px-6 py-4 border-t bg-muted/20">
                          <p className="text-muted-foreground leading-relaxed">{item.a}</p>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {filteredFaqs.length === 0 && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No questions found matching your search.</p>
          </div>
        )}

        {/* Contact Section */}
        <div className="mt-16 bg-card p-8 rounded-lg border shadow-sm text-center">
          <h3 className="text-xl font-semibold mb-2">Still have questions?</h3>
          <p className="text-muted-foreground mb-4">
            Can't find the answer you're looking for? Please contact our support team.
          </p>
          <a
            href="mailto:vibesdlc@gmail.com"
            className="inline-flex items-center justify-center px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Contact Support
          </a>
        </div>
      </div>
    </div>
  )
}

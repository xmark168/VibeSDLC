import { createFileRoute } from '@tanstack/react-router'
import { Mail, MapPin, Phone, Linkedin, Twitter, Github } from 'lucide-react'

export const Route = createFileRoute('/_public/company')({
  component: Company,
})

function Company() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 pb-16 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Company Information
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Get in touch with us and learn more about VibeSDLC
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Contact Information */}
          <div className="space-y-6">
            <div className="bg-card p-8 rounded-lg border shadow-sm">
              <h2 className="text-2xl font-semibold mb-6">Contact Us</h2>
              <div className="space-y-4">
                <div className="flex items-start gap-4">
                  <MapPin className="w-5 h-5 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <p className="font-medium mb-1">Address</p>
                    <p className="text-muted-foreground">
                      FPT University<br />
                      Hoa Lac, Ha Noi City<br />
                      Vietnam
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <Mail className="w-5 h-5 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <p className="font-medium mb-1">Email</p>
                    <a href="mailto:vibesdlc@gmail.com" className="text-primary hover:underline">
                      vibesdlc@gmail.com
                    </a>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <Phone className="w-5 h-5 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <p className="font-medium mb-1">Phone</p>
                    <a href="tel:+84911524396" className="text-primary hover:underline">
                      +84 911 524 396
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Social Media */}
            <div className="bg-card p-8 rounded-lg border shadow-sm">
              <h2 className="text-2xl font-semibold mb-6">Follow Us</h2>
              <div className="flex gap-4">
                <a
                  href="https://twitter.com/vibesdlc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center hover:bg-primary/20 transition-colors"
                >
                  <Twitter className="w-5 h-5 text-primary" />
                </a>
                <a
                  href="https://linkedin.com/company/vibesdlc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center hover:bg-primary/20 transition-colors"
                >
                  <Linkedin className="w-5 h-5 text-primary" />
                </a>
                <a
                  href="https://github.com/vibesdlc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center hover:bg-primary/20 transition-colors"
                >
                  <Github className="w-5 h-5 text-primary" />
                </a>
              </div>
            </div>
          </div>

          {/* Company Details */}
          <div className="bg-card p-8 rounded-lg border shadow-sm">
            <h2 className="text-2xl font-semibold mb-6">Company Details</h2>
            <div className="space-y-4">
              <div>
                <p className="font-medium text-muted-foreground mb-1">Legal Name</p>
                <p className="text-lg">VibeSDLC Technology Co., Ltd.</p>
              </div>

              <div>
                <p className="font-medium text-muted-foreground mb-1">Business Registration</p>
                <p className="text-lg">0123456789</p>
              </div>

              <div>
                <p className="font-medium text-muted-foreground mb-1">Tax ID</p>
                <p className="text-lg">0123456789-001</p>
              </div>

              <div>
                <p className="font-medium text-muted-foreground mb-1">Founded</p>
                <p className="text-lg">2025</p>
              </div>

              <div>
                <p className="font-medium text-muted-foreground mb-1">Industry</p>
                <p className="text-lg">Software Development & AI Technology</p>
              </div>
            </div>
          </div>
        </div>

        {/* Business Hours */}
        <div className="mt-8 bg-card p-8 rounded-lg border shadow-sm">
          <h2 className="text-2xl font-semibold mb-6">Business Hours</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Monday - Friday</span>
              <span className="font-medium">9:00 AM - 6:00 PM</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Saturday</span>
              <span className="font-medium">9:00 AM - 12:00 PM</span>
            </div>
            <div className="flex justify-between md:col-span-2">
              <span className="text-muted-foreground">Sunday & Public Holidays</span>
              <span className="font-medium">Closed</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

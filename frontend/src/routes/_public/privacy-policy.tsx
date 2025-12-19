import { createFileRoute } from '@tanstack/react-router'
import { Shield, Lock, Eye, Database, UserCheck, AlertCircle } from 'lucide-react'

export const Route = createFileRoute('/_public/privacy-policy')({
  component: PrivacyPolicy,
})

function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-16 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-4">
            <Shield className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Privacy Policy
          </h1>
          <p className="text-muted-foreground">Last updated: December 14, 2025</p>
        </div>

        {/* Content */}
        <div className="bg-card rounded-lg border shadow-sm">
          <div className="p-8 space-y-8">
            {/* Introduction */}
            <section>
              <p className="text-muted-foreground leading-relaxed">
                At VibeSDLC, we take your privacy seriously. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform. Please read this privacy policy carefully. If you do not agree with the terms of this privacy policy, please do not access the platform.
              </p>
            </section>

            {/* Information We Collect */}
            <section>
              <div className="flex items-center gap-3 mb-4">
                <Database className="w-6 h-6 text-primary" />
                <h2 className="text-2xl font-semibold">Information We Collect</h2>
              </div>
              <div className="space-y-4 text-muted-foreground leading-relaxed">
                <div>
                  <h3 className="font-semibold text-foreground mb-2">Personal Information</h3>
                  <p>
                    We may collect personal information that you voluntarily provide to us when you register on the platform, including:
                  </p>
                  <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
                    <li>Name and email address</li>
                    <li>Account credentials (encrypted passwords)</li>
                    <li>Profile information</li>
                    <li>Payment and billing information</li>
                  </ul>
                </div>

                <div>
                  <h3 className="font-semibold text-foreground mb-2">Usage Data</h3>
                  <p>
                    We automatically collect certain information when you use our platform:
                  </p>
                  <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
                    <li>IP address and browser type</li>
                    <li>Operating system and device information</li>
                    <li>Pages visited and time spent on pages</li>
                    <li>Project and code data you create</li>
                    <li>AI agent interactions and usage patterns</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* How We Use Your Information */}
            <section>
              <div className="flex items-center gap-3 mb-4">
                <Eye className="w-6 h-6 text-primary" />
                <h2 className="text-2xl font-semibold">How We Use Your Information</h2>
              </div>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>We use the information we collect to:</p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>Provide, maintain, and improve our services</li>
                  <li>Process your transactions and manage your account</li>
                  <li>Send you technical notices and support messages</li>
                  <li>Respond to your inquiries and provide customer support</li>
                  <li>Develop new features and enhance user experience</li>
                  <li>Monitor and analyze usage patterns and trends</li>
                  <li>Detect, prevent, and address technical issues and security threats</li>
                  <li>Train and improve our AI models (using anonymized data only)</li>
                </ul>
              </div>
            </section>

            {/* Data Security */}
            <section>
              <div className="flex items-center gap-3 mb-4">
                <Lock className="w-6 h-6 text-primary" />
                <h2 className="text-2xl font-semibold">Data Security</h2>
              </div>
              <div className="space-y-4 text-muted-foreground leading-relaxed">
                <p>
                  We implement appropriate technical and organizational measures to protect your personal information:
                </p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>End-to-end encryption for data in transit (HTTPS/TLS)</li>
                  <li>Encryption at rest for sensitive data</li>
                  <li>Regular security audits and penetration testing</li>
                  <li>Access controls and authentication mechanisms</li>
                  <li>Secure data centers with physical and network security</li>
                  <li>Regular backups and disaster recovery procedures</li>
                </ul>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 mt-4">
                  <div className="flex gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <p className="text-sm">
                      <strong className="text-amber-500">Important:</strong> While we strive to protect your personal information, no method of transmission over the Internet or electronic storage is 100% secure. We cannot guarantee absolute security.
                    </p>
                  </div>
                </div>
              </div>
            </section>

            {/* Data Sharing */}
            <section>
              <div className="flex items-center gap-3 mb-4">
                <UserCheck className="w-6 h-6 text-primary" />
                <h2 className="text-2xl font-semibold">Information Sharing and Disclosure</h2>
              </div>
              <div className="space-y-4 text-muted-foreground leading-relaxed">
                <p>We do not sell your personal information. We may share your information in the following circumstances:</p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li><strong className="text-foreground">Service Providers:</strong> With third-party vendors who perform services on our behalf (e.g., hosting, payment processing)</li>
                  <li><strong className="text-foreground">Legal Requirements:</strong> When required by law or to protect our rights and safety</li>
                  <li><strong className="text-foreground">Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets</li>
                  <li><strong className="text-foreground">With Your Consent:</strong> When you explicitly authorize us to share your information</li>
                </ul>
              </div>
            </section>

            {/* Your Rights */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">Your Privacy Rights</h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>You have the right to:</p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>Access and receive a copy of your personal data</li>
                  <li>Rectify inaccurate or incomplete personal data</li>
                  <li>Request deletion of your personal data</li>
                  <li>Object to processing of your personal data</li>
                  <li>Request restriction of processing</li>
                  <li>Data portability</li>
                  <li>Withdraw consent at any time</li>
                </ul>
                <p className="mt-4">
                  To exercise these rights, please contact us at <a href="mailto:vibesdlc@gmail.com" className="text-primary hover:underline">vibesdlc@gmail.com</a>
                </p>
              </div>
            </section>

            {/* Cookies */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">Cookies and Tracking Technologies</h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  We use cookies and similar tracking technologies to track activity on our platform and store certain information. You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent.
                </p>
              </div>
            </section>

            {/* Third-Party Links */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">Third-Party Services</h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  Our platform may contain links to third-party websites or services. We are not responsible for the privacy practices of these third parties. We encourage you to read their privacy policies.
                </p>
              </div>
            </section>

            {/* Children's Privacy */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">Children's Privacy</h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  Our platform is not intended for children under 13 years of age. We do not knowingly collect personal information from children under 13.
                </p>
              </div>
            </section>

            {/* Changes */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">Changes to This Privacy Policy</h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last updated" date.
                </p>
              </div>
            </section>

            {/* Contact */}
            <section className="border-t pt-8">
              <h2 className="text-2xl font-semibold mb-4">Contact Us</h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>If you have any questions about this Privacy Policy, please contact us:</p>
                <ul className="space-y-1">
                  <li>Email: <a href="mailto:vibesdlc@gmail.com" className="text-primary hover:underline">vibesdlc@gmail.com</a></li>
                  <li>Address: FPT University Hoa Lac, Ha Noi City Vietnam</li>
                </ul>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}

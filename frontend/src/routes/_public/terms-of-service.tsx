import { createFileRoute } from "@tanstack/react-router"
import { AlertCircle, FileText } from "lucide-react"

export const Route = createFileRoute("/_public/terms-of-service")({
  component: TermsOfService,
})

function TermsOfService() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-16 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-4">
            <FileText className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Terms of Service
          </h1>
          <p className="text-muted-foreground">
            Last updated: December 14, 2025
          </p>
        </div>

        {/* Content */}
        <div className="bg-card rounded-lg border shadow-sm">
          <div className="p-8 space-y-8">
            {/* Introduction */}
            <section>
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6">
                <div className="flex gap-3">
                  <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-muted-foreground">
                    <strong className="text-blue-500">
                      Please read carefully:
                    </strong>{" "}
                    By accessing and using VibeSDLC, you agree to be bound by
                    these Terms of Service. If you disagree with any part of
                    these terms, you may not access the service.
                  </p>
                </div>
              </div>
            </section>

            {/* Acceptance of Terms */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                1. Acceptance of Terms
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  By creating an account or using VibeSDLC ("the Service"), you
                  agree to comply with and be legally bound by these Terms of
                  Service, our Privacy Policy, and all applicable laws and
                  regulations.
                </p>
              </div>
            </section>

            {/* Account Registration */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                2. Account Registration
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  To use certain features of the Service, you must register for
                  an account. You agree to:
                </p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>
                    Provide accurate, current, and complete information during
                    registration
                  </li>
                  <li>Maintain and promptly update your account information</li>
                  <li>Maintain the security of your password and account</li>
                  <li>
                    Accept responsibility for all activities that occur under
                    your account
                  </li>
                  <li>
                    Notify us immediately of any unauthorized use of your
                    account
                  </li>
                </ul>
                <p className="mt-2">
                  You must be at least 13 years old to use this Service. By
                  creating an account, you represent that you meet this age
                  requirement.
                </p>
              </div>
            </section>

            {/* Use of Service */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">3. Use of Service</h2>
              <div className="space-y-4 text-muted-foreground leading-relaxed">
                <div>
                  <h3 className="font-semibold text-foreground mb-2">
                    Permitted Use
                  </h3>
                  <p>
                    You may use the Service for lawful purposes and in
                    accordance with these Terms. You agree not to:
                  </p>
                  <ul className="list-disc list-inside space-y-1 ml-4 mt-2">
                    <li>
                      Use the Service in any way that violates applicable laws
                      or regulations
                    </li>
                    <li>
                      Attempt to gain unauthorized access to the Service or
                      related systems
                    </li>
                    <li>
                      Interfere with or disrupt the Service or servers/networks
                      connected to the Service
                    </li>
                    <li>
                      Use the Service to transmit viruses, malware, or other
                      malicious code
                    </li>
                    <li>
                      Engage in any activity that could harm, disable, or impair
                      the Service
                    </li>
                    <li>
                      Attempt to reverse engineer, decompile, or disassemble any
                      part of the Service
                    </li>
                    <li>
                      Use automated systems to access the Service without our
                      permission
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            {/* Intellectual Property */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                4. Intellectual Property Rights
              </h2>
              <div className="space-y-4 text-muted-foreground leading-relaxed">
                <div>
                  <h3 className="font-semibold text-foreground mb-2">
                    Our Rights
                  </h3>
                  <p>
                    The Service and its original content, features, and
                    functionality are owned by VibeSDLC and are protected by
                    international copyright, trademark, and other intellectual
                    property laws.
                  </p>
                </div>
                <div>
                  <h3 className="font-semibold text-foreground mb-2">
                    Your Content
                  </h3>
                  <p>
                    You retain all rights to any code, content, or data you
                    create or upload to the Service. By uploading content, you
                    grant us a limited license to use, store, and process your
                    content solely to provide the Service to you.
                  </p>
                </div>
              </div>
            </section>

            {/* Subscription and Payments */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                5. Subscription and Payments
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>
                    Some features require a paid subscription. Fees are charged
                    in advance on a monthly or annual basis.
                  </li>
                  <li>
                    Subscriptions automatically renew unless cancelled before
                    the renewal date.
                  </li>
                  <li>
                    We reserve the right to modify pricing with 30 days' notice
                    to existing subscribers.
                  </li>
                  <li>
                    Refunds are provided according to our refund policy
                    available in your account settings.
                  </li>
                  <li>You are responsible for all applicable taxes.</li>
                </ul>
              </div>
            </section>

            {/* AI Services */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                6. AI-Generated Content
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  Our AI agents provide suggestions and generate content. You
                  acknowledge that:
                </p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>
                    AI-generated content may contain errors or inaccuracies
                  </li>
                  <li>
                    You are responsible for reviewing and validating all
                    AI-generated code and content
                  </li>
                  <li>
                    We do not guarantee the accuracy, completeness, or
                    suitability of AI-generated content
                  </li>
                  <li>
                    You should not rely solely on AI-generated content for
                    critical decisions
                  </li>
                </ul>
              </div>
            </section>

            {/* Data and Privacy */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                7. Data and Privacy
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  Your use of the Service is also governed by our Privacy
                  Policy. By using the Service, you consent to our collection
                  and use of your information as described in the Privacy
                  Policy.
                </p>
              </div>
            </section>

            {/* Termination */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">8. Termination</h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  We may terminate or suspend your account and access to the
                  Service immediately, without prior notice, for any reason,
                  including but not limited to:
                </p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>Violation of these Terms of Service</li>
                  <li>Fraudulent, abusive, or illegal activity</li>
                  <li>Extended period of inactivity</li>
                  <li>At your request</li>
                </ul>
                <p className="mt-2">
                  Upon termination, your right to use the Service will
                  immediately cease. You may export your data before
                  termination.
                </p>
              </div>
            </section>

            {/* Disclaimer */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                9. Disclaimer of Warranties
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT
                  WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING
                  BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY,
                  FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
                </p>
                <p>
                  We do not warrant that the Service will be uninterrupted,
                  secure, or error-free, or that defects will be corrected.
                </p>
              </div>
            </section>

            {/* Limitation of Liability */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                10. Limitation of Liability
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  TO THE MAXIMUM EXTENT PERMITTED BY LAW, VIBESDLC SHALL NOT BE
                  LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL,
                  OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES,
                  WHETHER INCURRED DIRECTLY OR INDIRECTLY, OR ANY LOSS OF DATA,
                  USE, OR OTHER INTANGIBLE LOSSES.
                </p>
              </div>
            </section>

            {/* Governing Law */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">11. Governing Law</h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  These Terms shall be governed by and construed in accordance
                  with the laws of Vietnam, without regard to its conflict of
                  law provisions.
                </p>
              </div>
            </section>

            {/* Changes to Terms */}
            <section>
              <h2 className="text-2xl font-semibold mb-4">
                12. Changes to Terms
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  We reserve the right to modify these Terms at any time. We
                  will notify users of any material changes by email or through
                  the Service. Your continued use of the Service after such
                  modifications constitutes acceptance of the updated Terms.
                </p>
              </div>
            </section>

            {/* Contact */}
            <section className="border-t pt-8">
              <h2 className="text-2xl font-semibold mb-4">
                13. Contact Information
              </h2>
              <div className="space-y-2 text-muted-foreground leading-relaxed">
                <p>
                  If you have any questions about these Terms of Service, please
                  contact us:
                </p>
                <ul className="space-y-1">
                  <li>
                    Email:{" "}
                    <a
                      href="mailto:vibesdlc@gmail.com"
                      className="text-primary hover:underline"
                    >
                      vibesdlc@gmail.com
                    </a>
                  </li>
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

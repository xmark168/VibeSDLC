import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import useAuth from "@/hooks/useAuth"
import { account } from "@/lib/appwrite"
import { withToast } from "@/utils"

export const Route = createFileRoute("/_auth/oauth-callback")({
    component: OAuthCallback,
})

function OAuthCallback() {
    const navigate = useNavigate()
    const { loginMutation } = useAuth()
    const [_isProcessing, setIsProcessing] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const hasCalledRef = useRef(false)

    useEffect(() => {
        // Prevent duplicate calls using ref
        if (hasCalledRef.current) {
            return
        }
        hasCalledRef.current = true

        const handleOAuthCallback = async () => {
            try {
                // Debug: Check current URL
                console.log("Current URL:", window.location.href);
                console.log("URL params:", window.location.search);

                // Check if we have OAuth params
                const urlParams = new URLSearchParams(window.location.search);
                const userId = urlParams.get('userId');
                const secret = urlParams.get('secret');

                console.log("OAuth params - userId:", userId, "secret:", secret);

                if (!userId || !secret) {
                    throw new Error("OAuth callback missing required parameters. Make sure OAuth is configured in Appwrite Console.");
                }

                // Wait a bit for Appwrite to process the OAuth session
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Try to get session with retry logic
                let user;
                let retries = 3;

                while (retries > 0) {
                    try {
                        // First, try to get the session
                        const session = await account.getSession('current');
                        console.log("Current session:", session);

                        // Then get user info
                        user = await account.get();
                        console.log("OAuth user:", user);
                        break; // Success, exit retry loop
                    } catch (err: any) {
                        console.log(`Retry ${4 - retries}, error:`, err);
                        if (err.code === 401 && retries > 1) {
                            // Session not ready yet, wait and retry
                            await new Promise(resolve => setTimeout(resolve, 1000));
                            retries--;
                        } else {
                            throw err; // Give up or different error
                        }
                    }
                }

                if (!user || !user.email) {
                    throw new Error("Email not found in OAuth response")
                }

                await withToast(
                    new Promise((resolve, reject) => {
                        loginMutation.mutate(
                            {
                                requestBody: {
                                    email: user.email,
                                    fullname: user.name || user.email.split("@")[0],
                                    login_provider: true,
                                    password: "",
                                },
                            },
                            {
                                onSuccess: () => {
                                    setIsProcessing(false)
                                    resolve(null)
                                    // Navigate after successful login
                                    navigate({ to: "/projects" })
                                },
                                onError: (err) => {
                                    setIsProcessing(false)
                                    reject(err)
                                },
                            },
                        )
                    }),
                    {
                        loading: "Completing OAuth login...",
                        success: <b>OAuth login successful!</b>,
                        error: <b>OAuth login failed. Please try again.</b>,
                    },
                )
            } catch (err) {
                const errorMessage =
                    err instanceof Error ? err.message : "OAuth callback failed"
                setError(errorMessage)
                setIsProcessing(false)
                console.error("OAuth callback error:", err)

                setTimeout(() => {
                    navigate({ to: "/login" })
                }, 3000)
            }
        }

        handleOAuthCallback()
    }, [loginMutation.mutate, navigate])

    if (error) {
        return (
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card">
                <div className="space-y-4 text-center">
                    <h2 className="text-2xl font-bold text-red-500">Login Failed</h2>
                    <p className="text-muted-foreground">{error}</p>
                    <p className="text-sm text-muted-foreground">
                        Redirecting to login page...
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card">
            <div className="space-y-4 text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto" />
                <h2 className="text-2xl font-bold">Completing OAuth Login</h2>
                <p className="text-muted-foreground">
                    Please wait while we authenticate you...
                </p>
            </div>
        </div>
    )
}
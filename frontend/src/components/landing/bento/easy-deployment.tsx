import type React from "react"

interface DeploymentEasyProps {
  width?: number | string
  height?: number | string
  className?: string
}

const DeploymentEasy: React.FC<DeploymentEasyProps> = ({
  width = "100%",
  height = "100%",
  className = "",
}) => {
  const logLines = [
    "[16:37:25.637] Running build in Washington, D.C., USA (East) – iad1",
    "[16:37:25.638] Build machine configuration: 2 cores, 8 GB",
    "[16:37:25.653] Retrieving list of deployment files...",
    "[16:37:25.741] Previous build caches not available",
    "[16:37:25.979] Downloading 84 deployment files...",
    '[16:37:29.945] Running "vercel build"',
    "[16:37:30.561] Vercel CLI 44.5.0",
    '[16:37:30.880] Running "install" command: `bun install`...',
    "[16:37:30.914] bun install v1.2.19 (aad3abea)",
    "[16:37:30.940] Resolving dependencies",
    "[16:37:34.436] Resolved, downloaded and extracted [1116]",
    '[16:37:34.436] warn: incorrect peer dependency "react@19.1.0"',
    "[16:37:37.265] Saved lockfile",
    "[16:37:39.076] Next.js anonymous telemetry notice",
    "[16:37:39.137] ▲ Next.js 15.2.4",
    "[16:37:41.439] ✓ Compiled successfully",
    "[16:37:53.979] ✓ Generated static pages",
    "[16:38:00.585] ○ (Static) prerendered as static content",
    "[16:38:01.099] Build Completed in /vercel/output [30s]",
    "🚀 Deployment complete – Easy!",
  ]

  return (
    <div
      className={`w-full h-full flex items-center justify-center p-4 relative ${className} bg-[#2a2b2a]/80 backdrop-blur-xl rounded-3xl border border-[#3a3b3a]`}
      style={{
        width,
        height,
        position: "relative",
      }}
      role="img"
      aria-label="Deployment console output with Deploy on Vercel button"
    >
      {/* -------------------------------------------------------- */}
      {/* Console / Terminal panel                                */}
      {/* -------------------------------------------------------- */}
      <div
        className="relative bg-[#1a1b1a]/90 backdrop-blur-md border border-[#3a3b3a] rounded-xl overflow-hidden"
        style={{
          width: "340px",
          height: "239px",
        }}
      >
        {/* Button inside terminal - positioned at bottom */}
        <button
          className="absolute bottom-3 left-1/2 transform -translate-x-1/2 flex items-center justify-center gap-2 px-4 py-2 bg-[#6efcd9] text-black font-bold border-none cursor-pointer rounded-xl whitespace-nowrap shadow-lg hover:bg-[#5ae0c0] transition-all duration-300 z-10"
          style={{
            fontSize: "12px",
          }}
        >
          <span>🚀</span>
          Deploy to production
        </button>

        {/* Log text with padding bottom để tránh button */}
        <div
          className="p-4 h-full overflow-hidden font-mono text-xs leading-relaxed"
          style={{
            color: "#e5e7eb",
            whiteSpace: "pre",
            paddingBottom: "50px", // Tạo không gian cho button
          }}
        >
          {logLines.map((line, index) => (
            <p
              key={index}
              className="m-0"
              style={{
                color:
                  line.includes("✓") || line.includes("🚀")
                    ? "#10b981"
                    : line.includes("warn")
                      ? "#f59e0b"
                      : line.includes("▲")
                        ? "#8b5cf6"
                        : "#9ca3af",
              }}
            >
              {line}
            </p>
          ))}
        </div>

        {/* Gradient overlay for fade effect - chỉ áp dụng phần trên button */}
        <div className="absolute bottom-10 left-0 right-0 h-6 bg-gradient-to-t from-[#1a1b1a] to-transparent pointer-events-none" />
      </div>
    </div>
  )
}

export default DeploymentEasy

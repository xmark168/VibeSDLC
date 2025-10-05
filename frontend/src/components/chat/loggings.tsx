
export default function Loggings() {
  return (
    <div className="flex-1 overflow-auto bg-[#1a1a1a] text-[#d4d4d4] font-mono">
            <div className="p-4 space-y-2">
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:45]</span> <span className="text-[#4ade80]">INFO</span>{" "}
                <span className="text-[#d4d4d4]">Application started successfully</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:46]</span> <span className="text-[#60a5fa]">DEBUG</span>{" "}
                <span className="text-[#d4d4d4]">Loading configuration from env</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:47]</span> <span className="text-[#4ade80]">INFO</span>{" "}
                <span className="text-[#d4d4d4]">Database connection established</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:48]</span> <span className="text-[#fbbf24]">WARN</span>{" "}
                <span className="text-[#d4d4d4]">Deprecated API usage detected in module auth.ts</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:49]</span> <span className="text-[#4ade80]">INFO</span>{" "}
                <span className="text-[#d4d4d4]">Server listening on port 3000</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:50]</span> <span className="text-[#ef4444]">ERROR</span>{" "}
                <span className="text-[#d4d4d4]">Failed to load user preferences: Network timeout</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:51]</span> <span className="text-[#60a5fa]">DEBUG</span>{" "}
                <span className="text-[#d4d4d4]">Retrying connection attempt 1/3</span>
              </div>
              <div className="text-xs">
                <span className="text-[#858585]">[10:23:52]</span> <span className="text-[#4ade80]">INFO</span>{" "}
                <span className="text-[#d4d4d4]">User preferences loaded successfully</span>
              </div>
            </div>
          </div>
  )
}

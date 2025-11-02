export default function TestingQA() {
  return (
    <div className="col-span-3 row-span-1 group relative overflow-hidden ">
      <div className="relative p-6 h-full">
        <div className="flex items-center gap-6">
          {/* Progress Circle */}
          <div className="flex-1 flex justify-center">
            <div className="relative w-32 h-32">
              <svg className="transform -rotate-90 w-32 h-32">
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="transparent"
                  className="text-[#3a3b3a]"
                />
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="transparent"
                  strokeDasharray={`${2 * Math.PI * 56}`}
                  strokeDashoffset={`${2 * Math.PI * 56 * (1 - 95 / 100)}`}
                  className="text-[#5cf6d5] transition-all duration-1000"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-3xl font-bold text-white">95%</span>
              </div>
            </div>
          </div>

          {/* Test Status */}
          <div className="flex-1 space-y-3">
            <div className="bg-[#3a3b3a] border border-[#10b981]/30 rounded-lg p-3 backdrop-blur-sm">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-[#10b981] rounded-full" />
                <span className="text-[#10b981] font-medium text-sm">
                  Unit Tests
                </span>
              </div>
              <div className="text-[#9ca3af] text-xs mt-1">
                All 152 tests passing
              </div>
            </div>

            <div className="bg-[#3a3b3a] border border-[#10b981]/30 rounded-lg p-3 backdrop-blur-sm">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-[#10b981] rounded-full" />
                <span className="text-[#10b981] font-medium text-sm">
                  Integration Tests
                </span>
              </div>
              <div className="text-[#9ca3af] text-xs mt-1">
                87/87 tests successful
              </div>
            </div>

            <div className="bg-[#3a3b3a] border border-[#f59e0b]/30 rounded-lg p-3 backdrop-blur-sm">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-[#f59e0b] rounded-full animate-pulse" />
                <span className="text-[#f59e0b] font-medium text-sm">
                  E2E Tests
                </span>
              </div>
              <div className="text-[#9ca3af] text-xs mt-1">
                Running 23/45 tests
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useState } from "react"

export default function ChatInterface() {
  const [messages, setMessages] = useState<string[]>([])
  const [_codeLines, setCodeLines] = useState<number>(0)
  const [_activeCard, setActiveCard] = useState<number | null>(null)

  useEffect(() => {
    const chatInterval = setInterval(() => {
      const sampleMessages = [
        "PO: Requirements clarified ✓",
        "Dev: Feature implemented ",
        "QA: Tests passing ",
        "SM: Sprint on track ",
      ]
      setMessages((prev) => [
        ...prev.slice(-2),
        sampleMessages[Math.floor(Math.random() * sampleMessages.length)],
      ])
    }, 3000)
    return () => clearInterval(chatInterval)
  }, [])

  useEffect(() => {
    const codeInterval = setInterval(() => {
      setCodeLines((prev) => (prev + Math.floor(Math.random() * 50)) % 9999)
    }, 2000)
    return () => clearInterval(codeInterval)
  }, [])

  return (
    <div
      className="col-span-2 row-span-2 group relative overflow-hidden rounded-3xl transition-all duration-500"
      onMouseEnter={() => setActiveCard(2)}
      onMouseLeave={() => setActiveCard(null)}
    >
      <div className="relative p-6 h-full flex flex-col">
        {/* <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-[#3a3b3a] border border-[#4a4b4a] flex items-center justify-center">
                        <MessageSquare className="w-6 h-6 text-gray-500" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-white">Live Chat</h3>
                        <p className="text-[#9ca3af] text-xs">Real-time Collaboration</p>
                    </div>
                </div> */}

        {/* Chat Messages */}
        <div className="flex-1 space-y-3 overflow-hidden">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className="bg-[#3a3b3a] rounded-xl p-3 border border-[#4a4b4a] animate-slide-up"
            >
              <p className="text-[#e5e7eb] text-sm">{msg}</p>
            </div>
          ))}
        </div>

        {/* Typing Indicator */}
        <div className="mt-4 flex items-center gap-2 text-[#9ca3af] text-sm">
          <div className="flex gap-1">
            <div
              className="w-2 h-2 bg-[#5cf6d5] rounded-full animate-bounce"
              style={{ animationDelay: "0s" }}
            />
            <div
              className="w-2 h-2 bg-[#5cf6d5] rounded-full animate-bounce"
              style={{ animationDelay: "0.2s" }}
            />
            <div
              className="w-2 h-2 bg-[#5cf6d5] rounded-full animate-bounce"
              style={{ animationDelay: "0.4s" }}
            />
          </div>
          <span>Agent typing...</span>
        </div>
      </div>
    </div>
  )
}

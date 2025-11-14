export const ChatTypingIndicator = () => {
  return (
    <div className="flex gap-3 px-4 py-3">
      {/* Agent Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center">
        <div className="w-5 h-5 rounded-full bg-white/30"></div>
      </div>

      {/* Typing Animation */}
      <div className="flex items-center gap-2 bg-white border-2 border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
        </div>
        <span className="text-sm text-gray-500">Agent is typing...</span>
      </div>
    </div>
  )
}

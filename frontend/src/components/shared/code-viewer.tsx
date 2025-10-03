
import { Copy, Download, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState } from "react"

interface CodeViewerProps {
  filePath: string
  content: string
}

export function CodeViewer({ filePath, content }: CodeViewerProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filePath.split("/").pop() || "file.txt"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const pathParts = filePath.split("/")
  const lines = content.split("\n")

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Breadcrumb and actions */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {pathParts.map((part, index) => (
            <div key={index} className="flex items-center gap-2">
              {index > 0 && <span>›</span>}
              <span className={index === pathParts.length - 1 ? "text-foreground font-medium" : ""}>{part}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleCopy} title="Copy code">
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleDownload} title="Download file">
            <Download className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Code content */}
      <div className="flex-1 overflow-auto bg-[#1e1e1e]">
        <div className="flex font-mono text-sm">
          {/* Line numbers */}
          <div className="flex-shrink-0 px-4 py-4 text-right text-[#858585] select-none bg-[#1e1e1e] border-r border-[#2d2d2d]">
            {lines.map((_, index) => (
              <div key={index} className="leading-6">
                {index + 1}
              </div>
            ))}
          </div>
          {/* Code */}
          <div className="flex-1 px-4 py-4 text-[#d4d4d4] overflow-x-auto">
            <pre className="leading-6">
              <code>{content}</code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}

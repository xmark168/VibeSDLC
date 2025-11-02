import { GripVertical } from "lucide-react"
import { useEffect, useRef, useState } from "react"

interface ResizableHandleProps {
  onResize: (delta: number) => void
}

export function ResizableHandle({ onResize }: ResizableHandleProps) {
  const [isDragging, setIsDragging] = useState(false)
  const startXRef = useRef(0)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        e.preventDefault()
        const delta = e.clientX - startXRef.current
        startXRef.current = e.clientX
        onResize(delta)
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      document.body.style.userSelect = ""
      document.body.style.cursor = ""
    }

    if (isDragging) {
      document.body.style.userSelect = "none"
      document.body.style.cursor = "col-resize"

      document.addEventListener("mousemove", handleMouseMove)
      document.addEventListener("mouseup", handleMouseUp)
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleMouseUp)
    }
  }, [isDragging, onResize])

  return (
    <div
      className="w-1 cursor-col-resize flex items-center justify-center group relative transition-colors select-none"
      onMouseDown={(e) => {
        e.preventDefault()
        setIsDragging(true)
        startXRef.current = e.clientX
      }}
    >
      <div className="absolute inset-y-0 left-0 right-0 flex items-center justify-center">
        <div
          className="w-full h-full relative transition-opacity duration-200 opacity-0 group-hover:opacity-100"
          style={{
            background: `linear-gradient(to bottom, 
              transparent 0%, 
              hsl(var(--border) / 0.3) 15%, 
              hsl(var(--border) / 0.6) 35%, 
              hsl(var(--primary) / 0.8) 50%, 
              hsl(var(--border) / 0.6) 65%, 
              hsl(var(--border) / 0.3) 85%, 
              transparent 100%)`,
          }}
        />
      </div>
      <div className="absolute inset-y-0 -left-1 -right-1" />
      <GripVertical className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity relative z-10" />
    </div>
  )
}

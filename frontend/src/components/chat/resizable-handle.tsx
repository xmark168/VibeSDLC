
import { useEffect, useRef, useState } from "react"
import { GripVertical } from "lucide-react"

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
      className="w-1 bg-border hover:bg-primary/50 cursor-col-resize flex items-center justify-center group relative transition-colors select-none"
      onMouseDown={(e) => {
        e.preventDefault()
        setIsDragging(true)
        startXRef.current = e.clientX
      }}
    >
      <div className="absolute inset-y-0 -left-1 -right-1" />
      <GripVertical className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  )
}

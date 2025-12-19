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
      className="w-1 invisible pointer-events-auto cursor-col-resize absolute inset-y-0 right-0"
      onMouseDown={(e) => {
        e.preventDefault()
        setIsDragging(true)
        startXRef.current = e.clientX
      }}
    />
  )
}

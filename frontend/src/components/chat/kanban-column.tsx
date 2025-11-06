import { Plus } from "lucide-react"
import type React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { KanbanCard, type KanbanCardData } from "./kanban-card"

export type KanbanColumnData = {
  id: string
  title: string
  color: string
  cards: KanbanCardData[]
}

interface KanbanColumnProps {
  column: KanbanColumnData
  isDraggedOver?: boolean
  draggedCardId?: string | null
  onDragOver: (e: React.DragEvent) => void
  onDragLeave: () => void
  onDrop: (e: React.DragEvent) => void
  onCardDragStart: (card: KanbanCardData) => void
  onCardDragEnd: () => void
  onCardClick: (card: KanbanCardData) => void
  onCardDelete: (cardId: string) => void
  onCardDownloadResult: (card: KanbanCardData) => void
  onAddCard: (content: string) => void
}

export function KanbanColumn({
  column,
  isDraggedOver,
  draggedCardId,
  onDragOver,
  onDragLeave,
  onDrop,
  onCardDragStart,
  onCardDragEnd,
  onCardClick,
  onCardDelete,
  onCardDownloadResult,
  onAddCard,
}: KanbanColumnProps) {
  const [isAddingCard, setIsAddingCard] = useState(false)
  const [newCardContent, setNewCardContent] = useState("")

  const handleAddCard = () => {
    if (!newCardContent.trim()) return
    onAddCard(newCardContent)
    setNewCardContent("")
    setIsAddingCard(false)
  }

  return (
    <div
      className="w-72 flex-shrink-0"
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* Column Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-foreground">
            {column.title}
          </h3>
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
            {column.cards.length}
          </span>
        </div>
      </div>

      <div
        className={`space-y-3 min-h-[100px] rounded-lg p-2 transition-colors ${isDraggedOver ? "bg-muted/50" : ""}`}
      >
        {/* Cards */}
        {column.cards.map((card) => (
          <KanbanCard
            key={card.id}
            card={card}
            isDragging={draggedCardId === card.id}
            onDragStart={() => onCardDragStart(card)}
            onDragEnd={onCardDragEnd}
            onClick={() => onCardClick(card)}
            onDelete={() => onCardDelete(card.id)}
            onDownloadResult={() => onCardDownloadResult(card)}
          />
        ))}

        {/* Add Card Form */}
        {isAddingCard ? (
          <div className="bg-card rounded-lg border border-border p-3">
            <Input
              autoFocus
              placeholder="Enter task name..."
              value={newCardContent}
              onChange={(e) => setNewCardContent(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleAddCard()
                } else if (e.key === "Escape") {
                  setIsAddingCard(false)
                  setNewCardContent("")
                }
              }}
              className="text-sm border-0 p-0 h-auto focus-visible:ring-0 focus-visible:ring-offset-0"
            />
            <div className="flex gap-2 mt-2">
              <Button size="sm" onClick={handleAddCard} className="h-7 text-xs">
                Add
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setIsAddingCard(false)
                  setNewCardContent("")
                }}
                className="h-7 text-xs"
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setIsAddingCard(true)}
            className="w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1 py-2 px-2 rounded hover:bg-muted"
          >
            <Plus className="w-4 h-4" />
            <span>Add task</span>
          </button>
        )}
      </div>
    </div>
  )
}

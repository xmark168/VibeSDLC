
import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plus, X } from "lucide-react"

type KanbanCard = {
  id: string
  content: string
  columnId: string
}

type KanbanColumn = {
  id: string
  title: string
  color: string
  cards: KanbanCard[]
}

const initialColumns: KanbanColumn[] = [
  { id: "backlog", title: "Backlog", color: "border-yellow-500", cards: [] },
  { id: "todo", title: "ToDo", color: "border-purple-500", cards: [{ id: "1", content: "test", columnId: "todo" }] },
  { id: "inprogress", title: "InProgress", color: "border-red-500", cards: [] },
  { id: "review", title: "Review", color: "border-blue-500", cards: [] },
  { id: "testing", title: "Testing", color: "border-pink-500", cards: [] },
  { id: "done", title: "Done", color: "border-cyan-500", cards: [] },
]

export function KanbanBoard() {
  const [columns, setColumns] = useState<KanbanColumn[]>(initialColumns)
  const [addingCardTo, setAddingCardTo] = useState<string | null>(null)
  const [newCardContent, setNewCardContent] = useState("")
  const [draggedCard, setDraggedCard] = useState<KanbanCard | null>(null)
  const [draggedOverColumn, setDraggedOverColumn] = useState<string | null>(null)

  const handleAddCard = (columnId: string) => {
    if (!newCardContent.trim()) return

    setColumns((prev) =>
      prev.map((col) => {
        if (col.id === columnId) {
          return {
            ...col,
            cards: [
              ...col.cards,
              {
                id: Date.now().toString(),
                content: newCardContent,
                columnId,
              },
            ],
          }
        }
        return col
      }),
    )

    setNewCardContent("")
    setAddingCardTo(null)
  }

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setColumns((prev) =>
      prev.map((col) => {
        if (col.id === columnId) {
          return {
            ...col,
            cards: col.cards.filter((card) => card.id !== cardId),
          }
        }
        return col
      }),
    )
  }

  const handleDragStart = (card: KanbanCard) => {
    setDraggedCard(card)
  }

  const handleDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault()
    setDraggedOverColumn(columnId)
  }

  const handleDragLeave = () => {
    setDraggedOverColumn(null)
  }

  const handleDrop = (e: React.DragEvent, targetColumnId: string) => {
    e.preventDefault()
    if (!draggedCard) return

    // Remove card from source column and add to target column
    setColumns((prev) =>
      prev.map((col) => {
        // Remove from source column
        if (col.id === draggedCard.columnId) {
          return {
            ...col,
            cards: col.cards.filter((card) => card.id !== draggedCard.id),
          }
        }
        // Add to target column
        if (col.id === targetColumnId) {
          return {
            ...col,
            cards: [...col.cards, { ...draggedCard, columnId: targetColumnId }],
          }
        }
        return col
      }),
    )

    setDraggedCard(null)
    setDraggedOverColumn(null)
  }

  const handleDragEnd = () => {
    setDraggedCard(null)
    setDraggedOverColumn(null)
  }

  return (
    <div className="h-full overflow-x-auto bg-background p-6">
      <div className="flex gap-4 min-w-max">
        {columns.map((column) => (
          <div
            key={column.id}
            className="w-64 flex-shrink-0"
            onDragOver={(e) => handleDragOver(e, column.id)}
            onDragLeave={handleDragLeave}
            onDrop={(e) => handleDrop(e, column.id)}
          >
            {/* Column Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium text-foreground">{column.title}</h3>
                <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                  {column.cards.length}
                </span>
              </div>
            </div>

            <div
              className={`space-y-2 min-h-[100px] rounded-lg p-2 transition-colors ${
                draggedOverColumn === column.id ? "bg-muted/50" : ""
              }`}
            >
              {column.cards.map((card) => (
                <div
                  key={card.id}
                  draggable
                  onDragStart={() => handleDragStart(card)}
                  onDragEnd={handleDragEnd}
                  className={`bg-card rounded-lg border-2 ${column.color} p-3 group relative hover:shadow-sm transition-all cursor-move ${
                    draggedCard?.id === card.id ? "opacity-50" : ""
                  }`}
                >
                  <p className="text-sm text-foreground pr-6">{card.content}</p>
                  <button
                    onClick={() => handleDeleteCard(column.id, card.id)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-3 h-3 text-muted-foreground hover:text-foreground" />
                  </button>
                </div>
              ))}

              {/* Add Card Form */}
              {addingCardTo === column.id ? (
                <div className={`bg-card rounded-lg border-2 ${column.color} p-3`}>
                  <Input
                    autoFocus
                    placeholder="Type something"
                    value={newCardContent}
                    onChange={(e) => setNewCardContent(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        handleAddCard(column.id)
                      } else if (e.key === "Escape") {
                        setAddingCardTo(null)
                        setNewCardContent("")
                      }
                    }}
                    className="text-sm border-0 p-0 h-auto focus-visible:ring-0 focus-visible:ring-offset-0"
                  />
                  <div className="flex gap-2 mt-2">
                    <Button size="sm" onClick={() => handleAddCard(column.id)} className="h-7 text-xs">
                      Add
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setAddingCardTo(null)
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
                  onClick={() => setAddingCardTo(column.id)}
                  className="w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1 py-2"
                >
                  <Plus className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

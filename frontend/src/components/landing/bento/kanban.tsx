export default function KanbanBento() {
  const tasks = {
    "In Progress": [
      { id: 1, title: "task 1", progress: 75 },
      { id: 2, title: "task 2", progress: 50 },
    ],
    "To Do": [
      { id: 3, title: "task 3", progress: 0 },
      { id: 4, title: "task 4", progress: 0 },
    ],
    Done: [
      { id: 6, title: "task 6", progress: 100 },
      { id: 7, title: "task 7", progress: 100 },
    ],
  }

  return (
    <div className="col-span-3 row-span-1 group relative overflow-hidden rounded-3xl mt-7">
      <div className="relative p-6 h-full">
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(tasks).map(([column, columnTasks], _idx) => (
            <div
              key={column}
              className="bg-[#2a2b2a] rounded-xl p-4 border border-[#3a3b3a] backdrop-blur-sm transition-all duration-500 hover:border-[#4a4b4a]"
            >
              <div className="space-y-3">
                {columnTasks.map((task) => (
                  <div
                    key={task.id}
                    className="bg-[#3a3b3a] rounded-lg p-3 border border-[#4a4b4a] transition-all duration-300 hover:border-[#8b5cf6]/30"
                  >
                    <div className="text-[#e5e7eb] text-sm font-medium mb-2">
                      {task.title}
                    </div>

                    <div className="h-1.5 bg-[#2a2b2a] rounded-full overflow-hidden mb-2">
                      <div
                        className="h-full bg-[#5cf6d5] rounded-full transition-all duration-1000"
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-[#9ca3af] text-xs">
                        {task.progress}% complete
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

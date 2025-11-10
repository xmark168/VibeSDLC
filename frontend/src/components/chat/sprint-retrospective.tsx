import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Loader2, CheckCircle2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { agentApi } from "@/apis/agent"

interface SprintRetrospectiveProps {
  projectId?: string
  sprintId?: string
}

interface AgentReport {
  role: "po" | "dev" | "tester"
  name: string
  avatar: string
  report: string
  isLoading: boolean
  isSubmitted: boolean
}

export function SprintRetrospective({ projectId, sprintId }: SprintRetrospectiveProps) {
  const [stage, setStage] = useState<"idle" | "reporting" | "analyzing" | "summary">("idle")
  const [currentAgentIndex, setCurrentAgentIndex] = useState(0)

  const [agents, setAgents] = useState<AgentReport[]>([
    {
      role: "po",
      name: "Product Owner",
      avatar: "https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=100&h=100&fit=crop",
      report: "",
      isLoading: false,
      isSubmitted: false,
    },
    {
      role: "dev",
      name: "Developer",
      avatar: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=100&h=100&fit=crop",
      report: "",
      isLoading: false,
      isSubmitted: false,
    },
    {
      role: "tester",
      name: "Tester",
      avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop",
      report: "",
      isLoading: false,
      isSubmitted: false,
    },
  ])

  const [summary, setSummary] = useState({
    wentWell: "",
    blockers: "",
    poRules: "",
    devRules: "",
    testerRules: "",
  })

  const [sprintMetrics, setSprintMetrics] = useState({
    total_tasks: 0,
    completed_tasks: 0,
    total_points: 0,
    completed_points: 0,
    velocity: 0,
    completion_rate: 0,
  })

  const [overviewSummary, setOverviewSummary] = useState("")

  const [showPOFeedbackDialog, setShowPOFeedbackDialog] = useState(false)
  const [poFeedback, setPOFeedback] = useState({
    achievements: "",
    challenges: "",
    priorities: ""
  })

  const startRetrospective = () => {
    // Show PO feedback dialog first
    setShowPOFeedbackDialog(true)
  }

  const handlePOFeedbackSubmit = () => {
    setShowPOFeedbackDialog(false)

    // Build PO report from feedback
    let poReport = ""
    if (poFeedback.achievements) poReport += `✅ Hài lòng với sản phẩm:\n${poFeedback.achievements}\n\n`
    if (poFeedback.challenges) poReport += `🚧 Chưa hài lòng/Cần sửa:\n${poFeedback.challenges}\n\n`
    if (poFeedback.priorities) poReport += `🎯 Mong muốn cho sprint sau:\n${poFeedback.priorities}`

    if (!poReport.trim()) {
      poReport = "✅ Đã hoàn thành:\n• Sprint đang trong quá trình thực hiện\n\n🚧 Vấn đề gặp phải:\n• Chưa có feedback cụ thể"
    }

    // Set PO report directly
    setAgents(prev => prev.map((agent, i) =>
      i === 0 ? { ...agent, report: poReport, isSubmitted: true } : agent
    ))

    setStage("reporting")
    setCurrentAgentIndex(1)
    generateReport(1)
  }

  const generateReport = async (index: number) => {
    if (index >= agents.length) {
      // All agents done, call backend API
      setStage("analyzing")

      try {
        // Format PO feedback
        const poFeedbackText = poFeedback.achievements || poFeedback.challenges || poFeedback.priorities
          ? `Hài lòng với sản phẩm: ${poFeedback.achievements}\n\nChưa hài lòng/Cần sửa: ${poFeedback.challenges}\n\nMong muốn cho sprint sau: ${poFeedback.priorities}`
          : undefined

        // Call backend API
        const response = await agentApi.analyzeRetrospective({
          sprint_id: sprintId || "",
          project_id: projectId || "",
          user_feedback: poFeedbackText,
        })

        if (response.status === "success" && response.data) {
          console.log("Backend response:", response.data)
          console.log("Agent reports:", response.data.agent_reports)

          // Update agents with real reports from backend
          const agentReports = response.data.agent_reports || {}
          console.log("PO report:", agentReports.po)
          console.log("Dev report:", agentReports.dev)
          console.log("Tester report:", agentReports.tester)

          setAgents(prev => prev.map((agent, i) => {
            if (i === 0) return { ...agent, report: agentReports.po || "Không có báo cáo PO", isSubmitted: true }
            if (i === 1) return { ...agent, report: agentReports.dev || "Không có báo cáo Dev", isSubmitted: true }
            if (i === 2) return { ...agent, report: agentReports.tester || "Không có báo cáo Tester", isSubmitted: true }
            return agent
          }))

          // Update summary with real data
          setSummary({
            wentWell: response.data.what_went_well || "Không có dữ liệu",
            blockers: response.data.blockers_summary || "Không có blockers",
            poRules: response.data.po_rules || "Không có quy tắc",
            devRules: response.data.dev_rules || "Không có quy tắc",
            testerRules: response.data.tester_rules || "Không có quy tắc",
          })

          // Store metrics for display
          setSprintMetrics(response.data.sprint_metrics)

          // Show reporting stage first, then summary
          setStage("reporting")
          setTimeout(() => setStage("summary"), 3000)
        } else {
          alert(`Lỗi: ${response.error || "Không thể phân tích retrospective"}`)
          setStage("idle")
        }
      } catch (error) {
        console.error("Error calling retro API:", error)
        alert("Lỗi khi gọi API. Vui lòng thử lại.")
        setStage("idle")
      }
      return
    }

    // Show loading for current agent
    setAgents(prev => prev.map((a, i) =>
      i === index ? { ...a, isLoading: true } : a
    ))

    // Simulate agent reporting (will be replaced by real data from API)
    setTimeout(() => {
      setAgents(prev => prev.map((a, i) =>
        i === index ? { ...a, isLoading: false, isSubmitted: true } : a
      ))

      setTimeout(() => {
        setCurrentAgentIndex(index + 1)
        generateReport(index + 1)
      }, 500)
    }, 1500)
  }

  return (
    <div className="h-full overflow-auto p-6 bg-background">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold">Sprint Retrospective</h2>
          <p className="text-sm text-muted-foreground">
            {stage === "idle" && "Bắt đầu retrospective để tạo báo cáo từ các agents"}
            {stage === "reporting" && "Các agents đang tạo báo cáo sprint..."}
            {stage === "analyzing" && "Scrum Master đang phân tích các báo cáo..."}
            {stage === "summary" && "Tổng kết Retrospective & Hành động cải tiến"}
          </p>
        </div>

        {/* Stage 0: Idle - Start Button */}
        {stage === "idle" && (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            {!sprintId && (
              <p className="text-sm text-muted-foreground">
                Vui lòng chọn sprint để chạy retrospective
              </p>
            )}
            {sprintId && (
              <>
                <Button
                  onClick={startRetrospective}
                  size="lg"
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  Bắt đầu Sprint Retrospective
                </Button>
                <p className="text-xs text-muted-foreground">
                  💡 Development mode: Có thể test với bất kỳ sprint nào
                </p>
              </>
            )}
          </div>
        )}

        {/* Stage 1: Agent Reporting */}
        {stage === "reporting" && (
          <div className="space-y-4">
            {agents.map((agent, index) => (
              <Card key={agent.role} className="p-6">
                <div className="flex gap-4">
                  <img
                    src={agent.avatar}
                    alt={agent.name}
                    className="w-16 h-16 rounded-full object-cover flex-shrink-0"
                  />
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-lg">{agent.name}</h3>
                        <p className="text-sm text-muted-foreground capitalize">{agent.role}</p>
                      </div>
                      {agent.isLoading && (
                        <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                      )}
                      {agent.isSubmitted && (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                      )}
                    </div>

                    {agent.isSubmitted && (
                      <div className="bg-muted/50 rounded-lg p-4">
                        <p className="text-sm leading-relaxed">{agent.report}</p>
                      </div>
                    )}

                    {agent.isLoading && (
                      <div className="bg-muted/30 rounded-lg p-4 flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <p className="text-sm text-muted-foreground">Đang tạo báo cáo...</p>
                      </div>
                    )}

                    {!agent.isLoading && !agent.isSubmitted && index > currentAgentIndex && (
                      <div className="bg-muted/20 rounded-lg p-4">
                        <p className="text-sm text-muted-foreground">Đang chờ...</p>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Stage 2: Scrum Master Analyzing */}
        {stage === "analyzing" && (
          <div className="flex flex-col items-center justify-center py-20 space-y-6">
            <div className="relative">
              <img
                src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=120&h=120&fit=crop"
                alt="Scrum Master"
                className="w-24 h-24 rounded-full object-cover"
              />
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin absolute -bottom-2 -right-2 bg-background rounded-full p-1" />
            </div>
            <div className="text-center space-y-2">
              <h3 className="text-xl font-semibold">Scrum Master đang phân tích...</h3>
              <p className="text-sm text-muted-foreground">
                Đang xử lý báo cáo và tạo insights
              </p>
            </div>
          </div>
        )}

        {/* Stage 3: Summary & Rules */}
        {stage === "summary" && (
          <div className="space-y-6">
            {/* Sprint Overview */}
            <Card className="p-6 space-y-4">
              <h3 className="text-lg font-semibold">📊 Sprint Overview</h3>

              <p className="text-sm leading-relaxed text-muted-foreground">
                Sprint tổng thể rất tốt! Chúng ta đã hoàn thành 40 story points với chất lượng cao. Team thể hiện sự phối hợp tốt giữa dev và QA. Tuy nhiên, chúng ta đã xác định được các vấn đề cần cải thiện: yêu cầu tích hợp cổng thanh toán cần làm rõ, tài liệu API bên thứ ba là điểm nghẽn, và môi trường test cần ổn định hơn. Hãy tập trung vào những cải tiến này cho sprint tiếp theo.
              </p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Story Points</p>
                  <p className="text-2xl font-bold">40/47</p>
                  <p className="text-xs text-green-600">85% completed</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Velocity</p>
                  <p className="text-2xl font-bold">40</p>
                  <p className="text-xs text-muted-foreground">points/sprint</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Tasks Completed</p>
                  <p className="text-2xl font-bold">18/21</p>
                  <p className="text-xs text-green-600">86% done</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Blockers Found</p>
                  <p className="text-2xl font-bold text-red-600">5</p>
                  <p className="text-xs text-muted-foreground">across team</p>
                </div>
              </div>
            </Card>

            {/* What Went Well */}
            <Card className="p-6 space-y-3">
              <h3 className="text-lg font-semibold text-green-600">✅ Những điều tốt</h3>
              <div className="text-sm whitespace-pre-line text-muted-foreground">
                {summary.wentWell}
              </div>
            </Card>

            {/* Blockers Summary */}
            <Card className="p-6 space-y-3">
              <h3 className="text-lg font-semibold text-red-600">🚧 Tổng hợp vấn đề</h3>
              <div className="text-sm whitespace-pre-line text-muted-foreground">
                {summary.blockers}
              </div>
            </Card>

            {/* Updated Project Rules */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">📋 Quy tắc dự án cho Sprint tiếp theo</h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* PO Rules */}
                <Card className="p-5 space-y-3 border-l-4 border-l-purple-500">
                  <div className="flex items-center gap-2">
                    <img
                      src={agents[0].avatar}
                      alt="PO"
                      className="w-8 h-8 rounded-full object-cover"
                    />
                    <h4 className="font-semibold">Product Owner</h4>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {summary.poRules}
                  </p>
                </Card>

                {/* Dev Rules */}
                <Card className="p-5 space-y-3 border-l-4 border-l-blue-500">
                  <div className="flex items-center gap-2">
                    <img
                      src={agents[1].avatar}
                      alt="Dev"
                      className="w-8 h-8 rounded-full object-cover"
                    />
                    <h4 className="font-semibold">Developer</h4>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {summary.devRules}
                  </p>
                </Card>

                {/* Tester Rules */}
                <Card className="p-5 space-y-3 border-l-4 border-l-green-500">
                  <div className="flex items-center gap-2">
                    <img
                      src={agents[2].avatar}
                      alt="Tester"
                      className="w-8 h-8 rounded-full object-cover"
                    />
                    <h4 className="font-semibold">Tester</h4>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {summary.testerRules}
                  </p>
                </Card>
              </div>
            </div>

            <div className="flex justify-center pt-4">
              <Button
                onClick={() => {
                  setStage("idle")
                  setCurrentAgentIndex(0)
                  setAgents(agents.map(a => ({ ...a, report: "", isLoading: false, isSubmitted: false })))
                  setPOFeedback({ achievements: "", challenges: "", priorities: "" })
                }}
                variant="outline"
              >
                Bắt đầu Retrospective mới
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* PO Feedback Dialog */}
      <Dialog open={showPOFeedbackDialog} onOpenChange={setShowPOFeedbackDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Product Owner Feedback</DialogTitle>
            <DialogDescription>
              Vui lòng chia sẻ góc nhìn của bạn về sprint này trước khi bắt đầu retrospective
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="achievements">Bạn có hài lòng với sản phẩm trong sprint này không? 😊</Label>
              <Textarea
                id="achievements"
                placeholder="Ví dụ: Tính năng đăng nhập hoạt động tốt, giao diện đẹp, người dùng thích..."
                value={poFeedback.achievements}
                onChange={(e) => setPOFeedback({...poFeedback, achievements: e.target.value})}
                className="min-h-[80px]"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="challenges">Có tính năng nào chưa hài lòng hoặc cần sửa không? 🤔</Label>
              <Textarea
                id="challenges"
                placeholder="Ví dụ: Trang chủ load chậm, nút thanh toán khó tìm, thiếu tính năng tìm kiếm..."
                value={poFeedback.challenges}
                onChange={(e) => setPOFeedback({...poFeedback, challenges: e.target.value})}
                className="min-h-[80px]"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="priorities">Bạn muốn thêm hoặc sửa đổi gì cho lần sau? 🎯</Label>
              <Textarea
                id="priorities"
                placeholder="Ví dụ: Thêm chức năng lọc sản phẩm, sửa màu nút cho dễ nhìn, làm app mượt hơn..."
                value={poFeedback.priorities}
                onChange={(e) => setPOFeedback({...poFeedback, priorities: e.target.value})}
                className="min-h-[80px]"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowPOFeedbackDialog(false)
                // Skip PO feedback, use empty report
                setAgents(prev => prev.map((agent, i) =>
                  i === 0 ? { ...agent, report: "", isSubmitted: true } : agent
                ))
                setStage("reporting")
                setCurrentAgentIndex(1) // Start from Dev
                generateReport(1)
              }}
            >
              Bỏ qua
            </Button>
            <Button onClick={handlePOFeedbackSubmit} className="bg-blue-600 hover:bg-blue-700">
              Tiếp tục
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  )
}

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Loader2, CheckCircle2 } from "lucide-react"
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
  const [useTestData, setUseTestData] = useState(false)

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

  const startRetrospective = (testMode: boolean) => {
    setUseTestData(testMode)
    setStage("analyzing")
    if (testMode) {
      loadTestData()
    } else {
      callBackendAPI()
    }
  }

  const loadTestData = () => {
    // Mock data for testing
    setTimeout(() => {
      setSummary({
        wentWell: "✅ Team hoàn thành 8/10 user stories với chất lượng cao\n✅ Code review process được cải thiện đáng kể\n✅ Daily standup hiệu quả, mọi người tham gia tích cực\n✅ Tích hợp CI/CD pipeline thành công\n✅ Performance optimization giảm load time 40%",
        blockers: "🚧 API documentation từ team backend chưa đầy đủ\n🚧 Môi trường staging bị down 2 ngày\n🚧 Thiếu thiết bị test cho iOS\n🚧 Requirements thay đổi giữa sprint\n🚧 Database migration gặp conflict",
        poRules: "📋 Freeze requirements sau planning meeting\n📋 Cung cấp acceptance criteria chi tiết hơn\n📋 Review mockup với team trước khi sprint\n📋 Tăng cường demo với stakeholders",
        devRules: "💻 Áp dụng pair programming cho complex tasks\n💻 Viết unit test trước khi code (TDD)\n💻 Code review trong vòng 4 giờ\n💻 Document API ngay khi implement\n💻 Refactor code cũ khi có cơ hội",
        testerRules: "🧪 Tạo test plan ngay sau planning\n🧪 Automation test cho regression\n🧪 Bug report phải có steps to reproduce\n🧪 Test trên nhiều browsers/devices\n🧪 Performance testing cho critical features",
      })
      setSprintMetrics({
        total_tasks: 21,
        completed_tasks: 18,
        total_points: 47,
        completed_points: 40,
        velocity: 40,
        completion_rate: 85,
      })

      const mockReports = {
        po: "Sprint này team đã làm việc rất tốt! Tôi đặc biệt ấn tượng với tốc độ delivery và chất lượng sản phẩm. Tuy nhiên, chúng ta cần cải thiện việc communication về requirements. Một số user stories bị hiểu sai dẫn đến phải rework. Tôi sẽ cố gắng làm rõ acceptance criteria hơn và tổ chức refinement session thường xuyên hơn.",
        dev: "Code quality trong sprint này khá tốt. Chúng tôi đã áp dụng code review nghiêm ngặt hơn và kết quả rất khả quan. Tuy nhiên, API documentation từ backend team chưa đầy đủ khiến frontend gặp khó khăn. Môi trường staging cũng bị down 2 ngày ảnh hưởng đến testing. Chúng tôi cần có backup environment và improve documentation process.",
        tester: "Testing process được cải thiện đáng kể. Automation coverage tăng lên 65%. Tuy nhiên, chúng tôi gặp blocker về thiết bị test iOS và môi trường staging không ổn định. Một số bugs được phát hiện muộn do requirements không rõ ràng. Cần có test plan sớm hơn và môi trường test ổn định hơn cho sprint sau.",
      }

      setStage("reporting")
      setTimeout(() => setAgents(prev => prev.map((a, i) => i === 0 ? { ...a, report: mockReports.po, isSubmitted: true } : a)), 500)
      setTimeout(() => setAgents(prev => prev.map((a, i) => i === 1 ? { ...a, report: mockReports.dev, isSubmitted: true } : a)), 1500)
      setTimeout(() => setAgents(prev => prev.map((a, i) => i === 2 ? { ...a, report: mockReports.tester, isSubmitted: true } : a)), 2500)
      setTimeout(() => setStage("summary"), 4500)
    }, 2000)
  }

  const callBackendAPI = async () => {
    try {
      // Call backend API
      const response = await agentApi.analyzeRetrospective({
        sprint_id: sprintId || "",
        project_id: projectId || "",
      })

        if (response.status === "success" && response.data) {
          const agentReports = response.data.agent_reports || {}

          // Update summary with real data (store for later)
          setSummary({
            wentWell: response.data.what_went_well || "Không có dữ liệu",
            blockers: response.data.blockers_summary || "Không có blockers",
            poRules: response.data.po_rules || "Không có quy tắc",
            devRules: response.data.dev_rules || "Không có quy tắc",
            testerRules: response.data.tester_rules || "Không có quy tắc",
          })
          setSprintMetrics(response.data.sprint_metrics)

          // Show reports one by one with animation
          setStage("reporting")

          // Show PO report (index 0)
          setTimeout(() => {
            setAgents(prev => prev.map((agent, i) =>
              i === 0 ? { ...agent, report: agentReports.po || "Không có báo cáo", isSubmitted: true } : agent
            ))
          }, 500)

          // Show Dev report (index 1)
          setTimeout(() => {
            setAgents(prev => prev.map((agent, i) =>
              i === 1 ? { ...agent, report: agentReports.dev || "Không có báo cáo", isSubmitted: true } : agent
            ))
          }, 1500)

          // Show Tester report (index 2)
          setTimeout(() => {
            setAgents(prev => prev.map((agent, i) =>
              i === 2 ? { ...agent, report: agentReports.tester || "Không có báo cáo", isSubmitted: true } : agent
            ))
          }, 2500)

          // Move to summary
          setTimeout(() => setStage("summary"), 4500)
      } else {
        alert(`Lỗi: ${response.error || "Không thể phân tích retrospective"}`)
        setStage("idle")
      }
    } catch (error) {
      console.error("Error calling retro API:", error)
      alert("Lỗi khi gọi API. Vui lòng thử lại.")
      setStage("idle")
    }
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
                <div className="flex gap-3">
                  <Button
                    onClick={() => startRetrospective(false)}
                    size="lg"
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    Chạy thật (Real Data)
                  </Button>
                  <Button
                    onClick={() => startRetrospective(true)}
                    size="lg"
                    variant="outline"
                  >
                    Test Mode (Mock Data)
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  💡 Chọn "Test Mode" để xem demo với dữ liệu mẫu đầy đủ
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
                }}
                variant="outline"
              >
                Bắt đầu Retrospective mới
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

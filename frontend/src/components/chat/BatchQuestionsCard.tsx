import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Loader2 } from 'lucide-react'

interface BatchQuestion {
  question_id?: string
  question_text: string
  question_type: 'open' | 'multichoice'
  options?: string[]
  allow_multiple?: boolean
  context?: string
}

interface BatchQuestionsCardProps {
  batchId: string
  questions: BatchQuestion[]
  questionIds: string[]
  onSubmit: (answers: Array<{ question_id: string; answer: string; selected_options?: string[] }>) => void
  agentName?: string
  answered?: boolean
}

export function BatchQuestionsCard({ 
  batchId, 
  questions, 
  questionIds,
  onSubmit, 
  agentName,
  answered = false 
}: BatchQuestionsCardProps) {
  // State for each question's answer
  const [answers, setAnswers] = useState<Map<string, { answer: string; selectedOptions: Set<string> }>>(
    new Map(questions.map((q, idx) => [questionIds[idx], { answer: '', selectedOptions: new Set() }]))
  )
  const [customInputs, setCustomInputs] = useState<Map<string, string>>(new Map())
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const updateAnswer = (questionId: string, answer: string) => {
    const newAnswers = new Map(answers)
    const current = newAnswers.get(questionId)
    if (current) {
      newAnswers.set(questionId, { ...current, answer })
      setAnswers(newAnswers)
    }
  }
  
  const toggleOption = (questionId: string, option: string, allowMultiple: boolean) => {
    const newAnswers = new Map(answers)
    const current = newAnswers.get(questionId)
    if (!current) return
    
    const newSelected = new Set(current.selectedOptions)
    
    if (allowMultiple) {
      // Multichoice: toggle
      if (newSelected.has(option)) {
        newSelected.delete(option)
      } else {
        newSelected.add(option)
      }
    } else {
      // Single choice: replace
      newSelected.clear()
      newSelected.add(option)
    }
    
    newAnswers.set(questionId, { ...current, selectedOptions: newSelected })
    setAnswers(newAnswers)
  }
  
  const handleSubmitAll = async () => {
    setIsSubmitting(true)
    
    try {
      const allAnswers = questions.map((q, idx) => {
        const questionId = questionIds[idx]
        const ans = answers.get(questionId)!
        let finalOptions = Array.from(ans.selectedOptions)
        
        // Replace "Other (Khác - vui lòng mô tả)" with custom input
        if (finalOptions.some(opt => opt.includes('Other') || opt.includes('Khác'))) {
          const customText = customInputs.get(questionId)
          if (customText?.trim()) {
            finalOptions = finalOptions.map(opt => 
              (opt.includes('Other') || opt.includes('Khác')) ? customText.trim() : opt
            )
          }
        }
        
        return {
          question_id: questionId,
          answer: ans.answer,
          selected_options: q.question_type === 'multichoice' ? finalOptions : undefined
        }
      })
      
      await onSubmit(allAnswers)
    } finally {
      setIsSubmitting(false)
    }
  }
  
  // Check if all questions answered
  const allAnswered = questions.every((q, idx) => {
    const questionId = questionIds[idx]
    const ans = answers.get(questionId)
    if (!ans) return false
    
    if (q.question_type === 'open') {
      return ans.answer.trim().length > 0
    } else {
      // Check if has selections AND custom input if needed
      const hasOther = Array.from(ans.selectedOptions).some(opt => 
        opt.includes('Other') || opt.includes('Khác')
      )
      const customText = customInputs.get(questionId)
      return ans.selectedOptions.size > 0 && (!hasOther || customText?.trim())
    }
  })
  
  if (answered) {
    return (
      <Card className="border-green-200 bg-green-50/50 dark:bg-green-950/20">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <div className="text-2xl">✅</div>
            <div>
              <h3 className="text-sm font-semibold text-green-700 dark:text-green-400">
                Đã trả lời {questions.length} câu hỏi
              </h3>
              <p className="text-xs text-muted-foreground">
                {agentName || 'Agent'} đang xử lý câu trả lời của bạn...
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }
  
  return (
    <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
      <CardContent className="p-4 space-y-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="text-2xl">❓</div>
          <div>
            <h3 className="text-sm font-semibold">
              {agentName || 'Agent'} đang hỏi {questions.length} câu hỏi
            </h3>
            <p className="text-xs text-muted-foreground">
              Vui lòng trả lời tất cả các câu hỏi bên dưới
            </p>
          </div>
        </div>
        
        {/* Render each question */}
        {questions.map((q, idx) => {
          const questionId = questionIds[idx]
          const ans = answers.get(questionId)
          if (!ans) return null
          
          const hasOther = Array.from(ans.selectedOptions).some(opt => 
            opt.includes('Other') || opt.includes('Khác')
          )
          
          return (
            <div key={questionId} className="p-4 border border-blue-200 dark:border-blue-700 rounded-lg bg-white dark:bg-gray-900">
              <div className="flex items-start gap-2 mb-3">
                <span className="text-sm font-semibold text-blue-600">
                  Q{idx + 1}:
                </span>
                <p className="text-sm font-medium flex-1">
                  {q.question_text}
                </p>
              </div>
              
              {q.question_type === 'open' ? (
                <Textarea
                  value={ans.answer}
                  onChange={(e) => updateAnswer(questionId, e.target.value)}
                  placeholder="Nhập câu trả lời của bạn..."
                  rows={3}
                  className="w-full"
                />
              ) : (
                <div className="space-y-3">
                  {q.allow_multiple ? (
                    <div className="space-y-2">
                      {q.options?.map(option => (
                        <div key={option} className="flex items-center space-x-2">
                          <Checkbox
                            id={`${questionId}-${option}`}
                            checked={ans.selectedOptions.has(option)}
                            onCheckedChange={() => toggleOption(questionId, option, true)}
                          />
                          <Label htmlFor={`${questionId}-${option}`} className="text-sm cursor-pointer">
                            {option}
                          </Label>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <RadioGroup
                      value={Array.from(ans.selectedOptions)[0] || ''}
                      onValueChange={(value) => toggleOption(questionId, value, false)}
                    >
                      {q.options?.map(option => (
                        <div key={option} className="flex items-center space-x-2">
                          <RadioGroupItem value={option} id={`${questionId}-${option}`} />
                          <Label htmlFor={`${questionId}-${option}`} className="text-sm cursor-pointer">
                            {option}
                          </Label>
                        </div>
                      ))}
                    </RadioGroup>
                  )}
                  
                  {/* Custom input for "Other" */}
                  {hasOther && (
                    <div className="mt-3 p-3 border rounded-lg bg-blue-50 dark:bg-blue-950">
                      <Label htmlFor={`custom-${questionId}`} className="text-xs text-muted-foreground mb-2 block">
                        Mô tả chi tiết:
                      </Label>
                      <Textarea
                        id={`custom-${questionId}`}
                        value={customInputs.get(questionId) || ''}
                        onChange={(e) => {
                          const newCustom = new Map(customInputs)
                          newCustom.set(questionId, e.target.value)
                          setCustomInputs(newCustom)
                        }}
                        placeholder="Vui lòng mô tả..."
                        rows={2}
                        className="w-full"
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
        
        {/* Submit All Button */}
        <Button
          onClick={handleSubmitAll}
          disabled={!allAnswered || isSubmitting}
          className="w-full"
          size="lg"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Đang gửi {questions.length} câu trả lời...
            </>
          ) : (
            <>
              📤 Submit All Answers ({questions.length})
            </>
          )}
        </Button>
        
        {!allAnswered && (
          <p className="text-xs text-center text-muted-foreground">
            Vui lòng trả lời tất cả {questions.length} câu hỏi để tiếp tục
          </p>
        )}
      </CardContent>
    </Card>
  )
}

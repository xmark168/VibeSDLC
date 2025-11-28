import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Loader2, ArrowLeft, ArrowRight } from 'lucide-react'

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
  // Current question index
  const [currentIndex, setCurrentIndex] = useState(0)
  
  // State for each question's answer
  const [answers, setAnswers] = useState<Map<string, { answer: string; selectedOptions: Set<string> }>>(
    new Map(questions.map((q, idx) => [questionIds[idx], { answer: '', selectedOptions: new Set() }]))
  )
  const [customInputs, setCustomInputs] = useState<Map<string, string>>(new Map())
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const currentQuestion = questions[currentIndex]
  const currentQuestionId = questionIds[currentIndex]
  const currentAnswer = currentQuestionId ? answers.get(currentQuestionId) : undefined
  
  const isFirstQuestion = currentIndex === 0
  const isLastQuestion = currentIndex === questions.length - 1
  
  // Guard: If no questions, show nothing
  if (!questions || questions.length === 0 || !currentQuestion) {
    return null
  }
  
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
      if (newSelected.has(option)) {
        newSelected.delete(option)
      } else {
        newSelected.add(option)
      }
    } else {
      newSelected.clear()
      newSelected.add(option)
    }
    
    newAnswers.set(questionId, { ...current, selectedOptions: newSelected })
    setAnswers(newAnswers)
  }
  
  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1)
    }
  }
  
  const handleBack = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
    }
  }
  
  const handleSubmitAll = async () => {
    setIsSubmitting(true)
    
    try {
      const allAnswers = questions.map((q, idx) => {
        const questionId = questionIds[idx]
        const ans = answers.get(questionId)!
        let finalOptions = Array.from(ans.selectedOptions)
        
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
  
  // Check if current question is answered
  const isCurrentAnswered = () => {
    if (!currentAnswer) return false
    
    if (currentQuestion.question_type === 'open') {
      return currentAnswer.answer.trim().length > 0
    } else {
      const hasOther = Array.from(currentAnswer.selectedOptions).some(opt => 
        opt.includes('Other') || opt.includes('Khác')
      )
      const customText = customInputs.get(currentQuestionId)
      return currentAnswer.selectedOptions.size > 0 && (!hasOther || customText?.trim())
    }
  }
  
  // Check if all questions are answered
  const allAnswered = questions.every((q, idx) => {
    const questionId = questionIds[idx]
    const ans = answers.get(questionId)
    if (!ans) return false
    
    if (q.question_type === 'open') {
      return ans.answer.trim().length > 0
    } else {
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
  
  const hasOther = currentAnswer ? Array.from(currentAnswer.selectedOptions).some(opt => 
    opt.includes('Other') || opt.includes('Khác')
  ) : false
  
  return (
    <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
      <CardContent className="p-4 space-y-4">
        {/* Header with progress */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-2xl">❓</div>
            <div>
              <h3 className="text-sm font-semibold">
                {agentName || 'Agent'} đang hỏi {questions.length} câu hỏi
              </h3>
            </div>
          </div>
          <div className="text-sm font-medium text-blue-600 dark:text-blue-400">
            {currentIndex + 1} / {questions.length}
          </div>
        </div>
        
        {/* Progress bar */}
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          />
        </div>
        
        {/* Current Question */}
        <div className="p-4 border border-blue-200 dark:border-blue-700 rounded-lg bg-white dark:bg-gray-900">
          <div className="flex items-start gap-2 mb-4">
            <span className="text-base font-semibold text-blue-600">
              Q{currentIndex + 1}:
            </span>
            <p className="text-base font-medium flex-1">
              {currentQuestion.question_text}
            </p>
          </div>
          
          {currentQuestion.question_type === 'open' ? (
            <Textarea
              value={currentAnswer?.answer || ''}
              onChange={(e) => updateAnswer(currentQuestionId, e.target.value)}
              placeholder="Nhập câu trả lời của bạn..."
              rows={4}
              className="w-full text-base"
            />
          ) : (
            <div className="space-y-3">
              {currentQuestion.allow_multiple ? (
                <div className="space-y-2">
                  {currentQuestion.options?.map(option => (
                    <div key={option} className="flex items-center space-x-2">
                      <Checkbox
                        id={`${currentQuestionId}-${option}`}
                        checked={currentAnswer?.selectedOptions.has(option) || false}
                        onCheckedChange={() => toggleOption(currentQuestionId, option, true)}
                      />
                      <Label htmlFor={`${currentQuestionId}-${option}`} className="text-sm cursor-pointer">
                        {option}
                      </Label>
                    </div>
                  ))}
                </div>
              ) : (
                <RadioGroup
                  value={currentAnswer ? Array.from(currentAnswer.selectedOptions)[0] || '' : ''}
                  onValueChange={(value) => toggleOption(currentQuestionId, value, false)}
                >
                  {currentQuestion.options?.map(option => (
                    <div key={option} className="flex items-center space-x-2">
                      <RadioGroupItem value={option} id={`${currentQuestionId}-${option}`} />
                      <Label htmlFor={`${currentQuestionId}-${option}`} className="text-sm cursor-pointer">
                        {option}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              )}
              
              {hasOther && (
                <div className="mt-3 p-3 border rounded-lg bg-blue-50 dark:bg-blue-950">
                  <Label htmlFor={`custom-${currentQuestionId}`} className="text-xs text-muted-foreground mb-2 block">
                    Mô tả chi tiết:
                  </Label>
                  <Textarea
                    id={`custom-${currentQuestionId}`}
                    value={customInputs.get(currentQuestionId) || ''}
                    onChange={(e) => {
                      const newCustom = new Map(customInputs)
                      newCustom.set(currentQuestionId, e.target.value)
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
        
        {/* Navigation Buttons */}
        <div className="flex justify-center gap-4 pt-2">
          {/* Back button - hidden on first question */}
          {!isFirstQuestion && (
            <Button
              variant="outline"
              onClick={handleBack}
              className="px-6"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          )}
          
          {/* Next or Submit button */}
          {isLastQuestion ? (
            <Button
              onClick={handleSubmitAll}
              disabled={!allAnswered || isSubmitting}
              className="px-6 bg-green-600 hover:bg-green-700"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Đang gửi...
                </>
              ) : (
                <>
                  Submit
                  <ArrowRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              disabled={!isCurrentAnswered()}
              className="px-6"
            >
              Next
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          )}
        </div>
        
        {/* Helper text */}
        {!isCurrentAnswered() && (
          <p className="text-xs text-center text-muted-foreground">
            Vui lòng trả lời câu hỏi để tiếp tục
          </p>
        )}
      </CardContent>
    </Card>
  )
}

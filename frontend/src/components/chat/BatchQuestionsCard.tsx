import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Loader2, ArrowLeft, ArrowRight, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, CheckCircle2 } from 'lucide-react'

interface BatchQuestion {
  question_id?: string
  question_text: string
  question_type: 'open' | 'multichoice'
  options?: string[]
  allow_multiple?: boolean
  context?: string
}

interface SubmittedAnswer {
  question_id: string
  answer?: string
  selected_options?: string[]
}

interface BatchQuestionsCardProps {
  batchId: string
  questions: BatchQuestion[]
  questionIds: string[]
  onSubmit: (answers: Array<{ question_id: string; answer: string; selected_options?: string[] }>) => void
  agentName?: string
  answered?: boolean
  submittedAnswers?: SubmittedAnswer[]  // Answers that were submitted
  chatInputValue?: string  // Current value from chat input
  onChatInputUsed?: () => void  // Callback when chat input is used as answer
  onQuestionChange?: (questionId: string, savedInput: string) => void  // Callback when question changes
  onAllAnsweredChange?: (allAnswered: boolean) => void  // Callback when all questions answered status changes
}

export function BatchQuestionsCard({
  batchId,
  questions,
  questionIds,
  onSubmit,
  agentName,
  answered = false,
  submittedAnswers = [],
  chatInputValue = '',
  onChatInputUsed,
  onQuestionChange,
  onAllAnsweredChange
}: BatchQuestionsCardProps) {
  // ALL hooks must be at the top, before any conditional returns
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<Map<string, { answer: string; selectedOptions: Set<string> }>>(
    new Map(questions.map((q, idx) => [questionIds[idx], { answer: '', selectedOptions: new Set() }]))
  )
  const [customInputs, setCustomInputs] = useState<Map<string, string>>(new Map())
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showQA, setShowQA] = useState(false)  // Moved here from below
  
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
    // ALWAYS save current chat input (even if empty) before switching
    const newCustom = new Map(customInputs)
    newCustom.set(currentQuestionId, chatInputValue) // Save current value (can be empty)
    setCustomInputs(newCustom)

    // Mark as selected if user typed something
    if (chatInputValue.trim() && currentQuestion.question_type === 'multichoice') {
      const newAnswers = new Map(answers)
      const current = newAnswers.get(currentQuestionId)
      if (current) {
        const newSelected = new Set(current.selectedOptions)
        newSelected.add('__CUSTOM__') // Special marker for custom answer
        newAnswers.set(currentQuestionId, { ...current, selectedOptions: newSelected })
        setAnswers(newAnswers)
      }
    } else if (!chatInputValue.trim() && currentQuestion.question_type === 'multichoice') {
      // If user cleared the input, remove the __CUSTOM__ marker
      const newAnswers = new Map(answers)
      const current = newAnswers.get(currentQuestionId)
      if (current) {
        const newSelected = new Set(current.selectedOptions)
        newSelected.delete('__CUSTOM__')
        newAnswers.set(currentQuestionId, { ...current, selectedOptions: newSelected })
        setAnswers(newAnswers)
      }
    }

    if (currentIndex < questions.length - 1) {
      const nextIndex = currentIndex + 1
      const nextQuestionId = questionIds[nextIndex]
      setCurrentIndex(nextIndex)

      // Notify parent to restore saved input for next question
      if (onQuestionChange) {
        const savedInput = newCustom.get(nextQuestionId) || ''
        onQuestionChange(nextQuestionId, savedInput)
      }
    }
  }

  const handleBack = () => {
    // ALWAYS save current chat input (even if empty) before switching
    const newCustom = new Map(customInputs)
    newCustom.set(currentQuestionId, chatInputValue) // Save current value (can be empty)
    setCustomInputs(newCustom)

    // Update __CUSTOM__ marker based on current input
    if (chatInputValue.trim() && currentQuestion.question_type === 'multichoice') {
      const newAnswers = new Map(answers)
      const current = newAnswers.get(currentQuestionId)
      if (current) {
        const newSelected = new Set(current.selectedOptions)
        newSelected.add('__CUSTOM__')
        newAnswers.set(currentQuestionId, { ...current, selectedOptions: newSelected })
        setAnswers(newAnswers)
      }
    } else if (!chatInputValue.trim() && currentQuestion.question_type === 'multichoice') {
      const newAnswers = new Map(answers)
      const current = newAnswers.get(currentQuestionId)
      if (current) {
        const newSelected = new Set(current.selectedOptions)
        newSelected.delete('__CUSTOM__')
        newAnswers.set(currentQuestionId, { ...current, selectedOptions: newSelected })
        setAnswers(newAnswers)
      }
    }

    if (currentIndex > 0) {
      const prevIndex = currentIndex - 1
      const prevQuestionId = questionIds[prevIndex]
      setCurrentIndex(prevIndex)

      // Notify parent to restore saved input for previous question
      if (onQuestionChange) {
        const savedInput = newCustom.get(prevQuestionId) || ''
        onQuestionChange(prevQuestionId, savedInput)
      }
    }
  }
  
  const handleSubmitAll = async () => {
    setIsSubmitting(true)
    
    try {
      // Prepare final answers and custom inputs map
      let finalAnswers = new Map(answers)
      let finalCustomInputs = new Map(customInputs)
      
      // Save current chat input before submitting
      if (chatInputValue.trim() && currentQuestion.question_type === 'multichoice') {
        finalCustomInputs.set(currentQuestionId, chatInputValue.trim())
        
        const current = finalAnswers.get(currentQuestionId)
        if (current) {
          const newSelected = new Set(current.selectedOptions)
          newSelected.add('__CUSTOM__')
          finalAnswers.set(currentQuestionId, { ...current, selectedOptions: newSelected })
        }
        
        if (onChatInputUsed) {
          onChatInputUsed()
        }
      }
      
      const allAnswers = questions.map((q, idx) => {
        const questionId = questionIds[idx]
        const ans = finalAnswers.get(questionId)!
        let finalOptions = Array.from(ans.selectedOptions)
        
        // Replace __CUSTOM__ marker with actual custom text
        if (finalOptions.includes('__CUSTOM__')) {
          const customText = finalCustomInputs.get(questionId)
          if (customText?.trim()) {
            finalOptions = finalOptions.filter(o => o !== '__CUSTOM__')
            finalOptions.push(customText.trim())
          } else {
            finalOptions = finalOptions.filter(o => o !== '__CUSTOM__')
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
      // For multichoice: either has selected options OR has custom text from chat
      const hasSelectedOptions = currentAnswer.selectedOptions.size > 0
      const hasCustomText = customInputs.get(currentQuestionId)?.trim() || chatInputValue.trim()
      return hasSelectedOptions || hasCustomText
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
      // For multichoice: either has selected options OR has custom text
      const hasSelectedOptions = ans.selectedOptions.size > 0
      const hasCustomText = customInputs.get(questionId)?.trim()
      // For current question, also check chatInputValue
      const isCurrentQ = questionId === currentQuestionId
      const currentHasCustom = isCurrentQ && chatInputValue.trim()
      return hasSelectedOptions || hasCustomText || currentHasCustom
    }
  })

  // Notify parent when allAnswered status changes
  useEffect(() => {
    if (onAllAnsweredChange) {
      onAllAnsweredChange(allAnswered)
    }
  }, [allAnswered, onAllAnsweredChange])
  
  if (answered) {
    // Build a map of answers by question_id for quick lookup
    const answersMap = new Map(submittedAnswers.map(a => [a.question_id, a]))

    return (
      <Card className="p-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-green-500/20">
        <CardContent className="p-0 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
              </div>
              <span className="text-sm font-medium text-green-700 dark:text-green-400">
                Đã trả lời
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowQA(!showQA)}
              className="text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50"
            >
              {showQA ? (
                <>
                  Ẩn <ChevronUp className="w-4 h-4 ml-1" />
                </>
              ) : (
                <>
                  Xem <ChevronDown className="w-4 h-4 ml-1" />
                </>
              )}
            </Button>
          </div>

          {/* Show all Q&A - collapsible */}
          {showQA && (
            <div className="space-y-2 mt-3 border-l-2 border-green-300 dark:border-green-600 pl-3">
              {questions.map((q, idx) => {
                const questionId = questionIds[idx]
                const ans = answersMap.get(questionId)
                const answerText = ans?.selected_options?.length
                  ? ans.selected_options.join(', ')
                  : ans?.answer || ''

                return (
                  <div key={questionId}>
                    <p className="text-sm text-muted-foreground">
                      <span className="font-medium text-green-600 dark:text-green-400">Q{idx + 1}:</span> {q.question_text}
                    </p>
                    <p className="text-sm text-foreground mt-0.5">
                      <span className="font-medium">→</span> {answerText || <span className="italic text-muted-foreground">Không có câu trả lời</span>}
                    </p>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }
  
  // Filter out "Khác" options from the list
  const filterOutOtherOption = (options: string[] | undefined): string[] => {
    if (!options) return []
    return options.filter(opt => {
      const lower = opt.toLowerCase()
      return !lower.startsWith('khác') && !lower.startsWith('other')
    })
  }

  // Get filtered options for current question
  const filteredOptions = filterOutOtherOption(currentQuestion.options)

  return (
    <Card className="overflow-hidden bg-transparent border-none shadow-none -py-7 pt-3">
      <CardContent className="space-y-2.5 -p-6 px-4">
        {/* Navigation Header */}
        <div className="flex items-center justify-between">
          {!isFirstQuestion ? (
            <Button
              variant="outline"
              onClick={handleBack}
              className="px-6 h-8"
            >
              <ArrowLeft className="w-4 h-4"/>
              Back
            </Button>
          ) : (
            <div />
          )}

          {isLastQuestion ? (
            <Button
              size="sm"
              onClick={handleSubmitAll}
              disabled={!allAnswered || isSubmitting}
              className="disabled:opacity-20 h-8"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  Sending...
                </>
              ) : (
                'Submit'
              )}
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              disabled={!isCurrentAnswered()}
              className="px-6 h-8"
            >
              Next
              <ArrowRight className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1 overflow-hidden">
          <div
            className="bg-blue-400 dark:bg-blue-500 h-1 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          />
        </div>

        <div className="space-y-2.5 max-h-[14rem] overflow-y-auto">
          {/* Question Header */}
          <div className="flex items-start gap-2 pt-1">
            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
              Q{currentIndex + 1}:
            </span>
            <p className="text-sm font-medium flex-1">
              {currentQuestion.question_text}
            </p>
          </div>

          {/* Answer Options */}
          {currentQuestion.question_type === 'open' ? (
            <Textarea
              value={currentAnswer?.answer || ''}
              onChange={(e) => updateAnswer(currentQuestionId, e.target.value)}
              placeholder="Nhập câu trả lời của bạn..."
              rows={3}
              className="w-full text-sm resize-none"
            />
          ) : (
            <div className="space-y-1.5">
              {currentQuestion.allow_multiple ? (
                <div className="space-y-1.5">
                  {filteredOptions.map(option => (
                    <div 
                      key={option} 
                      className="flex items-center space-x-2 p-1.5 rounded hover:bg-accent transition-colors cursor-pointer"
                      onClick={() => toggleOption(currentQuestionId, option, true)}
                    >
                      <Checkbox
                        id={`${currentQuestionId}-${option}`}
                        checked={currentAnswer?.selectedOptions.has(option) || false}
                        onCheckedChange={() => {}}
                      />
                      <span className="text-sm flex-1">
                        {option}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <RadioGroup
                  value={currentAnswer ? Array.from(currentAnswer.selectedOptions)[0] || '' : ''}
                  onValueChange={(value) => toggleOption(currentQuestionId, value, false)}
                  className="space-y-1.5"
                >
                  {filteredOptions.map(option => (
                    <div 
                      key={option} 
                      className="flex items-center space-x-2 p-1.5 rounded hover:bg-accent transition-colors cursor-pointer"
                      onClick={() => toggleOption(currentQuestionId, option, false)}
                    >
                      <RadioGroupItem 
                        value={option} 
                        id={`${currentQuestionId}-${option}`}
                      />
                      <span className="text-sm flex-1">
                        {option}
                      </span>
                    </div>
                  ))}
                </RadioGroup>
              )}
            </div>
          )}
        </div>

      </CardContent>
    </Card>
  )
}

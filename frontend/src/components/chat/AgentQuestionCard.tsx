import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'

interface AgentQuestionCardProps {
  question: string
  questionType: 'open' | 'multichoice'
  options: string[]
  allowMultiple: boolean
  answered?: boolean
  processing?: boolean
  userAnswer?: string
  userSelectedOptions?: string[]
  onSubmit: (answer: string, selectedOptions?: string[]) => void
  agentName?: string
}

export function AgentQuestionCard({
  question,
  questionType,
  options,
  allowMultiple,
  answered = false,
  processing = false,
  userAnswer,
  userSelectedOptions,
  onSubmit,
  agentName,
}: AgentQuestionCardProps) {
  const [textAnswer, setTextAnswer] = useState('')
  const [selectedOptions, setSelectedOptions] = useState<Set<string>>(new Set())
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const handleSubmit = async () => {
    setIsSubmitting(true)
    
    try {
      if (questionType === 'open') {
        await onSubmit(textAnswer, undefined)
      } else {
        await onSubmit('', Array.from(selectedOptions))
      }
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const canSubmit = questionType === 'open' 
    ? textAnswer.trim().length > 0 
    : selectedOptions.size > 0
  
  // Processing state (after answer, agent is working on it)
  if (answered && processing) {
    return (
      <Card className="border-yellow-200 bg-yellow-50 dark:bg-yellow-950/20">
        <CardContent className="pt-6 space-y-2">
          <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-sm font-medium">Processing your answer...</span>
          </div>
          {userSelectedOptions && userSelectedOptions.length > 0 && (
            <div className="text-sm text-gray-700 dark:text-gray-300">
              <strong>You selected:</strong> {userSelectedOptions.join(', ')}
            </div>
          )}
          {userAnswer && userAnswer.trim() && (
            <div className="text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 rounded p-2 border">
              <strong>Your answer:</strong> {userAnswer}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }
  
  // Answered state (agent has processed the answer)
  if (answered) {
    return (
      <Card className="border-green-200 bg-green-50 dark:bg-green-950/20">
        <CardContent className="pt-6 space-y-2">
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
            <CheckCircle2 className="w-5 h-5" />
            <span className="text-sm font-medium">Answered</span>
          </div>
          {userSelectedOptions && userSelectedOptions.length > 0 && (
            <div className="text-sm text-gray-700 dark:text-gray-300">
              <strong>You selected:</strong> {userSelectedOptions.join(', ')}
            </div>
          )}
          {userAnswer && userAnswer.trim() && (
            <div className="text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 rounded p-2 border">
              {userAnswer}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }
  
  return (
    <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950/20 shadow-md">
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
            <span className="text-xl">❓</span>
          </div>
          <div className="flex-1">
            <CardTitle className="text-base font-medium text-blue-900 dark:text-blue-100">
              {agentName || 'Agent'} is asking for clarification
            </CardTitle>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Question Text */}
        <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-blue-200">
          <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
            {question}
          </p>
        </div>
        
        {/* Answer Input */}
        {questionType === 'open' ? (
          // Open text input
          <div className="space-y-2">
            <Label htmlFor="answer" className="text-sm font-medium">
              Your answer:
            </Label>
            <Textarea
              id="answer"
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              placeholder="Type your answer here..."
              className="min-h-[100px] resize-none"
              disabled={isSubmitting}
            />
          </div>
        ) : (
          // Multichoice options
          <div className="space-y-3">
            <Label className="text-sm font-medium">
              {allowMultiple ? 'Select all that apply:' : 'Select one:'}
            </Label>
            
            {allowMultiple ? (
              // Checkboxes for multiple selection
              <div className="space-y-2">
                {options.map((option) => (
                  <div key={option} className="flex items-center space-x-2">
                    <Checkbox
                      id={`option-${option}`}
                      checked={selectedOptions.has(option)}
                      onCheckedChange={(checked) => {
                        const newSelected = new Set(selectedOptions)
                        if (checked) {
                          newSelected.add(option)
                        } else {
                          newSelected.delete(option)
                        }
                        setSelectedOptions(newSelected)
                      }}
                      disabled={isSubmitting}
                    />
                    <Label
                      htmlFor={`option-${option}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {option}
                    </Label>
                  </div>
                ))}
              </div>
            ) : (
              // Radio buttons for single selection
              <RadioGroup
                value={Array.from(selectedOptions)[0] || ''}
                onValueChange={(value) => {
                  setSelectedOptions(new Set([value]))
                }}
                disabled={isSubmitting}
              >
                {options.map((option) => (
                  <div key={option} className="flex items-center space-x-2">
                    <RadioGroupItem value={option} id={`radio-${option}`} />
                    <Label
                      htmlFor={`radio-${option}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {option}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            )}
          </div>
        )}
        
        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={!canSubmit || isSubmitting}
          className="w-full"
          size="lg"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Sending...
            </>
          ) : (
            'Send Answer'
          )}
        </Button>
        
        {/* Helper Text */}
        <div className="flex items-start gap-2 text-xs text-muted-foreground">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <p>
            The agent will continue processing once you submit your answer.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

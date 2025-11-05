import { useState, useEffect, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Clock, Send, SkipForward } from "lucide-react";
import type { AgentQuestion } from "@/hooks/useChatWebSocket";

interface AgentQuestionModalProps {
  question: AgentQuestion | null;
  onSubmit: (question_id: string, answer: string) => void;
  onSkip: (question_id: string) => void;
  onSkipAll: (question_id: string) => void;
}

export function AgentQuestionModal({
  question,
  onSubmit,
  onSkip,
  onSkipAll,
}: AgentQuestionModalProps) {
  const [answer, setAnswer] = useState("");
  const [timeRemaining, setTimeRemaining] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Reset answer when question changes
  useEffect(() => {
    if (question) {
      setAnswer("");
      // Auto-focus on textarea
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  }, [question?.question_id]);

  // Countdown timer
  useEffect(() => {
    if (!question) return;

    const startTime = question.receivedAt;
    const timeout = question.timeout * 1000; // convert to ms

    const updateTimer = () => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, timeout - elapsed);
      setTimeRemaining(remaining);

      if (remaining <= 0) {
        // Auto-skip on timeout
        handleSkip();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [question]);

  const handleSubmit = () => {
    if (!question || !answer.trim()) return;
    onSubmit(question.question_id, answer.trim());
    setAnswer("");
  };

  const handleSkip = () => {
    if (!question) return;
    onSkip(question.question_id);
    setAnswer("");
  };

  const handleSkipAll = () => {
    if (!question) return;
    onSkipAll(question.question_id);
    setAnswer("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  if (!question) return null;

  const timeRemainingSeconds = Math.ceil(timeRemaining / 1000);
  const timeRemainingMinutes = Math.floor(timeRemainingSeconds / 60);
  const timeRemainingSecondsDisplay = timeRemainingSeconds % 60;
  const progressPercentage = (timeRemaining / (question.timeout * 1000)) * 100;

  return (
    <Dialog open={!!question} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-2xl" showCloseButton={false}>
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl">
              {question.agent}
            </DialogTitle>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>
                {timeRemainingMinutes}:{timeRemainingSecondsDisplay.toString().padStart(2, "0")}
              </span>
            </div>
          </div>
          <DialogDescription className="text-base">
            Câu hỏi {question.question_number} / {question.total_questions}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Progress bar */}
          <Progress value={progressPercentage} className="h-1" />

          {/* Question text */}
          <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-base leading-relaxed whitespace-pre-wrap">
              {question.question_text}
            </p>
          </div>

          {/* Answer input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Câu trả lời của bạn:</label>
            <Textarea
              ref={textareaRef}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Nhập câu trả lời... (Enter để gửi, Shift+Enter để xuống dòng)"
              className="min-h-[120px] text-base p-3"
              autoFocus
            />
          </div>
        </div>

        <DialogFooter className="flex flex-col sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={handleSkipAll}
            className="sm:flex-1"
          >
            Bỏ qua tất cả
          </Button>
          <Button
            variant="outline"
            onClick={handleSkip}
            className="sm:flex-1"
          >
            <SkipForward className="w-4 h-4 mr-2" />
            Bỏ qua câu này
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!answer.trim()}
            className="sm:flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
          >
            <Send className="w-4 h-4 mr-2" />
            Gửi câu trả lời
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

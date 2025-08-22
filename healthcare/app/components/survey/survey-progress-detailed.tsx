"use client"

import type { Question } from "@/types/survey"
import { Progress } from "@/components/ui/progress"
import { Card, CardContent } from "@/components/ui/card"
import { CheckCircle, Circle, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

interface QuestionStatus {
  question: Question
  index: number
  status: "completed" | "current" | "upcoming"
  isValid: boolean
}

interface SurveyProgressDetailedProps {
  questions: Question[]
  currentIndex: number
  answers: Record<string, any>
  onQuestionClick?: (index: number) => void
  className?: string
}

export function SurveyProgressDetailed({
  questions,
  currentIndex,
  answers,
  onQuestionClick,
  className,
}: SurveyProgressDetailedProps) {
  const questionStatuses: QuestionStatus[] = questions.map((question, index) => {
    const hasAnswer = answers[question.code] !== undefined && answers[question.code] !== ""
    const status = index < currentIndex ? "completed" : index === currentIndex ? "current" : "upcoming"

    return {
      question,
      index,
      status,
      isValid: hasAnswer,
    }
  })

  const completedCount = questionStatuses.filter((q) => q.status === "completed" && q.isValid).length
  const progressPercentage = Math.round((completedCount / questions.length) * 100)

  return (
    <Card className={cn("w-full", className)}>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-foreground">Survey Progress</h3>
            <span className="text-sm text-muted-foreground">
              {completedCount} of {questions.length} completed
            </span>
          </div>

          <Progress value={progressPercentage} className="h-2" />

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {questionStatuses.map((questionStatus) => (
              <div
                key={questionStatus.question.code}
                className={cn(
                  "flex items-center gap-3 p-2 rounded-md transition-colors cursor-pointer hover:bg-muted/50",
                  questionStatus.status === "current" && "bg-primary/10 border border-primary/20",
                  onQuestionClick && "cursor-pointer",
                )}
                onClick={() => onQuestionClick?.(questionStatus.index)}
              >
                <div className="flex-shrink-0">
                  {questionStatus.status === "completed" && questionStatus.isValid ? (
                    <CheckCircle className="h-5 w-5 text-primary" />
                  ) : questionStatus.status === "current" ? (
                    <Clock className="h-5 w-5 text-primary" />
                  ) : (
                    <Circle className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "text-sm font-medium truncate",
                      questionStatus.status === "current" ? "text-primary" : "text-foreground",
                    )}
                  >
                    {questionStatus.question.title}
                  </p>
                  <p className="text-xs text-muted-foreground">Question {questionStatus.index + 1}</p>
                </div>

                {questionStatus.status === "completed" && !questionStatus.isValid && (
                  <div className="flex-shrink-0">
                    <div className="h-2 w-2 bg-destructive rounded-full" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

"use client"

import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"

interface SurveyProgressProps {
  currentQuestion: number
  totalQuestions: number
  percentage: number
  className?: string
}

export function SurveyProgress({ currentQuestion, totalQuestions, percentage, className }: SurveyProgressProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Question {currentQuestion} of {totalQuestions}
        </span>
        <span>{percentage}% complete</span>
      </div>
      <Progress value={percentage} className="h-2" />
    </div>
  )
}

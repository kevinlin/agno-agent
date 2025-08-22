"use client"

import type { Question } from "@/types/survey"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { QuestionRenderer } from "./question-renderer"
import { cn } from "@/lib/utils"

interface SurveyQuestionCardProps {
  question: Question
  value?: any
  onChange: (value: any) => void
  questionNumber: number
  totalQuestions: number
  className?: string
}

export function SurveyQuestionCard({
  question,
  value,
  onChange,
  questionNumber,
  totalQuestions,
  className,
}: SurveyQuestionCardProps) {
  return (
    <Card className={cn("w-full max-w-2xl mx-auto", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between text-sm text-muted-foreground mb-2">
          <span>
            Question {questionNumber} of {totalQuestions}
          </span>
          <span>{Math.round((questionNumber / totalQuestions) * 100)}% complete</span>
        </div>
        <div className="w-full bg-muted rounded-full h-2">
          <div
            className="bg-primary h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${(questionNumber / totalQuestions) * 100}%` }}
          />
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <QuestionRenderer question={question} value={value} onChange={onChange} className="mb-6" />
      </CardContent>
    </Card>
  )
}

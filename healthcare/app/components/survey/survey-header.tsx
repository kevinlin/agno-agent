"use client"

import type { Survey } from "@/types/survey"
import { Card, CardContent } from "@/components/ui/card"
import { SurveyProgress } from "./survey-progress"

interface SurveyHeaderProps {
  survey: Survey
  currentQuestion: number
  totalQuestions: number
  progressPercentage: number
}

export function SurveyHeader({ survey, currentQuestion, totalQuestions, progressPercentage }: SurveyHeaderProps) {
  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardContent className="pt-6">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-foreground mb-2">{survey.title}</h1>
          {survey.description && <p className="text-muted-foreground">{survey.description}</p>}
        </div>

        <SurveyProgress
          currentQuestion={currentQuestion}
          totalQuestions={totalQuestions}
          percentage={progressPercentage}
        />
      </CardContent>
    </Card>
  )
}

"use client"

import type { Survey, Question } from "@/types/survey"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Edit, CheckCircle } from "lucide-react"
import { cn } from "@/lib/utils"

interface SurveyReviewProps {
  survey: Survey
  questions: Question[]
  answers: Record<string, any>
  onEdit: (questionIndex: number) => void
  onSubmit: () => void
  isSubmitting?: boolean
  className?: string
}

export function SurveyReview({
  survey,
  questions,
  answers,
  onEdit,
  onSubmit,
  isSubmitting,
  className,
}: SurveyReviewProps) {
  const getAnswerDisplay = (question: Question, value: any): string => {
    if (value === undefined || value === null || value === "") {
      return "Not answered"
    }

    switch (question.type) {
      case "INPUT":
        return `${value}${question.unit_text ? ` ${question.unit_text}` : ""}`

      case "SINGLE_SELECT":
      case "DROPDOWN":
        const singleOption = question.answers?.answers.find((a) => a.code === value)
        return singleOption?.title || value

      case "MULTIPLE_SELECT":
        if (!Array.isArray(value)) return "Invalid selection"
        const selectedOptions = question.answers?.answers.filter((a) => value.includes(a.code))
        return selectedOptions?.map((o) => o.title).join(", ") || "None selected"

      case "TIME":
        if (typeof value === "number") {
          const hours = Math.floor(value / 60)
          const minutes = value % 60
          return `${hours}h ${minutes}m`
        }
        return value

      default:
        return String(value)
    }
  }

  const answeredCount = questions.filter((q) => {
    const value = answers[q.code]
    return value !== undefined && value !== null && value !== ""
  }).length

  const completionPercentage = Math.round((answeredCount / questions.length) * 100)

  return (
    <div className={cn("w-full max-w-4xl mx-auto space-y-6", className)}>
      {/* Review Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Review Your Answers</CardTitle>
              <p className="text-muted-foreground mt-2">
                Please review your responses before submitting. You can edit any answer by clicking the edit button.
              </p>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="h-5 w-5 text-primary" />
                <span className="font-semibold">{completionPercentage}% Complete</span>
              </div>
              <p className="text-sm text-muted-foreground">
                {answeredCount} of {questions.length} questions answered
              </p>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Questions Review */}
      <div className="space-y-4">
        {questions.map((question, index) => {
          const value = answers[question.code]
          const hasAnswer = value !== undefined && value !== null && value !== ""
          const displayValue = getAnswerDisplay(question, value)

          return (
            <Card
              key={question.code}
              className={cn("transition-all duration-200", !hasAnswer && "border-destructive/20 bg-destructive/5")}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        Q{index + 1}
                      </Badge>
                      {question.required && (
                        <Badge variant="destructive" className="text-xs">
                          Required
                        </Badge>
                      )}
                    </div>

                    <h3 className="font-medium text-foreground">{question.title}</h3>

                    {question.subtitle && <p className="text-sm text-muted-foreground">{question.subtitle}</p>}

                    <div
                      className={cn(
                        "p-3 rounded-md border",
                        hasAnswer ? "bg-muted/50 border-border" : "bg-destructive/10 border-destructive/20",
                      )}
                    >
                      <p className={cn("text-sm", hasAnswer ? "text-foreground" : "text-destructive font-medium")}>
                        {displayValue}
                      </p>
                    </div>
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onEdit(index)}
                    className="flex items-center gap-2 flex-shrink-0"
                  >
                    <Edit className="h-4 w-4" />
                    Edit
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Submit Section */}
      <Card>
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            <div>
              <h3 className="text-lg font-semibold mb-2">Ready to Submit?</h3>
              <p className="text-muted-foreground">
                Once you submit, your responses will be processed and you'll receive your personalized results.
              </p>
            </div>

            {answeredCount < questions.length && (
              <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
                <p className="text-sm text-destructive font-medium">
                  You have {questions.length - answeredCount} unanswered questions. Please complete all required
                  questions before submitting.
                </p>
              </div>
            )}

            <Button
              onClick={onSubmit}
              disabled={isSubmitting || answeredCount < questions.filter((q) => q.required).length}
              size="lg"
              className="min-w-[200px]"
            >
              {isSubmitting ? "Submitting..." : "Submit Survey"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

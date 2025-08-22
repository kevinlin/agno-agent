"use client"

import type { Question } from "@/types/survey"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { CheckCircle, Circle, Clock, Save } from "lucide-react"
import { cn } from "@/lib/utils"

interface SurveyProgressSidebarProps {
  questions: Question[]
  currentIndex: number
  answers: Record<string, any>
  onQuestionClick?: (index: number) => void
  onSave?: () => void
  isSaving?: boolean
  lastSaved?: Date
  className?: string
}

export function SurveyProgressSidebar({
  questions,
  currentIndex,
  answers,
  onQuestionClick,
  onSave,
  isSaving,
  lastSaved,
  className,
}: SurveyProgressSidebarProps) {
  const completedCount = questions.filter((q, index) => {
    const hasAnswer = answers[q.code] !== undefined && answers[q.code] !== ""
    return index <= currentIndex && hasAnswer
  }).length

  const progressPercentage = Math.round((completedCount / questions.length) * 100)

  return (
    <div className={cn("w-80 space-y-4", className)}>
      {/* Progress Overview */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Progress Overview</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Completed</span>
            <span className="font-medium">
              {completedCount} of {questions.length}
            </span>
          </div>
          <Progress value={progressPercentage} className="h-2" />
          <div className="text-center text-sm text-muted-foreground">{progressPercentage}% complete</div>
        </CardContent>
      </Card>

      {/* Save Progress */}
      {onSave && (
        <Card>
          <CardContent className="pt-6">
            <Button
              onClick={onSave}
              disabled={isSaving}
              variant="outline"
              className="w-full flex items-center gap-2 bg-transparent"
            >
              <Save className="h-4 w-4" />
              {isSaving ? "Saving..." : "Save Progress"}
            </Button>
            {lastSaved && (
              <p className="text-xs text-muted-foreground mt-2 text-center">
                Last saved: {lastSaved.toLocaleTimeString()}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Question List */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Questions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-1 max-h-96 overflow-y-auto">
            {questions.map((question, index) => {
              const hasAnswer = answers[question.code] !== undefined && answers[question.code] !== ""
              const status = index < currentIndex ? "completed" : index === currentIndex ? "current" : "upcoming"
              const isClickable = index <= currentIndex && onQuestionClick

              return (
                <div
                  key={question.code}
                  className={cn(
                    "flex items-center gap-2 p-2 rounded-md text-sm transition-colors",
                    status === "current" && "bg-primary/10 border border-primary/20",
                    isClickable && "cursor-pointer hover:bg-muted/50",
                    !isClickable && "cursor-default",
                  )}
                  onClick={() => isClickable && onQuestionClick(index)}
                >
                  <div className="flex-shrink-0">
                    {status === "completed" && hasAnswer ? (
                      <CheckCircle className="h-4 w-4 text-primary" />
                    ) : status === "current" ? (
                      <Clock className="h-4 w-4 text-primary" />
                    ) : (
                      <Circle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p
                      className={cn("font-medium truncate", status === "current" ? "text-primary" : "text-foreground")}
                    >
                      {index + 1}. {question.title}
                    </p>
                  </div>

                  {status === "completed" && !hasAnswer && (
                    <div className="flex-shrink-0">
                      <div className="h-2 w-2 bg-destructive rounded-full" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

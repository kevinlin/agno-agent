"use client"

import { useState, useEffect } from "react"
import type { Survey } from "@/types/survey"
import { useSurvey } from "@/hooks/use-survey"
import { useSurveyPersistence } from "@/hooks/use-survey-persistence"
import { SurveyAppBar } from "./survey-app-bar"
import { SurveyQuestionCard } from "./survey-question-card"
import { SurveyNavigation } from "./survey-navigation"
import { SurveyProgressSidebar } from "./survey-progress-sidebar"
import { SurveyReview } from "./survey-review"
import { SurveyCompletion } from "./survey-completion"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { calculateDerivedMetrics } from "@/lib/survey-calculations"

interface SurveyContainerProps {
  survey: Survey
  userId?: string
  onComplete?: (answers: any[]) => void
  onSave?: (answers: any[]) => void
}

export function SurveyContainer({ survey, userId, onComplete, onSave }: SurveyContainerProps) {
  const [showSidebar, setShowSidebar] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const persistence = useSurveyPersistence({
    surveyCode: survey.code,
    userId,
    autoSaveInterval: 30000,
  })

  // Load initial data from persistence
  const savedProgress = persistence.loadProgress()

  const {
    currentQuestion,
    currentQuestionIndex,
    totalQuestions,
    answers,
    progressPercentage,
    surveyMode,
    isFirstQuestion,
    isLastQuestion,
    isCurrentQuestionValid,
    isComplete,
    updateAnswer,
    goToNext,
    goToPrevious,
    goToQuestion,
    goToReview,
    goToComplete,
    getAllAnswers,
    visibleQuestions,
  } = useSurvey({
    survey,
    initialSession: savedProgress
      ? {
          answers: Object.entries(savedProgress.answers).map(([question_code, value]) => ({
            question_code,
            value,
          })),
          current_question_index: savedProgress.currentQuestionIndex,
        }
      : undefined,
  })

  // Set last saved time from persistence
  useEffect(() => {
    if (savedProgress?.lastSaved) {
      // This would be handled by the persistence hook
    }
  }, [savedProgress])

  // Mark as unsaved when answers change
  useEffect(() => {
    persistence.markUnsaved()
  }, [answers, persistence])

  const handleNext = () => {
    if (isLastQuestion && isCurrentQuestionValid) {
      goToReview()
    } else {
      goToNext()
    }
  }

  const handleSave = async () => {
    await persistence.saveProgress(answers, currentQuestionIndex)
    onSave?.(getAllAnswers())
  }

  const handleQuestionClick = (index: number) => {
    goToQuestion(index)
    setShowSidebar(false)
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      const allAnswers = getAllAnswers()
      await onComplete?.(allAnswers)
      persistence.clearProgress()
      goToComplete()
    } catch (error) {
      console.error("Failed to submit survey:", error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const derivedMetrics = surveyMode === "complete" ? calculateDerivedMetrics(visibleQuestions, answers) : []

  if (surveyMode === "complete") {
    return (
      <div className="min-h-screen bg-background">
        <SurveyAppBar
          survey={survey}
          currentQuestion={totalQuestions}
          totalQuestions={totalQuestions}
          progressPercentage={100}
          showSidebar={false}
          onToggleSidebar={() => {}}
          surveyMode="complete"
        />
        <div className="container mx-auto px-4 py-8">
          <SurveyCompletion
            survey={survey}
            derivedMetrics={derivedMetrics}
            onStartNewSurvey={() => (window.location.href = "/")}
          />
        </div>
      </div>
    )
  }

  if (surveyMode === "review") {
    return (
      <div className="min-h-screen bg-background">
        <SurveyAppBar
          survey={survey}
          currentQuestion={totalQuestions}
          totalQuestions={totalQuestions}
          progressPercentage={100}
          showSidebar={showSidebar}
          onToggleSidebar={() => setShowSidebar(!showSidebar)}
          surveyMode="review"
        />

        <div className="flex">
          {/* Sidebar for review mode */}
          <div
            className={cn(
              "fixed inset-y-0 left-0 z-40 bg-background border-r transform transition-transform lg:relative lg:translate-x-0 top-[120px]",
              showSidebar ? "translate-x-0" : "-translate-x-full",
            )}
          >
            <div className="p-4 h-full overflow-y-auto flex flex-col">
              <SurveyProgressSidebar
                questions={visibleQuestions}
                currentIndex={currentQuestionIndex}
                answers={answers}
                onQuestionClick={handleQuestionClick}
                onSave={handleSave}
                isSaving={persistence.isSaving}
                lastSaved={persistence.lastSaved}
              />
            </div>
          </div>

          <div className="flex-1">
            <div className="container mx-auto px-4 py-8">
              <SurveyReview
                survey={survey}
                questions={visibleQuestions}
                answers={answers}
                onEdit={handleQuestionClick}
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
              />
            </div>
          </div>
        </div>

        {/* Overlay for mobile sidebar */}
        {showSidebar && (
          <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={() => setShowSidebar(false)} />
        )}
      </div>
    )
  }

  if (!currentQuestion) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md mx-auto">
          <CardContent className="pt-6 text-center">
            <h2 className="text-xl font-semibold mb-2">Survey Complete</h2>
            <p className="text-muted-foreground">Thank you for completing the survey!</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <SurveyAppBar
        survey={survey}
        currentQuestion={currentQuestionIndex + 1}
        totalQuestions={totalQuestions}
        progressPercentage={progressPercentage}
        showSidebar={showSidebar}
        onToggleSidebar={() => setShowSidebar(!showSidebar)}
        onSave={handleSave}
        isSaving={persistence.isSaving}
        lastSaved={persistence.lastSaved}
        surveyMode="question"
      />

      <div className="flex">
        {/* Sidebar */}
        <div
          className={cn(
            "fixed inset-y-0 left-0 z-40 bg-background border-r transform transition-transform lg:relative lg:translate-x-0 top-[120px]",
            showSidebar ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="p-4 h-full overflow-y-auto flex flex-col">
            <SurveyProgressSidebar
              questions={visibleQuestions}
              currentIndex={currentQuestionIndex}
              answers={answers}
              onQuestionClick={handleQuestionClick}
              onSave={handleSave}
              isSaving={persistence.isSaving}
              lastSaved={persistence.lastSaved}
            />
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 lg:ml-0">
          <div className="container mx-auto px-4 py-8 space-y-6">
            <SurveyQuestionCard
              question={currentQuestion}
              value={answers[currentQuestion.code]}
              onChange={(value) => updateAnswer(currentQuestion.code, value)}
              questionNumber={currentQuestionIndex + 1}
              totalQuestions={totalQuestions}
            />

            <div className="w-full max-w-2xl mx-auto space-y-4">
              <SurveyNavigation
                onPrevious={goToPrevious}
                onNext={handleNext}
                canGoBack={!isFirstQuestion}
                canGoForward={isCurrentQuestionValid}
                isLastQuestion={isLastQuestion}
              />

              <div className="flex justify-center lg:hidden">
                <Button
                  variant="outline"
                  onClick={handleSave}
                  disabled={persistence.isSaving}
                  className="text-sm bg-transparent"
                >
                  {persistence.isSaving ? "Saving..." : "Save Progress"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Overlay for mobile sidebar */}
      {showSidebar && (
        <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={() => setShowSidebar(false)} />
      )}
    </div>
  )
}

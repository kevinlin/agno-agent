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
import { SurveyErrorBoundary } from "./survey-error-boundary"
import { SurveyLoadingSkeleton, SurveyQuestionSkeleton } from "./survey-loading-skeleton"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { calculateDerivedMetrics } from "@/lib/survey-calculations"
import { formatErrorMessage, isNetworkError } from "@/lib/survey-api"
import { AlertCircle, RefreshCw, Wifi, WifiOff } from "lucide-react"

interface SurveyContainerProps {
  survey: Survey
  userId?: string
  onComplete?: (answers: any[]) => void
  onSave?: (answers: any[]) => void
}

export function SurveyContainer({ survey, userId, onComplete, onSave }: SurveyContainerProps) {
  const [showSidebar, setShowSidebar] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [savedProgress, setSavedProgress] = useState<any>(null)
  const [isLoadingProgress, setIsLoadingProgress] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [isOnline, setIsOnline] = useState(true)

  const persistence = useSurveyPersistence({
    surveyCode: survey.code,
    userId,
    autoSaveInterval: 30000,
  })

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    setIsOnline(navigator.onLine)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Load initial data from persistence with enhanced error handling
  useEffect(() => {
    const loadInitialProgress = async () => {
      try {
        setIsLoadingProgress(true)
        setLoadError(null)
        const progress = await persistence.loadProgress()
        setSavedProgress(progress)
        setRetryCount(0) // Reset retry count on success
      } catch (error) {
        console.error("Failed to load saved progress:", error)
        setSavedProgress(null)
        
        // Set user-friendly error message
        if (isNetworkError(error)) {
          setLoadError("Unable to connect to the server. Please check your internet connection and try again.")
        } else {
          setLoadError(formatErrorMessage(error))
        }
      } finally {
        setIsLoadingProgress(false)
      }
    }

    loadInitialProgress()
  }, [persistence.loadProgress, retryCount])

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
    completeOnBackend,
    isSaving,
    error,
  } = useSurvey({
    survey,
    userId,
    initialSession: savedProgress && savedProgress.answers
      ? {
          answers: Object.entries(savedProgress.answers).map(([question_code, value]) => ({
            question_code,
            value,
          })),
          current_question_index: savedProgress.currentQuestionIndex,
        }
      : undefined,
  })

  // Mark as unsaved when answers change
  useEffect(() => {
    persistence.markUnsaved()
  }, [answers, persistence.markUnsaved])

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
      // Complete survey on backend (saves status as completed and creates results)
      const result = await completeOnBackend()
      
      // Call onComplete callback if provided (for additional handling)
      if (onComplete) {
        const allAnswers = getAllAnswers()
        await onComplete(allAnswers)
      }
      
      // Clear local storage and navigate to completion
      persistence.clearProgress()
      goToComplete()
    } catch (error) {
      console.error("Failed to submit survey:", error)
      // Error is already handled by the useSurvey hook
      // Don't navigate to completion if submission failed
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleRetryLoad = () => {
    setRetryCount(prev => prev + 1)
  }

  const handleErrorReset = () => {
    setLoadError(null)
    setRetryCount(prev => prev + 1)
  }

  const derivedMetrics = surveyMode === "complete" ? calculateDerivedMetrics(visibleQuestions, answers) : []

  // Show error state if loading failed
  if (loadError && !isLoadingProgress) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md mx-auto">
          <CardContent className="pt-6 text-center space-y-4">
            <div className="mx-auto mb-4 w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-destructive" />
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Unable to Load Survey</h2>
              <p className="text-muted-foreground">{loadError}</p>
            </div>
            
            {!isOnline && (
              <div className="flex items-center justify-center space-x-2 text-amber-600 bg-amber-50 p-3 rounded-lg">
                <WifiOff className="w-4 h-4" />
                <span className="text-sm">You appear to be offline</span>
              </div>
            )}

            <div className="flex flex-col space-y-2 pt-4">
              <Button onClick={handleRetryLoad} disabled={isLoadingProgress}>
                <RefreshCw className={cn("w-4 h-4 mr-2", isLoadingProgress && "animate-spin")} />
                {isLoadingProgress ? "Retrying..." : "Try Again"}
              </Button>
              
              {retryCount > 2 && (
                <Button variant="outline" onClick={() => window.location.reload()}>
                  Reload Page
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Show loading state while progress is being loaded
  if (isLoadingProgress) {
    return <SurveyLoadingSkeleton />
  }

  if (surveyMode === "complete") {
    return (
      <SurveyErrorBoundary onReset={handleErrorReset}>
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
      </SurveyErrorBoundary>
    )
  }

  if (surveyMode === "review") {
    return (
      <SurveyErrorBoundary onReset={handleErrorReset}>
        <div className="min-h-screen bg-background">
          {/* Error display for review mode */}
          {error && (
            <div className="bg-destructive/10 border-l-4 border-destructive px-4 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 text-destructive" />
                  <span className="text-sm text-destructive">{error}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setLoadError(null)}
                  className="h-auto p-1 text-destructive hover:text-destructive"
                >
                  ×
                </Button>
              </div>
            </div>
          )}

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
                  isSaving={persistence.isSaving || isSaving}
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
      </SurveyErrorBoundary>
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
    <SurveyErrorBoundary onReset={handleErrorReset}>
      <div className="min-h-screen bg-background">
        {/* Online status indicator */}
        {!isOnline && (
          <div className="bg-amber-500 text-white px-4 py-2 text-center text-sm">
            <div className="flex items-center justify-center space-x-2">
              <WifiOff className="w-4 h-4" />
              <span>You're offline. Changes will be saved locally and synced when you reconnect.</span>
            </div>
          </div>
        )}

        {/* Survey error display */}
        {error && (
          <div className="bg-destructive/10 border-l-4 border-destructive px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-destructive" />
                <span className="text-sm text-destructive">{error}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setLoadError(null)}
                className="h-auto p-1 text-destructive hover:text-destructive"
              >
                ×
              </Button>
            </div>
          </div>
        )}

        <SurveyAppBar
          survey={survey}
          currentQuestion={currentQuestionIndex + 1}
          totalQuestions={totalQuestions}
          progressPercentage={progressPercentage}
          showSidebar={showSidebar}
          onToggleSidebar={() => setShowSidebar(!showSidebar)}
          onSave={handleSave}
          isSaving={persistence.isSaving || isSaving}
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
    </SurveyErrorBoundary>
  )
}

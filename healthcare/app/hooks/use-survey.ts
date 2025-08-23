"use client"

import { useState, useCallback, useMemo, useEffect, useRef } from "react"
import type { Survey, SurveyAnswer, SurveySession } from "@/types/survey"
import { getVisibleQuestions } from "@/lib/survey-data"
import { validateAnswer } from "@/lib/survey-validation"
import {
  getSurveyResponse,
  saveSurveyAnswer,
  completeSurveyResponse,
  SurveyApiError,
  formatErrorMessage,
  isNetworkError,
} from "@/lib/survey-api"

interface UseSurveyOptions {
  survey: Survey
  initialSession?: Partial<SurveySession>
  userId?: string // For backend synchronization
  enableAutoSave?: boolean // Enable automatic saving to backend
  autoSaveDelay?: number // Delay in ms before auto-saving
}

export function useSurvey({
  survey,
  initialSession,
  userId,
  enableAutoSave = true,
  autoSaveDelay = 2000,
}: UseSurveyOptions) {
  // Initialize answers from session or empty
  const [answers, setAnswers] = useState<Record<string, any>>(() => {
    const answerMap: Record<string, any> = {}
    if (initialSession?.answers) {
      initialSession.answers.forEach((answer) => {
        answerMap[answer.question_code] = answer.value
      })
    }
    return answerMap
  })

  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(initialSession?.current_question_index || 0)
  const [surveyMode, setSurveyMode] = useState<"questions" | "review" | "complete">("questions")

  // Backend integration state
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date>()
  const [error, setError] = useState<string>()
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [backendProgress, setBackendProgress] = useState<number>(0)

  // Auto-save timeout ref
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)

  // Load initial data from backend if userId is provided
  useEffect(() => {
    if (!userId || !survey?.code) return

    const loadBackendData = async () => {
      setIsLoading(true)
      setError(undefined)

      try {
        const response = await getSurveyResponse(userId, survey.code)
        
        // Update answers with backend data
        const backendAnswers: Record<string, any> = {}
        response.answers.forEach((answer) => {
          backendAnswers[answer.question_id] = answer.value
        })

        // Merge with existing answers (backend takes precedence)
        setAnswers((prev) => ({ ...prev, ...backendAnswers }))
        setBackendProgress(response.progress_pct)
        
        // Set last saved time
        setLastSaved(new Date())
        setHasUnsavedChanges(false)

      } catch (err) {
        if (err instanceof SurveyApiError && err.code !== 'survey_not_found') {
          setError(formatErrorMessage(err))
        }
        // If survey not found, that's okay - we'll start fresh
      } finally {
        setIsLoading(false)
      }
    }

    loadBackendData()
  }, [userId, survey?.code])

  // Save individual answer to backend
  const saveToBackend = useCallback(async (questionCode?: string, value?: any) => {
    if (!userId || !survey?.code) return

    setIsSaving(true)
    setError(undefined)

    try {
      if (questionCode && value !== undefined) {
        // Save single answer
        const response = await saveSurveyAnswer(userId, survey.code, questionCode, value)
        setBackendProgress(response.progress_pct)
      } else {
        // Save all unsaved answers (batch save)
        // For now, we'll save the most recent answer
        // In a more sophisticated implementation, we could track which answers are dirty
        const answerEntries = Object.entries(answers)
        if (answerEntries.length > 0) {
          const [lastQuestionCode, lastValue] = answerEntries[answerEntries.length - 1]
          const response = await saveSurveyAnswer(userId, survey.code, lastQuestionCode, lastValue)
          setBackendProgress(response.progress_pct)
        }
      }

      setLastSaved(new Date())
      setHasUnsavedChanges(false)
    } catch (err) {
      const errorMessage = formatErrorMessage(err)
      setError(errorMessage)
      
      // Don't show error for network issues during auto-save
      if (!isNetworkError(err)) {
        console.error('Failed to save to backend:', err)
      }
    } finally {
      setIsSaving(false)
    }
  }, [userId, survey?.code, answers])

  // Complete survey on backend
  const completeOnBackend = useCallback(async () => {
    if (!userId || !survey?.code) return null

    setIsSaving(true)
    setError(undefined)

    try {
      const result = await completeSurveyResponse(userId, survey.code)
      setLastSaved(new Date())
      setHasUnsavedChanges(false)
      return result
    } catch (err) {
      const errorMessage = formatErrorMessage(err)
      setError(errorMessage)
      throw err
    } finally {
      setIsSaving(false)
    }
  }, [userId, survey?.code])

  // Auto-save functionality
  useEffect(() => {
    if (!enableAutoSave || !userId || !hasUnsavedChanges) return

    // Clear existing timeout
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }

    // Set new timeout
    autoSaveTimeoutRef.current = setTimeout(() => {
      saveToBackend()
    }, autoSaveDelay)

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
      }
    }
  }, [hasUnsavedChanges, enableAutoSave, userId, autoSaveDelay, saveToBackend])

  // Get visible questions based on current answers
  const visibleQuestions = useMemo(() => {
    return getVisibleQuestions(survey, answers)
  }, [survey, answers])

  const currentQuestion = surveyMode === "questions" ? visibleQuestions[currentQuestionIndex] : null
  const totalQuestions = visibleQuestions.length
  const isFirstQuestion = currentQuestionIndex === 0
  const isLastQuestion = currentQuestionIndex === totalQuestions - 1

  // Calculate progress percentage
  const progressPercentage = Math.round(((currentQuestionIndex + 1) / totalQuestions) * 100)

  // Check if current question is valid
  const isCurrentQuestionValid = useMemo(() => {
    if (!currentQuestion) return false
    const currentValue = answers[currentQuestion.code]
    const validation = validateAnswer(currentQuestion, currentValue)
    return validation.isValid
  }, [currentQuestion, answers])

  // Update answer for a question with backend integration
  const updateAnswer = useCallback(
    async (questionCode: string, value: any, saveImmediately = false) => {
      // Optimistic update - update UI immediately
      setAnswers((prev) => ({
        ...prev,
        [questionCode]: value,
      }))

      // Mark as having unsaved changes
      setHasUnsavedChanges(true)

      // Save immediately if requested or if auto-save is disabled
      if (saveImmediately || !enableAutoSave) {
        await saveToBackend(questionCode, value)
      }
    },
    [enableAutoSave, saveToBackend]
  )

  // Navigate to next question
  const goToNext = useCallback(() => {
    if (!isCurrentQuestionValid) return
    
    // Trigger immediate save if there are unsaved changes
    if (hasUnsavedChanges && currentQuestion && answers[currentQuestion.code] !== undefined) {
      // Save without waiting to avoid blocking navigation
      saveToBackend(currentQuestion.code, answers[currentQuestion.code]).catch(err => {
        console.warn('Failed to save answer during navigation:', err)
      })
    }
    
    if (isLastQuestion) {
      setSurveyMode("review")
    } else {
      setCurrentQuestionIndex((prev) => prev + 1)
    }
  }, [isLastQuestion, isCurrentQuestionValid, hasUnsavedChanges, currentQuestion, answers, saveToBackend])

  // Navigate to previous question
  const goToPrevious = useCallback(() => {
    if (!isFirstQuestion) {
      // Trigger immediate save if there are unsaved changes
      if (hasUnsavedChanges && currentQuestion && answers[currentQuestion.code] !== undefined) {
        // Save without waiting to avoid blocking navigation
        saveToBackend(currentQuestion.code, answers[currentQuestion.code]).catch(err => {
          console.warn('Failed to save answer during navigation:', err)
        })
      }
      
      setCurrentQuestionIndex((prev) => prev - 1)
    }
  }, [isFirstQuestion, hasUnsavedChanges, currentQuestion, answers, saveToBackend])

  // Jump to specific question index
  const goToQuestion = useCallback(
    (index: number) => {
      if (index >= 0 && index < totalQuestions) {
        // Trigger immediate save if there are unsaved changes
        if (hasUnsavedChanges && currentQuestion && answers[currentQuestion.code] !== undefined) {
          // Save without waiting to avoid blocking navigation
          saveToBackend(currentQuestion.code, answers[currentQuestion.code]).catch(err => {
            console.warn('Failed to save answer during navigation:', err)
          })
        }
        
        setCurrentQuestionIndex(index)
        setSurveyMode("questions")
      }
    },
    [totalQuestions, hasUnsavedChanges, currentQuestion, answers, saveToBackend],
  )

  const goToReview = useCallback(() => {
    setSurveyMode("review")
  }, [])

  const goToComplete = useCallback(async () => {
    setSurveyMode("complete")
    
    // Complete survey on backend if userId is provided
    if (userId) {
      try {
        await completeOnBackend()
      } catch (err) {
        // Error is already handled in completeOnBackend
        console.error('Failed to complete survey on backend:', err)
      }
    }
  }, [userId, completeOnBackend])

  // Get all answers in the format expected by the API
  const getAllAnswers = useCallback((): SurveyAnswer[] => {
    return Object.entries(answers).map(([questionCode, value]) => ({
      question_code: questionCode,
      value,
    }))
  }, [answers])

  // Check if survey is complete (all visible questions answered)
  const isComplete = useMemo(() => {
    return visibleQuestions.every((question) => {
      const value = answers[question.code]
      const validation = validateAnswer(question, value)
      return validation.isValid
    })
  }, [visibleQuestions, answers])

  return {
    // Current state
    currentQuestion,
    currentQuestionIndex,
    totalQuestions,
    answers,
    progressPercentage,
    surveyMode,

    // Navigation state
    isFirstQuestion,
    isLastQuestion,
    isCurrentQuestionValid,
    isComplete,

    // Backend integration state
    isLoading,
    isSaving,
    lastSaved,
    error,
    hasUnsavedChanges,
    backendProgress,

    // Actions
    updateAnswer,
    goToNext,
    goToPrevious,
    goToQuestion,
    goToReview,
    goToComplete,
    getAllAnswers,
    saveToBackend,
    completeOnBackend,

    // Utility actions
    clearError: useCallback(() => setError(undefined), []),
    retryLastAction: useCallback(async () => {
      setError(undefined)
      // Could implement more sophisticated retry logic here
      if (hasUnsavedChanges) {
        await saveToBackend()
      }
    }, [hasUnsavedChanges, saveToBackend]),

    // Data
    visibleQuestions,
    survey,
  }
}

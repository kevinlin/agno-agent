"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import {
  getSurveyResponse,
  saveSurveyAnswer,
  SurveyApiError,
  formatErrorMessage,
  isNetworkError,
} from "@/lib/survey-api"

interface SurveyPersistenceOptions {
  surveyCode: string
  userId?: string
  autoSaveInterval?: number // in milliseconds
  enableBackendSync?: boolean // Enable backend synchronization
  fallbackToLocalStorage?: boolean // Fall back to localStorage when backend fails
}

export function useSurveyPersistence({
  surveyCode,
  userId,
  autoSaveInterval = 3000, // 3 seconds
  enableBackendSync = true,
  fallbackToLocalStorage = true,
}: SurveyPersistenceOptions) {
  const [isSaving, setIsSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date>()
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [error, setError] = useState<string>()
  const [isOnline, setIsOnline] = useState(true)
  const [backendAvailable, setBackendAvailable] = useState(true)

  const storageKey = `survey_${surveyCode}_${userId || "anonymous"}`
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout>()

  // Monitor online status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Load saved progress from localStorage and optionally backend
  const loadProgress = useCallback(async (preferBackend = true) => {
    let localData = null
    let backendData = null

    // Always try to load from localStorage first
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        const data = JSON.parse(saved)
        localData = {
          answers: data.answers || {},
          currentQuestionIndex: data.currentQuestionIndex || 0,
          lastSaved: data.lastSaved ? new Date(data.lastSaved) : undefined,
          source: 'localStorage' as const,
        }
      }
    } catch (error) {
      console.error("Failed to load survey progress from localStorage:", error)
    }

    // Try to load from backend if enabled and online
    if (enableBackendSync && userId && isOnline && preferBackend) {
      try {
        const response = await getSurveyResponse(userId, surveyCode)
        const backendAnswers: Record<string, any> = {}
        
        response.answers.forEach((answer) => {
          backendAnswers[answer.question_id] = answer.value
        })

        backendData = {
          answers: backendAnswers,
          currentQuestionIndex: 0, // Backend doesn't track current question index
          lastSaved: new Date(),
          progress_pct: response.progress_pct,
          status: response.status,
          source: 'backend' as const,
        }

        setBackendAvailable(true)
        setError(undefined)
      } catch (error) {
        if (error instanceof SurveyApiError) {
          if (error.code === 'survey_not_found') {
            // Survey not found is okay - start fresh
            setBackendAvailable(true)
          } else {
            setBackendAvailable(false)
            setError(formatErrorMessage(error))
          }
        } else {
          setBackendAvailable(false)
          console.error("Failed to load survey progress from backend:", error)
        }
      }
    }

    // Return backend data if available and more recent, otherwise local data
    if (backendData && localData) {
      // Compare timestamps to determine which is more recent
      const backendTime = backendData.lastSaved?.getTime() || 0
      const localTime = localData.lastSaved?.getTime() || 0
      
      return backendTime > localTime ? backendData : localData
    }

    return backendData || localData
  }, [storageKey, enableBackendSync, userId, isOnline, surveyCode])

  // Save progress to localStorage and backend
  const saveProgress = useCallback(
    async (answers: Record<string, any>, currentQuestionIndex: number, questionCode?: string) => {
      setIsSaving(true)
      setError(undefined)
      
      let localSaveSuccess = false
      let backendSaveSuccess = false

      try {
        // Always save to localStorage first (as fallback)
        if (fallbackToLocalStorage) {
          try {
            const data = {
              answers,
              currentQuestionIndex,
              lastSaved: new Date().toISOString(),
            }

            localStorage.setItem(storageKey, JSON.stringify(data))
            localSaveSuccess = true
          } catch (error) {
            console.error("Failed to save survey progress to localStorage:", error)
          }
        }

        // Save to backend if enabled and conditions are met
        if (enableBackendSync && userId && isOnline && backendAvailable) {
          try {
            if (questionCode && answers[questionCode] !== undefined) {
              // Save specific answer
              await saveSurveyAnswer(userId, surveyCode, questionCode, answers[questionCode])
              backendSaveSuccess = true
              setBackendAvailable(true)
            } else {
              // Save most recent answer (batch save not implemented yet)
              const answerEntries = Object.entries(answers)
              if (answerEntries.length > 0) {
                const [lastQuestionCode, lastValue] = answerEntries[answerEntries.length - 1]
                await saveSurveyAnswer(userId, surveyCode, lastQuestionCode, lastValue)
                backendSaveSuccess = true
                setBackendAvailable(true)
              }
            }
          } catch (error) {
            if (error instanceof SurveyApiError) {
              setError(formatErrorMessage(error))
              if (!isNetworkError(error)) {
                setBackendAvailable(false)
              }
            } else {
              console.error("Failed to save survey progress to backend:", error)
              setBackendAvailable(false)
            }
          }
        }

        // Update state if at least one save method succeeded
        if (localSaveSuccess || backendSaveSuccess) {
          setLastSaved(new Date())
          setHasUnsavedChanges(false)
        } else {
          throw new Error("Failed to save progress to any storage method")
        }

      } catch (error) {
        console.error("Failed to save survey progress:", error)
        if (!error) {
          setError("Failed to save progress. Please try again.")
        }
      } finally {
        setIsSaving(false)
      }
    },
    [storageKey, userId, surveyCode, enableBackendSync, isOnline, backendAvailable, fallbackToLocalStorage],
  )

  // Mark as having unsaved changes
  const markUnsaved = useCallback(() => {
    setHasUnsavedChanges(true)
  }, [])

  // Clear saved progress
  const clearProgress = useCallback(() => {
    try {
      localStorage.removeItem(storageKey)
      setLastSaved(undefined)
      setHasUnsavedChanges(false)
    } catch (error) {
      console.error("Failed to clear survey progress:", error)
    }
  }, [storageKey])

  // Auto-save functionality (enhanced)
  useEffect(() => {
    if (!autoSaveInterval || !hasUnsavedChanges) return

    // Clear existing timeout
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }

    // Set new timeout for auto-save
    autoSaveTimeoutRef.current = setTimeout(() => {
      // This callback will be provided by the component
      // The component should call triggerAutoSave when it wants to enable auto-save
    }, autoSaveInterval)

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
      }
    }
  }, [autoSaveInterval, hasUnsavedChanges])

  // Sync with backend when coming online
  useEffect(() => {
    if (isOnline && enableBackendSync && userId && hasUnsavedChanges) {
      // Auto-sync when coming back online
      // This would need to be triggered by the component
    }
  }, [isOnline, enableBackendSync, userId, hasUnsavedChanges])

  // Utility functions
  const clearError = useCallback(() => setError(undefined), [])
  
  const retryLastSave = useCallback(async (answers: Record<string, any>, currentQuestionIndex: number) => {
    if (!hasUnsavedChanges) return
    await saveProgress(answers, currentQuestionIndex)
  }, [hasUnsavedChanges, saveProgress])

  const syncWithBackend = useCallback(async (answers: Record<string, any>) => {
    if (!enableBackendSync || !userId || !isOnline) return

    try {
      // Try to sync all answers with backend
      for (const [questionCode, value] of Object.entries(answers)) {
        await saveSurveyAnswer(userId, surveyCode, questionCode, value)
      }
      setBackendAvailable(true)
      setError(undefined)
    } catch (error) {
      if (error instanceof SurveyApiError) {
        setError(formatErrorMessage(error))
      }
      console.error("Failed to sync with backend:", error)
    }
  }, [enableBackendSync, userId, isOnline, surveyCode])

  return {
    // Core functions
    loadProgress,
    saveProgress,
    clearProgress,
    markUnsaved,

    // State
    isSaving,
    lastSaved,
    hasUnsavedChanges,
    error,
    isOnline,
    backendAvailable,

    // Enhanced features
    clearError,
    retryLastSave,
    syncWithBackend,

    // Status helpers
    canSaveToBackend: enableBackendSync && userId && isOnline && backendAvailable,
    shouldFallbackToLocal: fallbackToLocalStorage && (!isOnline || !backendAvailable),
  }
}

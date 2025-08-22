"use client"

import { useState, useCallback, useEffect } from "react"

interface SurveyPersistenceOptions {
  surveyCode: string
  userId?: string
  autoSaveInterval?: number // in milliseconds
}

export function useSurveyPersistence({
  surveyCode,
  userId,
  autoSaveInterval = 30000, // 30 seconds
}: SurveyPersistenceOptions) {
  const [isSaving, setIsSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date>()
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  const storageKey = `survey_${surveyCode}_${userId || "anonymous"}`

  // Load saved progress from localStorage
  const loadProgress = useCallback(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        const data = JSON.parse(saved)
        return {
          answers: data.answers || {},
          currentQuestionIndex: data.currentQuestionIndex || 0,
          lastSaved: data.lastSaved ? new Date(data.lastSaved) : undefined,
        }
      }
    } catch (error) {
      console.error("Failed to load survey progress:", error)
    }
    return null
  }, [storageKey])

  // Save progress to localStorage
  const saveProgress = useCallback(
    async (answers: Record<string, any>, currentQuestionIndex: number) => {
      setIsSaving(true)
      try {
        const data = {
          answers,
          currentQuestionIndex,
          lastSaved: new Date().toISOString(),
        }

        localStorage.setItem(storageKey, JSON.stringify(data))
        setLastSaved(new Date())
        setHasUnsavedChanges(false)

        // TODO: Also save to API if userId is provided
        if (userId) {
          // await saveToAPI(surveyCode, userId, answers, currentQuestionIndex);
        }
      } catch (error) {
        console.error("Failed to save survey progress:", error)
      } finally {
        setIsSaving(false)
      }
    },
    [storageKey, userId, surveyCode],
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

  // Auto-save functionality
  useEffect(() => {
    if (!autoSaveInterval || !hasUnsavedChanges) return

    const interval = setInterval(() => {
      if (hasUnsavedChanges) {
        // This would need to be triggered from the component using this hook
        // with the current answers and question index
      }
    }, autoSaveInterval)

    return () => clearInterval(interval)
  }, [autoSaveInterval, hasUnsavedChanges])

  return {
    loadProgress,
    saveProgress,
    clearProgress,
    markUnsaved,
    isSaving,
    lastSaved,
    hasUnsavedChanges,
  }
}

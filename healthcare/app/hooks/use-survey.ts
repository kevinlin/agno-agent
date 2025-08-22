"use client"

import { useState, useCallback, useMemo } from "react"
import type { Survey, SurveyAnswer, SurveySession } from "@/types/survey"
import { getVisibleQuestions } from "@/lib/survey-data"
import { validateAnswer } from "@/lib/survey-validation"

interface UseSurveyOptions {
  survey: Survey
  initialSession?: Partial<SurveySession>
}

export function useSurvey({ survey, initialSession }: UseSurveyOptions) {
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

  // Update answer for a question
  const updateAnswer = useCallback((questionCode: string, value: any) => {
    setAnswers((prev) => ({
      ...prev,
      [questionCode]: value,
    }))
  }, [])

  // Navigate to next question
  const goToNext = useCallback(() => {
    if (isLastQuestion && isCurrentQuestionValid) {
      setSurveyMode("review")
    } else if (!isLastQuestion && isCurrentQuestionValid) {
      setCurrentQuestionIndex((prev) => prev + 1)
    }
  }, [isLastQuestion, isCurrentQuestionValid])

  // Navigate to previous question
  const goToPrevious = useCallback(() => {
    if (!isFirstQuestion) {
      setCurrentQuestionIndex((prev) => prev - 1)
    }
  }, [isFirstQuestion])

  // Jump to specific question index
  const goToQuestion = useCallback(
    (index: number) => {
      if (index >= 0 && index < totalQuestions) {
        setCurrentQuestionIndex(index)
        setSurveyMode("questions")
      }
    },
    [totalQuestions],
  )

  const goToReview = useCallback(() => {
    setSurveyMode("review")
  }, [])

  const goToComplete = useCallback(() => {
    setSurveyMode("complete")
  }, [])

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

    // Actions
    updateAnswer,
    goToNext,
    goToPrevious,
    goToQuestion,
    goToReview,
    goToComplete,
    getAllAnswers,

    // Data
    visibleQuestions,
    survey,
  }
}

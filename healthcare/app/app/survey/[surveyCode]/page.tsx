"use client"

import { use, useState, useEffect } from "react"
import { notFound } from "next/navigation"
import { getSurveyDefinition, SurveyApiError, formatErrorMessage } from "@/lib/survey-api"
import { SurveyContainer } from "@/components/survey/survey-container"
import { SurveyLoadingSkeleton } from "@/components/survey/survey-loading-skeleton"
import { SurveyErrorBoundary } from "@/components/survey/survey-error-boundary"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle, RefreshCw } from "lucide-react"
import type { Survey } from "@/types/survey"

interface SurveyPageProps {
  params: Promise<{
    surveyCode: string
  }>
  searchParams: Promise<{
    user_id?: string
  }>
}

export default function SurveyPage({ params, searchParams }: SurveyPageProps) {
  const { surveyCode } = use(params)
  const { user_id } = use(searchParams)
  
  const [survey, setSurvey] = useState<Survey | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  // Load survey from backend API
  useEffect(() => {
    const loadSurvey = async () => {
      try {
        setLoading(true)
        setError(null)
        const surveyData = await getSurveyDefinition(surveyCode)
        setSurvey(surveyData)
      } catch (err) {
        console.error("Failed to load survey:", err)
        if (err instanceof SurveyApiError) {
          if (err.code === 'survey_not_found') {
            // Survey not found, trigger 404
            notFound()
          } else {
            setError(formatErrorMessage(err))
          }
        } else {
          setError("Failed to load survey. Please try again.")
        }
      } finally {
        setLoading(false)
      }
    }

    loadSurvey()
  }, [surveyCode, retryCount])

  const handleRetry = () => {
    setRetryCount(prev => prev + 1)
  }

  const handleComplete = (answers: any[]) => {
    console.log("Survey completed:", answers)
    // Survey completion is now handled by the SurveyContainer's backend integration
  }

  const handleSave = (answers: any[]) => {
    console.log("Survey progress saved:", answers)
    // Survey saving is now handled by the SurveyContainer's backend integration
  }

  const handleErrorReset = () => {
    setError(null)
    setRetryCount(prev => prev + 1)
  }

  // Show loading state
  if (loading) {
    return <SurveyLoadingSkeleton />
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md mx-auto">
          <CardContent className="pt-6 text-center space-y-4">
            <div className="mx-auto mb-4 w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-destructive" />
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Unable to Load Survey</h2>
              <p className="text-muted-foreground">{error}</p>
            </div>
            
            <div className="flex flex-col space-y-2 pt-4">
              <Button onClick={handleRetry} disabled={loading}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
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

  // Survey not loaded
  if (!survey) {
    notFound()
  }

  return (
    <SurveyErrorBoundary onReset={handleErrorReset}>
      <SurveyContainer 
        survey={survey} 
        userId={user_id} 
        onComplete={handleComplete} 
        onSave={handleSave} 
      />
    </SurveyErrorBoundary>
  )
}

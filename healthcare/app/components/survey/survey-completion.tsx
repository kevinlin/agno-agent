"use client"

import type { Survey } from "@/types/survey"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CheckCircle, Download, Share } from "lucide-react"
import { cn } from "@/lib/utils"

interface DerivedMetric {
  name: string
  value: string
  description?: string
  category?: "normal" | "warning" | "alert"
}

interface SurveyCompletionProps {
  survey: Survey
  derivedMetrics?: DerivedMetric[]
  onDownloadResults?: () => void
  onShareResults?: () => void
  onStartNewSurvey?: () => void
  className?: string
}

export function SurveyCompletion({
  survey,
  derivedMetrics = [],
  onDownloadResults,
  onShareResults,
  onStartNewSurvey,
  className,
}: SurveyCompletionProps) {
  const getMetricColor = (category?: string) => {
    switch (category) {
      case "warning":
        return "text-yellow-600 bg-yellow-50 border-yellow-200"
      case "alert":
        return "text-red-600 bg-red-50 border-red-200"
      default:
        return "text-green-600 bg-green-50 border-green-200"
    }
  }

  return (
    <div className={cn("w-full max-w-2xl mx-auto space-y-6", className)}>
      {/* Success Message */}
      <Card>
        <CardContent className="pt-8 pb-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="h-16 w-16 bg-primary/10 rounded-full flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-primary" />
            </div>
          </div>

          <h1 className="text-2xl font-bold text-foreground mb-2">Survey Complete!</h1>

          <p className="text-muted-foreground">
            Thank you for completing the {survey.title} survey. Your responses have been successfully submitted and
            processed.
          </p>
        </CardContent>
      </Card>

      {/* Derived Metrics */}
      {derivedMetrics.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {derivedMetrics.map((metric, index) => (
              <div key={index} className={cn("p-4 rounded-md border", getMetricColor(metric.category))}>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{metric.name}</h3>
                  <span className="text-lg font-bold">{metric.value}</span>
                </div>
                {metric.description && <p className="text-sm opacity-80">{metric.description}</p>}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <h3 className="font-semibold text-center mb-4">What's Next?</h3>

            <div className="grid gap-3 sm:grid-cols-2">
              {onDownloadResults && (
                <Button
                  variant="outline"
                  onClick={onDownloadResults}
                  className="flex items-center gap-2 bg-transparent"
                >
                  <Download className="h-4 w-4" />
                  Download Results
                </Button>
              )}

              {onShareResults && (
                <Button variant="outline" onClick={onShareResults} className="flex items-center gap-2 bg-transparent">
                  <Share className="h-4 w-4" />
                  Share Results
                </Button>
              )}
            </div>

            {onStartNewSurvey && (
              <Button onClick={onStartNewSurvey} className="w-full">
                Take Another Survey
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Additional Information */}
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-sm text-muted-foreground space-y-2">
            <p>
              Your responses are confidential and will be used to provide personalized health insights and
              recommendations.
            </p>
            <p>For questions about your results, please consult with a healthcare professional.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

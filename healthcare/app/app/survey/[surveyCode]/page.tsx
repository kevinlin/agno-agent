import { notFound } from "next/navigation"
import { getSurvey } from "@/lib/survey-data"
import { SurveyContainer } from "@/components/survey/survey-container"

interface SurveyPageProps {
  params: {
    surveyCode: string
  }
  searchParams: {
    user_id?: string
  }
}

export default function SurveyPage({ params, searchParams }: SurveyPageProps) {
  const survey = getSurvey(params.surveyCode)

  if (!survey) {
    notFound()
  }

  const handleComplete = (answers: any[]) => {
    console.log("Survey completed:", answers)
    // TODO: Submit to API
  }

  const handleSave = (answers: any[]) => {
    console.log("Survey progress saved:", answers)
    // TODO: Save to API
  }

  return <SurveyContainer survey={survey} onComplete={handleComplete} onSave={handleSave} />
}

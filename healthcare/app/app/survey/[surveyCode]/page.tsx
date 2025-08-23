"use client"

import { use } from "react"
import { notFound } from "next/navigation"
import { getSurvey } from "@/lib/survey-data"
import { SurveyContainer } from "@/components/survey/survey-container"

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
  
  const survey = getSurvey(surveyCode)

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

  return <SurveyContainer survey={survey} userId={user_id} onComplete={handleComplete} onSave={handleSave} />
}

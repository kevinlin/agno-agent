"use client"

import type { Question } from "@/types/survey"
import { QuestionInput } from "./question-input"
import { QuestionSingleSelect } from "./question-single-select"
import { QuestionMultipleSelect } from "./question-multiple-select"
import { QuestionDropdown } from "./question-dropdown"
import { QuestionTime } from "./question-time"

interface QuestionRendererProps {
  question: Question
  value?: any
  onChange: (value: any) => void
  className?: string
}

export function QuestionRenderer({ question, value, onChange, className }: QuestionRendererProps) {
  switch (question.type) {
    case "INPUT":
      return <QuestionInput question={question} value={value} onChange={onChange} className={className} />

    case "SINGLE_SELECT":
      return <QuestionSingleSelect question={question} value={value} onChange={onChange} className={className} />

    case "MULTIPLE_SELECT":
      return <QuestionMultipleSelect question={question} value={value} onChange={onChange} className={className} />

    case "DROPDOWN":
      return <QuestionDropdown question={question} value={value} onChange={onChange} className={className} />

    case "TIME":
      return <QuestionTime question={question} value={value} onChange={onChange} className={className} />

    default:
      return (
        <div className="p-4 border border-destructive rounded-md">
          <p className="text-destructive">Unsupported question type: {question.type}</p>
        </div>
      )
  }
}

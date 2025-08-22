"use client"

import { useState } from "react"
import type { Question } from "@/types/survey"
import { validateAnswer } from "@/lib/survey-validation"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

interface QuestionInputProps {
  question: Question
  value?: string | number
  onChange: (value: string | number) => void
  className?: string
}

export function QuestionInput({ question, value, onChange, className }: QuestionInputProps) {
  const [error, setError] = useState<string>()
  const [touched, setTouched] = useState(false)

  const handleChange = (inputValue: string) => {
    const processedValue =
      question.unit === "INTEGER_NUMBER"
        ? Number.parseInt(inputValue) || inputValue
        : question.unit === "DECIMAL_NUMBER"
          ? Number.parseFloat(inputValue) || inputValue
          : inputValue

    onChange(processedValue)

    if (touched) {
      const validation = validateAnswer(question, processedValue)
      setError(validation.error)
    }
  }

  const handleBlur = () => {
    setTouched(true)
    const validation = validateAnswer(question, value)
    setError(validation.error)
  }

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={question.code} className="text-sm font-medium text-foreground">
        {question.title}
        {question.required && <span className="text-destructive ml-1">*</span>}
      </Label>

      {question.subtitle && <p className="text-sm text-muted-foreground">{question.subtitle}</p>}

      <div className="relative">
        <Input
          id={question.code}
          type={question.unit ? "number" : "text"}
          value={value || ""}
          onChange={(e) => handleChange(e.target.value)}
          onBlur={handleBlur}
          placeholder={question.unit_text ? `Enter value in ${question.unit_text}` : ""}
          className={cn("pr-12", error && "border-destructive focus-visible:ring-destructive")}
          min={question.constraints?.min}
          max={question.constraints?.max}
          step={question.unit === "DECIMAL_NUMBER" ? "0.1" : "1"}
        />

        {question.unit_text && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
            {question.unit_text}
          </div>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {question.help && !error && <p className="text-sm text-muted-foreground">{question.help}</p>}
    </div>
  )
}

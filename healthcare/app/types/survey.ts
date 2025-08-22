export interface SurveyAnswer {
  question_code: string
  value: any
}

export interface SurveySession {
  survey_code: string
  user_id: string
  current_question_index: number
  answers: SurveyAnswer[]
  completed_at?: string
  created_at: string
  updated_at: string
}

export interface QuestionConstraints {
  min?: number
  max?: number
  minLength?: number
  maxLength?: number
}

export interface AnswerOption {
  code: string
  title: string
}

export interface QuestionAnswers {
  answers: AnswerOption[]
  exclusiveOptions?: string[]
}

export interface Question {
  type: "INPUT" | "SINGLE_SELECT" | "MULTIPLE_SELECT" | "DROPDOWN" | "TIME"
  code: string
  title: string
  required?: boolean
  unit?: "INTEGER_NUMBER" | "DECIMAL_NUMBER" | "TEXT" | "MINUTES"
  unit_text?: string
  constraints?: QuestionConstraints
  answers?: QuestionAnswers
  visibility_conditions?: Array<{
    question_code: string
    operator: "equals" | "not_equals" | "contains" | "not_contains"
    value: any
  }>
}

export interface BranchingRule {
  condition: {
    question_code: string
    operator: "equals" | "not_equals" | "contains" | "not_contains"
    value: any
  }
  action: {
    type: "skip_to" | "show" | "hide"
    target: string
  }
}

export interface Survey {
  code: string
  type: string
  version: string
  title: string
  description?: string
  questions: Question[]
  branching_rules?: BranchingRule[]
}

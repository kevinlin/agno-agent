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
  subtitle?: string
  required?: boolean
  unit?: "INTEGER_NUMBER" | "DECIMAL_NUMBER" | "TEXT" | "MINUTES"
  unit_text?: string
  constraints?: QuestionConstraints
  answers?: QuestionAnswers
  visible_if?: Condition
  help?: string
}

export type ConditionOperator = 
  | "equals" 
  | "one_of" 
  | "includes" 
  | "gt" 
  | "gte" 
  | "lt" 
  | "lte" 
  | "and" 
  | "or" 
  | "not"

export interface Condition {
  operator: ConditionOperator
  question_code?: string
  value?: any
  conditions?: Condition[]
}

export type ActionType = 
  | "skip_questions" 
  | "goto_question" 
  | "insert_questions_after" 
  | "require_questions"

export interface BranchingAction {
  type: ActionType
  target: string | string[]
  data?: Record<string, any>
}

export interface BranchingRule {
  id: string
  condition: Condition
  action: BranchingAction
  priority?: number
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

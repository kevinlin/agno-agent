import type { Survey, Question } from "@/types/survey"

// Import the survey data from the JSON file
const personalizationSurveyData = {
  code: "personalization",
  type: "PERSONALIZATION",
  version: "1.0.0",
  title: "Personalization",
  description: "Complete this health assessment to get personalized insights and recommendations.",
  questions: [
    {
      type: "INPUT" as const,
      code: "height_cm",
      title: "What's your height?",
      required: true,
      unit: "INTEGER_NUMBER" as const,
      unit_text: "cm",
      constraints: { min: 80, max: 250 },
    },
    {
      type: "INPUT" as const,
      code: "weight_kg",
      title: "What's your current weight?",
      required: true,
      unit: "DECIMAL_NUMBER" as const,
      unit_text: "kg",
      constraints: { min: 20, max: 300 },
    },
    {
      type: "MULTIPLE_SELECT" as const,
      code: "conditions",
      title: "I have ...",
      answers: {
        answers: [
          { code: "diabetes", title: "Diabetes" },
          { code: "allergy", title: "Allergy" },
          { code: "stroke", title: "Stroke" },
          { code: "pad", title: "Peripheral artery disease" },
          { code: "digestive_disorder", title: "Digestive disorder" },
          { code: "asthma", title: "Asthma" },
          { code: "heart_attack", title: "Heart attack" },
          { code: "angina", title: "Angina" },
          { code: "heart_failure", title: "Heart Failure" },
          { code: "liver_disease", title: "Liver disease" },
          { code: "kidney_stones", title: "Kidney stones" },
          { code: "hypertension", title: "Hypertension" },
          { code: "rheumatoid_arthritis", title: "Rheumatoid arthritis" },
          { code: "cancer", title: "Cancer" },
          { code: "anemia", title: "Anemia" },
          { code: "meds_hypertension", title: "Medication for high blood pressure" },
          { code: "tia", title: "Transient Ischemic Attack (TIA)" },
          { code: "heart_disease", title: "Heart disease" },
          { code: "intermittent_claudication", title: "Intermittent claudication" },
          { code: "lupus", title: "Lupus" },
          { code: "dry_skin_hair", title: "Dry Skin and Hair concern" },
          { code: "none", title: "None of the above" },
        ],
        exclusiveOptions: ["none"],
      },
    },
    {
      type: "MULTIPLE_SELECT" as const,
      code: "family_conditions",
      title: "My family has ...",
      answers: {
        answers: [
          { code: "fh_cvd", title: "Cardiovascular disease" },
          { code: "fh_anemia", title: "Anemia" },
          { code: "fh_kidney_disease", title: "Kidney disease" },
          { code: "fh_allergy", title: "Allergy" },
          { code: "fh_hypertension", title: "Hypertension" },
          { code: "fh_diabetes", title: "Diabetes" },
          { code: "fh_stroke", title: "Stroke" },
          { code: "fh_liver_disease", title: "Liver disease" },
          { code: "fh_liver_cancer", title: "Liver cancer" },
          { code: "fh_prostate_cancer", title: "Prostate cancer" },
          { code: "fh_breast_cancer", title: "Breast cancer" },
          { code: "fh_colorectal_cancer", title: "Colorectal cancer" },
          { code: "fh_pancreatic_cancer", title: "Pancreatic cancer" },
          { code: "fh_stomach_cancer", title: "Stomach cancer" },
          { code: "fh_nasopharyngeal_cancer", title: "Nasopharyngeal cancer" },
          { code: "fh_bladder_cancer", title: "Bladder cancer" },
          { code: "fh_cervical_cancer", title: "Cervical cancer" },
          { code: "fh_thyroid_cancer", title: "Thyroid cancer" },
          { code: "fh_others", title: "Other cancers" },
          { code: "fh_none", title: "None of the above" },
        ],
        exclusiveOptions: ["fh_none"],
      },
    },
    {
      type: "SINGLE_SELECT" as const,
      code: "smoke_status",
      title: "Do you smoke?",
      required: true,
      answers: {
        answers: [
          { code: "current", title: "Yes, I currently smoke" },
          { code: "quit", title: "No, I quit smoking" },
          { code: "never", title: "No, I don't smoke" },
        ],
      },
    },
    {
      type: "SINGLE_SELECT" as const,
      code: "sedentary_8h",
      title: "Do you spend more than 8 hours indoor or in a car?",
      answers: {
        answers: [
          { code: "yes", title: "Yes" },
          { code: "no", title: "No" },
        ],
      },
    },
    {
      type: "SINGLE_SELECT" as const,
      code: "marital_status",
      title: "Are you married?",
      answers: {
        answers: [
          { code: "planning", title: "I'm planning to get married" },
          { code: "married", title: "I am married" },
          { code: "none", title: "None of the above" },
        ],
      },
    },
    {
      type: "SINGLE_SELECT" as const,
      code: "sex_active",
      title: "Are you currently sexually active?",
      answers: {
        answers: [
          { code: "yes", title: "Yes, I am" },
          { code: "no", title: "No, I am not" },
          { code: "prefer_not", title: "Prefer not to say" },
        ],
      },
    },
  ],
  branching_rules: [],
}

// Available surveys
const surveys: Survey[] = [personalizationSurveyData as Survey]

export function getAllSurveys(): Survey[] {
  return surveys
}

export function getSurveyByCode(code: string): Survey | undefined {
  return surveys.find((survey) => survey.code === code)
}

export function getSurvey(code: string): Survey | undefined {
  return getSurveyByCode(code)
}

export function getVisibleQuestions(survey: Survey, answers: Record<string, any>): Question[] {
  // For now, return all questions since there are no branching rules in the sample data
  // This function can be extended to handle conditional logic based on branching_rules
  return survey.questions.filter((question) => {
    // Check visibility conditions if they exist
    if (question.visibility_conditions) {
      return question.visibility_conditions.every((condition) => {
        const answerValue = answers[condition.question_code]

        switch (condition.operator) {
          case "equals":
            return answerValue === condition.value
          case "not_equals":
            return answerValue !== condition.value
          case "contains":
            return Array.isArray(answerValue) && answerValue.includes(condition.value)
          case "not_contains":
            return !Array.isArray(answerValue) || !answerValue.includes(condition.value)
          default:
            return true
        }
      })
    }

    return true
  })
}

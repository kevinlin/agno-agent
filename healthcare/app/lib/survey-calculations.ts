import type { Question } from "@/types/survey"

interface DerivedMetric {
  name: string
  value: string
  description?: string
  category?: "normal" | "warning" | "alert"
}

export function calculateDerivedMetrics(questions: Question[], answers: Record<string, any>): DerivedMetric[] {
  const metrics: DerivedMetric[] = []

  // Calculate BMI if height and weight are available
  const height = answers["height_cm"]
  const weight = answers["weight_kg"]

  if (height && weight && typeof height === "number" && typeof weight === "number") {
    const heightInMeters = height / 100
    const bmi = weight / (heightInMeters * heightInMeters)

    let category: "normal" | "warning" | "alert" = "normal"
    let description = ""

    if (bmi < 18.5) {
      category = "warning"
      description = "Underweight - Consider consulting with a healthcare provider about healthy weight gain strategies."
    } else if (bmi >= 18.5 && bmi < 25) {
      category = "normal"
      description = "Normal weight - Maintain your current healthy lifestyle."
    } else if (bmi >= 25 && bmi < 30) {
      category = "warning"
      description = "Overweight - Consider lifestyle changes to achieve a healthier weight."
    } else {
      category = "alert"
      description = "Obese - Consult with a healthcare provider about weight management strategies."
    }

    metrics.push({
      name: "Body Mass Index (BMI)",
      value: bmi.toFixed(1),
      description,
      category,
    })
  }

  // Calculate risk factors based on conditions
  const conditions = answers["conditions"]
  if (Array.isArray(conditions) && conditions.length > 0 && !conditions.includes("none")) {
    const riskConditions = conditions.filter((c) => c !== "none")
    let category: "normal" | "warning" | "alert" = "normal"

    if (riskConditions.length >= 3) {
      category = "alert"
    } else if (riskConditions.length >= 1) {
      category = "warning"
    }

    metrics.push({
      name: "Health Conditions",
      value: `${riskConditions.length} condition${riskConditions.length !== 1 ? "s" : ""}`,
      description:
        riskConditions.length > 0
          ? "Regular monitoring and healthcare provider consultation recommended."
          : "No significant health conditions reported.",
      category,
    })
  }

  // Smoking risk assessment
  const smokingStatus = answers["smoke_status"]
  if (smokingStatus) {
    let category: "normal" | "warning" | "alert" = "normal"
    let description = ""

    switch (smokingStatus) {
      case "current":
        category = "alert"
        description = "Current smoking significantly increases health risks. Consider smoking cessation programs."
        break
      case "quit":
        category = "warning"
        description = "Great job on quitting! Continue to avoid smoking to maintain health benefits."
        break
      case "never":
        category = "normal"
        description = "Excellent! Non-smoking is one of the best choices for long-term health."
        break
    }

    metrics.push({
      name: "Smoking Status",
      value: smokingStatus === "current" ? "Current Smoker" : smokingStatus === "quit" ? "Former Smoker" : "Non-Smoker",
      description,
      category,
    })
  }

  return metrics
}

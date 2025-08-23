import Link from "next/link"
import { getSurveysWithDefinitionsServer } from "@/lib/survey-api-server"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default async function HomePage() {
  // Fetch surveys from the backend API
  let surveys = []
  try {
    surveys = await getSurveysWithDefinitionsServer()
  } catch (error) {
    console.error('Failed to load surveys:', error)
    // Return error state if surveys can't be loaded
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-foreground mb-4">Health Assessment Surveys</h1>
            <p className="text-red-500 mb-4">
              Unable to load surveys. Please check if the backend server is running.
            </p>
            <p className="text-muted-foreground">
              Try refreshing the page or contact support if the problem persists.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-4">Health Assessment Surveys</h1>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Complete our comprehensive health surveys to get personalized insights and recommendations for your
            wellbeing.
          </p>
        </div>

        {surveys.length === 0 ? (
          <div className="text-center">
            <p className="text-muted-foreground">No surveys available at the moment.</p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 max-w-4xl mx-auto">
            {surveys.map((survey) => (
              <Card key={survey.code} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="text-lg">{survey.title}</CardTitle>
                  <div className="text-sm text-muted-foreground">
                    {survey.type.replace("_", " ").toLowerCase()}
                  </div>
                </CardHeader>
                <CardContent>
                  {survey.description && (
                    <p className="text-sm text-muted-foreground mb-4">{survey.description}</p>
                  )}
                  <Link href={`/survey/${survey.code}?user_id=demo`}>
                    <Button className="w-full">Start Survey</Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

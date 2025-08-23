"use client"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "../ui/skeleton"
import { cn } from "@/lib/utils"

interface SurveyLoadingSkeletonProps {
  className?: string
}

export function SurveyLoadingSkeleton({ className }: SurveyLoadingSkeletonProps) {
  return (
    <div className={cn("min-h-screen bg-background", className)}>
      {/* App Bar Skeleton */}
      <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Skeleton className="h-6 w-6" />
              <div className="space-y-1">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Skeleton className="h-2 w-24" />
              <Skeleton className="h-4 w-8" />
            </div>
          </div>
          <div className="mt-4">
            <Skeleton className="h-2 w-full rounded-full" />
          </div>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar Skeleton */}
        <div className="hidden lg:block w-80 border-r bg-background">
          <div className="p-4 space-y-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-2 w-full" />
            </div>
            
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center space-x-3 p-2 rounded-lg">
                  <Skeleton className="h-6 w-6 rounded-full" />
                  <div className="flex-1 space-y-1">
                    <Skeleton className="h-3 w-3/4" />
                    <Skeleton className="h-2 w-1/2" />
                  </div>
                  <Skeleton className="h-4 w-4" />
                </div>
              ))}
            </div>

            <div className="pt-4 border-t">
              <Skeleton className="h-8 w-full" />
            </div>
          </div>
        </div>

        {/* Main Content Skeleton */}
        <div className="flex-1">
          <div className="container mx-auto px-4 py-8 space-y-6">
            <Card className="w-full max-w-2xl mx-auto">
              <CardHeader>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Skeleton className="h-4 w-16" />
                    <Skeleton className="h-4 w-12" />
                  </div>
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  {/* Question content skeleton */}
                  <div className="space-y-3">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                  
                  {/* Input/Options skeleton */}
                  <div className="space-y-2">
                    <Skeleton className="h-10 w-full" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Navigation Skeleton */}
            <div className="w-full max-w-2xl mx-auto">
              <div className="flex justify-between items-center">
                <Skeleton className="h-10 w-24" />
                <Skeleton className="h-10 w-24" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function SurveyQuestionSkeleton() {
  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-12" />
          </div>
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <Skeleton className="h-10 w-full" />
      </CardContent>
    </Card>
  )
}

export function SurveyProgressSkeleton() {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-2 w-full" />
      </div>
      
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex items-center space-x-3 p-2 rounded-lg">
            <Skeleton className="h-6 w-6 rounded-full" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-2 w-1/2" />
            </div>
            <Skeleton className="h-4 w-4" />
          </div>
        ))}
      </div>

      <div className="pt-4 border-t">
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  )
}

export function SurveyReviewSkeleton() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <Skeleton className="h-8 w-64 mx-auto" />
        <Skeleton className="h-4 w-96 mx-auto" />
      </div>

      <div className="space-y-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="flex justify-between items-start">
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-5 w-2/3" />
                </div>
                <Skeleton className="h-8 w-16" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-center pt-6">
        <Skeleton className="h-10 w-32" />
      </div>
    </div>
  )
}

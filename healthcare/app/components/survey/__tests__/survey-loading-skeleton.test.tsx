import React from 'react'
import { render, screen } from '@testing-library/react'
import { 
  SurveyLoadingSkeleton, 
  SurveyQuestionSkeleton, 
  SurveyProgressSkeleton,
  SurveyReviewSkeleton 
} from '../survey-loading-skeleton'

describe('Survey Loading Skeletons', () => {
  describe('SurveyLoadingSkeleton', () => {
    it('renders main survey loading skeleton', () => {
      const { container } = render(<SurveyLoadingSkeleton />)
      
      // Should render the main container with the expected class
      expect(container.querySelector('.min-h-screen')).toBeInTheDocument()
    })

    it('applies custom className', () => {
      const { container } = render(<SurveyLoadingSkeleton className="custom-class" />)
      
      expect(container.firstChild).toHaveClass('custom-class')
    })
  })

  describe('SurveyQuestionSkeleton', () => {
    it('renders question skeleton structure', () => {
      render(<SurveyQuestionSkeleton />)
      
      // Should render card structure
      const cards = document.querySelectorAll('[class*="border"]')
      expect(cards.length).toBeGreaterThan(0)
    })
  })

  describe('SurveyProgressSkeleton', () => {
    it('renders progress skeleton with multiple items', () => {
      render(<SurveyProgressSkeleton />)
      
      // Should render multiple skeleton items for progress
      const skeletonItems = document.querySelectorAll('[class*="animate-pulse"]')
      expect(skeletonItems.length).toBeGreaterThan(5)
    })
  })

  describe('SurveyReviewSkeleton', () => {
    it('renders review skeleton with card structure', () => {
      render(<SurveyReviewSkeleton />)
      
      // Should render multiple card items for review
      const skeletonItems = document.querySelectorAll('[class*="animate-pulse"]')
      expect(skeletonItems.length).toBeGreaterThan(3)
    })
  })
})

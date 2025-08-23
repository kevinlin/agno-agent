import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SurveyErrorBoundary } from '../survey-error-boundary'

// Mock a component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error')
  }
  return <div>No error</div>
}

describe('SurveyErrorBoundary', () => {
  beforeEach(() => {
    // Suppress console.error for these tests since we're testing error conditions
    jest.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  it('renders children when there is no error', () => {
    render(
      <SurveyErrorBoundary>
        <ThrowError shouldThrow={false} />
      </SurveyErrorBoundary>
    )

    expect(screen.getByText('No error')).toBeInTheDocument()
  })

  it('renders error UI when child component throws', () => {
    render(
      <SurveyErrorBoundary>
        <ThrowError shouldThrow={true} />
      </SurveyErrorBoundary>
    )

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText(/We encountered an unexpected error/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /go back/i })).toBeInTheDocument()
  })

  it('calls onReset when try again button is clicked', async () => {
    const user = userEvent.setup()
    const onReset = jest.fn()

    render(
      <SurveyErrorBoundary onReset={onReset}>
        <ThrowError shouldThrow={true} />
      </SurveyErrorBoundary>
    )

    const tryAgainButton = screen.getByRole('button', { name: /try again/i })
    await user.click(tryAgainButton)

    expect(onReset).toHaveBeenCalledTimes(1)
  })

  it('renders custom fallback when provided', () => {
    const fallback = <div>Custom error message</div>

    render(
      <SurveyErrorBoundary fallback={fallback}>
        <ThrowError shouldThrow={true} />
      </SurveyErrorBoundary>
    )

    expect(screen.getByText('Custom error message')).toBeInTheDocument()
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()
  })

  it('shows error details in development mode', () => {
    // Mock NODE_ENV for this test
    const originalEnv = process.env.NODE_ENV
    process.env.NODE_ENV = 'development'

    render(
      <SurveyErrorBoundary>
        <ThrowError shouldThrow={true} />
      </SurveyErrorBoundary>
    )

    expect(screen.getByText('Error Details (Development)')).toBeInTheDocument()

    // Restore original environment
    process.env.NODE_ENV = originalEnv
  })
})

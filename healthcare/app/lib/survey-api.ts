"use client"

/**
 * Survey API Client Functions
 * 
 * This module provides TypeScript functions for interacting with the healthcare
 * survey backend API. It includes proper error handling, retry logic, and 
 * optimistic updates for a seamless user experience.
 */

// Types for API requests and responses
export interface ApiError {
  ok: false
  error: {
    code: string
    message: string
    details?: string
  }
}

export interface SurveyCatalogItem {
  id: string
  code: string
  title: string
  type: string
  active_version: string
}

export interface SurveyResponseStatus {
  ok: true
  status: "in_progress" | "completed" | "cancelled"
  progress_pct: number
  user_response: Record<string, any>
}

export interface SaveSurveyResponseRequest {
  user_response: Record<string, any>
  status?: "in_progress" | "completed"
}

export interface SaveSurveyResponseResponse {
  ok: true
  progress_pct: number
  status: "in_progress" | "completed" | "cancelled"
}

export interface SurveyLinkRequest {
  user_id: string
  survey_code: string
}

export interface SurveyLinkResponse {
  ok: true
  survey_url: string
  user_id: string
  survey_code: string
}

// Configuration for API client
const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000, // 10 seconds
  retryAttempts: 3,
  retryDelay: 1000, // 1 second
}

/**
 * Custom error class for API errors
 */
export class SurveyApiError extends Error {
  public code: string;
  public details?: string;
  public status?: number;

  constructor(
    code: string,
    message: string,
    details?: string,
    status?: number
  ) {
    super(message);
    this.name = 'SurveyApiError';
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

/**
 * Utility function to handle fetch with timeout and error handling
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = API_CONFIG.timeout
): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    clearTimeout(timeoutId)
    return response
  } catch (error) {
    clearTimeout(timeoutId)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new SurveyApiError('timeout', 'Request timed out')
    }
    throw error
  }
}

/**
 * Utility function to handle API responses and errors
 */
async function handleApiResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type')
  
  if (!contentType?.includes('application/json')) {
    throw new SurveyApiError(
      'invalid_response',
      'Invalid response format',
      'Expected JSON response',
      response.status
    )
  }

  const data = await response.json()

  if (!response.ok) {
    // Handle API error responses
    if (data.ok === false && data.error) {
      throw new SurveyApiError(
        data.error.code,
        data.error.message,
        data.error.details,
        response.status
      )
    }
    
    throw new SurveyApiError(
      'http_error',
      `HTTP ${response.status}`,
      response.statusText,
      response.status
    )
  }

  return data
}

/**
 * Retry wrapper with exponential backoff
 */
async function withRetry<T>(
  fn: () => Promise<T>,
  attempts: number = API_CONFIG.retryAttempts,
  delay: number = API_CONFIG.retryDelay
): Promise<T> {
  let lastError: Error

  for (let i = 0; i < attempts; i++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error as Error
      
      // Don't retry on client errors (4xx)
      if (error instanceof SurveyApiError && error.status && error.status >= 400 && error.status < 500) {
        throw error
      }
      
      if (i < attempts - 1) {
        // Wait before retrying with exponential backoff
        await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)))
      }
    }
  }

  throw lastError!
}

// Survey Catalog API Functions

/**
 * Get list of all surveys
 */
export async function getSurveyCatalog(type?: string): Promise<SurveyCatalogItem[]> {
  const url = new URL(`${API_CONFIG.baseUrl}/api/survey`)
  if (type) {
    url.searchParams.set('type', type)
  }

  return withRetry(async () => {
    const response = await fetchWithTimeout(url.toString())
    return handleApiResponse<SurveyCatalogItem[]>(response)
  })
}

/**
 * Get surveys with full definitions for homepage display
 * This function fetches the catalog and then loads the full definition for each survey
 */
export async function getSurveysWithDefinitions(type?: string): Promise<any[]> {
  // First get the catalog
  const catalog = await getSurveyCatalog(type)
  
  // Then load full definitions for each survey
  const surveys = await Promise.all(
    catalog.map(async (item) => {
      try {
        const definition = await getSurveyDefinition(item.code)
        return {
          ...definition,
          // Ensure we have catalog metadata
          id: item.id,
          active_version: item.active_version,
        }
      } catch (error) {
        console.error(`Failed to load definition for survey ${item.code}:`, error)
        // Return basic info if definition fails to load
        return {
          code: item.code,
          title: item.title,
          type: item.type,
          version: item.active_version,
          description: `Failed to load survey definition`,
          questions: [],
          branching_rules: [],
        }
      }
    })
  )
  
  return surveys
}

/**
 * Get full survey definition by code
 */
export async function getSurveyDefinition(code: string): Promise<any> {
  const url = `${API_CONFIG.baseUrl}/api/survey/${encodeURIComponent(code)}`

  return withRetry(async () => {
    const response = await fetchWithTimeout(url)
    return handleApiResponse<any>(response)
  })
}

/**
 * Create a new survey
 */
export async function createSurvey(surveyData: {
  code: string
  title: string
  version: string
  type: string
  description?: string
  definition: any
}): Promise<{ ok: true; survey_id: string; message: string }> {
  const url = `${API_CONFIG.baseUrl}/api/survey`

  return withRetry(async () => {
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      body: JSON.stringify(surveyData),
    })
    return handleApiResponse<{ ok: true; survey_id: string; message: string }>(response)
  })
}

// Survey Response API Functions

/**
 * Get existing survey response with status and answers
 */
export async function getSurveyResponse(
  userId: string,
  surveyCode: string
): Promise<SurveyResponseStatus> {
  const url = new URL(`${API_CONFIG.baseUrl}/api/survey-response`)
  url.searchParams.set('user_id', userId)
  url.searchParams.set('survey_code', surveyCode)

  return withRetry(async () => {
    const response = await fetchWithTimeout(url.toString())
    return handleApiResponse<SurveyResponseStatus>(response)
  })
}

/**
 * Save complete survey response (handles both partial and complete saves)
 */
export async function saveSurveyResponse(
  userId: string,
  surveyCode: string,
  userResponse: Record<string, any>,
  status?: "in_progress" | "completed"
): Promise<SaveSurveyResponseResponse> {
  const url = new URL(`${API_CONFIG.baseUrl}/api/survey-response`)
  url.searchParams.set('user_id', userId)
  url.searchParams.set('survey_code', surveyCode)

  const requestBody: SaveSurveyResponseRequest = {
    user_response: userResponse,
    ...(status && { status })
  }

  return withRetry(async () => {
    const response = await fetchWithTimeout(url.toString(), {
      method: 'POST',
      body: JSON.stringify(requestBody),
    })
    return handleApiResponse<SaveSurveyResponseResponse>(response)
  })
}

/**
 * Complete a survey response and calculate derived metrics
 */
export async function completeSurveyResponse(
  userId: string,
  surveyCode: string,
  userResponse: Record<string, any>
): Promise<SaveSurveyResponseResponse> {
  return saveSurveyResponse(userId, surveyCode, userResponse, "completed")
}

// Agent Integration API Functions

/**
 * Generate signed survey URLs for agent integration
 */
export async function generateSurveyLink(
  userId: string,
  surveyCode: string
): Promise<SurveyLinkResponse> {
  const url = `${API_CONFIG.baseUrl}/api/survey-links`

  return withRetry(async () => {
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        survey_code: surveyCode,
      }),
    })
    return handleApiResponse<SurveyLinkResponse>(response)
  })
}

// Utility Functions

/**
 * Check if error is a network error (for retry logic)
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof SurveyApiError) {
    return error.code === 'timeout' || (error.status !== undefined && error.status >= 500)
  }
  return error instanceof TypeError && error.message.includes('fetch')
}

/**
 * Check if error is a client error (no retry needed)
 */
export function isClientError(error: unknown): boolean {
  if (error instanceof SurveyApiError) {
    return error.status !== undefined && error.status >= 400 && error.status < 500
  }
  return false
}

/**
 * Format error message for user display
 */
export function formatErrorMessage(error: unknown): string {
  if (error instanceof SurveyApiError) {
    switch (error.code) {
      case 'timeout':
        return 'Request timed out. Please check your connection and try again.'
      case 'survey_not_found':
        return 'Survey not found. Please check the survey code.'
      case 'invalid_response':
        return 'Invalid server response. Please try again later.'
      default:
        return error.message || 'An unexpected error occurred.'
    }
  }
  
  return 'An unexpected error occurred. Please try again.'
}

// Export configuration for testing
export { API_CONFIG }

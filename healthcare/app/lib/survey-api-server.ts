/**
 * Server-side Survey API Functions
 * 
 * This module provides server-side functions for fetching surveys from the backend API.
 * These functions can be used in Server Components for SSR.
 */

import { Survey } from "@/types/survey"

// Configuration for API client
const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000, // 10 seconds
}

// Types for API responses
export interface SurveyCatalogItem {
  id: string
  code: string
  title: string
  type: string
  active_version: string
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
 * Server-side fetch with timeout and error handling
 */
async function serverFetch(
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
 * Handle API responses and errors for server-side calls
 */
async function handleServerApiResponse<T>(response: Response): Promise<T> {
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
 * Get list of all surveys (server-side)
 */
export async function getSurveyCatalogServer(type?: string): Promise<SurveyCatalogItem[]> {
  const url = new URL(`${API_CONFIG.baseUrl}/api/survey`)
  if (type) {
    url.searchParams.set('type', type)
  }

  try {
    const response = await serverFetch(url.toString())
    return handleServerApiResponse<SurveyCatalogItem[]>(response)
  } catch (error) {
    console.error('Failed to fetch survey catalog:', error)
    throw error
  }
}

/**
 * Get full survey definition by code (server-side)
 */
export async function getSurveyDefinitionServer(code: string): Promise<Survey> {
  const url = `${API_CONFIG.baseUrl}/api/survey/${encodeURIComponent(code)}`

  try {
    const response = await serverFetch(url)
    return handleServerApiResponse<Survey>(response)
  } catch (error) {
    console.error(`Failed to fetch survey definition for ${code}:`, error)
    throw error
  }
}

/**
 * Get surveys with full definitions for homepage display (server-side)
 * This function fetches the catalog and then loads the full definition for each survey
 */
export async function getSurveysWithDefinitionsServer(type?: string): Promise<Survey[]> {
  try {
    // First get the catalog
    const catalog = await getSurveyCatalogServer(type)
    
    // Then load full definitions for each survey
    const surveys = await Promise.all(
      catalog.map(async (item) => {
        try {
          const definition = await getSurveyDefinitionServer(item.code)
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
  } catch (error) {
    console.error('Failed to fetch surveys with definitions:', error)
    throw error
  }
}

/**
 * Format error message for user display
 */
export function formatServerErrorMessage(error: unknown): string {
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

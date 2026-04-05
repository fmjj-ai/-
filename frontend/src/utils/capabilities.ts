import request from './request'

export interface CapabilityResponse<T = Record<string, any>> {
  success: boolean
  data?: T
  error?: {
    error_code: string
    message: string
    debug_info?: Record<string, any> | null
    suggestion?: string | null
  }
}

export const getQuickCleaningCapabilities = () =>
  request.get<any, CapabilityResponse>('/quick-cleaning/capabilities')

export const getChartCalculationCapabilities = () =>
  request.get<any, CapabilityResponse>('/chart-calculations/capabilities')

export const getThemePaletteCapabilities = () =>
  request.get<any, CapabilityResponse>('/theme-palettes/capabilities')

export const getQuickReportCapabilities = () =>
  request.get<any, CapabilityResponse>('/quick-reports/capabilities')

/**
 * Time formatting utilities for human-friendly display
 *
 * Provides relative time ("2 hours ago"), duration ("1h 23m"), and
 * full timestamp formatting with consistent behavior across the app.
 */

/**
 * Format a date as relative time ("2 hours ago", "3 days ago", etc.)
 * Shows "just now" for times less than 1 minute ago.
 *
 * @param date - Date string, Date object, or timestamp
 * @returns Human-readable relative time string
 */
export function formatRelativeTime(date: string | Date | number | null | undefined): string {
  if (!date) return '-'

  const now = new Date()
  const then = new Date(date)

  // Handle invalid dates
  if (isNaN(then.getTime())) return '-'

  const diffMs = now.getTime() - then.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)
  const diffWeek = Math.floor(diffDay / 7)
  const diffMonth = Math.floor(diffDay / 30)

  // Future dates
  if (diffMs < 0) {
    return 'in the future'
  }

  // Less than 1 minute
  if (diffSec < 60) {
    return 'just now'
  }

  // Less than 1 hour
  if (diffMin < 60) {
    return diffMin === 1 ? '1 minute ago' : `${diffMin} minutes ago`
  }

  // Less than 1 day
  if (diffHour < 24) {
    return diffHour === 1 ? '1 hour ago' : `${diffHour} hours ago`
  }

  // Less than 1 week
  if (diffDay < 7) {
    return diffDay === 1 ? 'yesterday' : `${diffDay} days ago`
  }

  // Less than 1 month
  if (diffWeek < 4) {
    return diffWeek === 1 ? '1 week ago' : `${diffWeek} weeks ago`
  }

  // Less than 1 year
  if (diffMonth < 12) {
    return diffMonth === 1 ? '1 month ago' : `${diffMonth} months ago`
  }

  // More than 1 year - fall back to full date
  return formatTimestamp(then)
}

/**
 * Format duration between two dates as human-readable string
 * Examples: "1h 23m", "45m 12s", "2d 3h"
 *
 * @param start - Start date
 * @param end - End date (defaults to now)
 * @returns Human-readable duration string
 */
export function formatDuration(
  start: string | Date | number | null | undefined,
  end?: string | Date | number | null
): string {
  if (!start) return '-'

  const startDate = new Date(start)
  const endDate = end ? new Date(end) : new Date()

  // Handle invalid dates
  if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) return '-'

  const diffMs = endDate.getTime() - startDate.getTime()

  // Negative duration
  if (diffMs < 0) return '-'

  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  // Less than 1 minute - show seconds
  if (diffMin < 1) {
    return `${diffSec}s`
  }

  // Less than 1 hour - show minutes and seconds
  if (diffHour < 1) {
    const mins = diffMin
    const secs = diffSec % 60
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`
  }

  // Less than 1 day - show hours and minutes
  if (diffDay < 1) {
    const hours = diffHour
    const mins = diffMin % 60
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
  }

  // 1+ days - show days and hours
  const days = diffDay
  const hours = diffHour % 24
  return hours > 0 ? `${days}d ${hours}h` : `${days}d`
}

/**
 * Format a date as a full timestamp for tooltips and detailed views
 * Uses the user's locale for formatting.
 *
 * @param date - Date string, Date object, or timestamp
 * @returns Full localized timestamp string
 */
export function formatTimestamp(date: string | Date | number | null | undefined): string {
  if (!date) return '-'

  const d = new Date(date)

  // Handle invalid dates
  if (isNaN(d.getTime())) return '-'

  return d.toLocaleString()
}

/**
 * Format a date as time only (for logs, status updates)
 *
 * @param date - Date string, Date object, or timestamp
 * @returns Localized time string (e.g., "2:30:45 PM")
 */
export function formatTime(date: string | Date | number | null | undefined): string {
  if (!date) return '-'

  const d = new Date(date)

  // Handle invalid dates
  if (isNaN(d.getTime())) return '-'

  return d.toLocaleTimeString()
}

/**
 * Format a date as date only
 *
 * @param date - Date string, Date object, or timestamp
 * @returns Localized date string (e.g., "12/31/2025")
 */
export function formatDate(date: string | Date | number | null | undefined): string {
  if (!date) return '-'

  const d = new Date(date)

  // Handle invalid dates
  if (isNaN(d.getTime())) return '-'

  return d.toLocaleDateString()
}

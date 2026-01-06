import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export type TextSize = 'default' | 'large' | 'larger'

export interface UserPreferences {
  reduceMotion: boolean
  textSize: TextSize
  highContrast: boolean
}

interface PreferencesContextType {
  preferences: UserPreferences
  updatePreferences: (updates: Partial<UserPreferences>) => void
}

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined)

const STORAGE_KEY = 'pbs-wisconsin-preferences'

const DEFAULT_PREFERENCES: UserPreferences = {
  reduceMotion: false,
  textSize: 'default',
  highContrast: false,
}

/**
 * Detect system preferences for accessibility
 */
function getSystemPreferences(): Partial<UserPreferences> {
  const systemPrefs: Partial<UserPreferences> = {}

  // Check for prefers-reduced-motion
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    systemPrefs.reduceMotion = true
  }

  // Check for prefers-contrast
  if (window.matchMedia('(prefers-contrast: more)').matches) {
    systemPrefs.highContrast = true
  }

  return systemPrefs
}

/**
 * Load preferences from localStorage, falling back to system preferences
 */
function loadPreferences(): UserPreferences {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return { ...DEFAULT_PREFERENCES, ...parsed }
    }
  } catch (error) {
    console.error('Failed to load preferences from localStorage:', error)
  }

  // No stored preferences, use system defaults
  const systemPrefs = getSystemPreferences()
  return { ...DEFAULT_PREFERENCES, ...systemPrefs }
}

/**
 * Save preferences to localStorage
 */
function savePreferences(preferences: UserPreferences): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
  } catch (error) {
    console.error('Failed to save preferences to localStorage:', error)
  }
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<UserPreferences>(loadPreferences)

  // Save to localStorage whenever preferences change
  useEffect(() => {
    savePreferences(preferences)
  }, [preferences])

  const updatePreferences = (updates: Partial<UserPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...updates }))
  }

  return (
    <PreferencesContext.Provider value={{ preferences, updatePreferences }}>
      {children}
    </PreferencesContext.Provider>
  )
}

/**
 * Hook to access user preferences
 */
export function usePreferences() {
  const context = useContext(PreferencesContext)
  if (!context) {
    throw new Error('usePreferences must be used within PreferencesProvider')
  }
  return context
}

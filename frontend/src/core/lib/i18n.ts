import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import commonVi from '@/locales/vi/common.json'
import authVi from '@/locales/vi/auth.json'

/**
 * i18n configuration for internationalization
 * Currently supports Vietnamese (vi) as the default language
 *
 * To add a new language:
 * 1. Create translation files in src/locales/[lang]/
 * 2. Import the translations
 * 3. Add to resources object below
 * 4. Update supportedLngs array
 */

// Define resources type for type safety
export const resources = {
  vi: {
    common: commonVi,
    auth: authVi,
  },
} as const

// Initialize i18next
i18n
  .use(initReactI18next) // passes i18n down to react-i18next
  .init({
    resources,
    lng: 'vi', // default language
    fallbackLng: 'vi', // fallback language if translation is missing
    defaultNS: 'common', // default namespace
    ns: ['common', 'auth'], // available namespaces

    interpolation: {
      escapeValue: false, // React already escapes values
    },

    // React i18next options
    react: {
      useSuspense: false, // Set to true if you want to use Suspense
    },

    // Debug mode (only in development)
    debug: process.env.NODE_ENV === 'development',
  })

export default i18n

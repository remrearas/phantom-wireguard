import translationsData from './translations.json';

export type Locale = 'tr' | 'en';

export const DEFAULT_LOCALE: Locale = translationsData._default as Locale;

export const translations = translationsData as {
  _default: Locale;
  tr: typeof translationsData.tr;
  en: typeof translationsData.en;
};

export const translate = (locale: Locale) => {
  return translations[locale] || translations[DEFAULT_LOCALE];
};

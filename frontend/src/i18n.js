// Lightweight client-side localization system
(function () {
  let translations = {};
  let currentLang = 'en';

  // Load translation file from server
  async function loadTranslations(lang) {
    try {
      const response = await fetch(`/assets/lang/en.json`);
      if (!response.ok) throw new Error(`Could not load en.json`);
      translations = await response.json();
      currentLang = 'en';
    } catch (error) {
      console.error('Localization loading error:', error);
      translations = {};
    }
  }

  // Translate all DOM elements with data-i18n
  function translatePage() {
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (translations[key]) {
        // If it's an input or textarea with placeholder
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
          if (el.hasAttribute('placeholder')) {
            el.setAttribute('placeholder', translations[key]);
          } else {
            el.value = translations[key];
          }
        } else {
          el.innerHTML = translations[key];
        }
      }
    });

    // Handle attributes like placeholders separately if needed
    const placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
    placeholderElements.forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (translations[key]) {
        el.setAttribute('placeholder', translations[key]);
      }
    });
  }

  // Translate single key manually
  function t(key, defaultValue = '') {
    return translations[key] || defaultValue || key;
  }

  // Setup Lang dropdown if present (no-op as Hindi is removed)
  function initLangDropdown() {}

  // Change active language (no-op)
  async function changeLanguage(lang) {}

  // Initialize on page load
  async function init() {
    await loadTranslations('en');
    translatePage();
  }

  // Export globally
  window.i18n = {
    init,
    changeLanguage,
    t,
    translatePage,
    getCurrentLanguage: () => 'en'
  };

  // Run automatically when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

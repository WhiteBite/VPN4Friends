/**
 * Telegram WebApp SDK integration.
 *
 * The SDK is loaded dynamically ONLY when we detect we're inside
 * Telegram's WebView (via tgWebAppData in URL hash/search).
 * Outside Telegram, we skip loading entirely so the app works
 * without VPN in countries where telegram.org is blocked.
 */

let _sdkLoaded = false;
let _sdkPromise = null;

/**
 * Detect if we're inside a Telegram WebView by checking for
 * Telegram-specific URL parameters or the global object.
 */
function isInsideTelegram() {
  if (typeof window === 'undefined') return false;

  // Already loaded
  if (window.Telegram && window.Telegram.WebApp) return true;

  // Telegram injects tgWebAppData into the URL hash
  const hash = window.location.hash || '';
  const search = window.location.search || '';
  return hash.includes('tgWebAppData') || search.includes('tgWebAppData');
}

/**
 * Load the Telegram WebApp SDK dynamically.
 * Returns a promise that resolves when loaded (or rejects after timeout).
 */
export function loadTelegramSdk(timeoutMs = 4000) {
  if (_sdkPromise) return _sdkPromise;

  if (!isInsideTelegram()) {
    _sdkPromise = Promise.resolve(false);
    return _sdkPromise;
  }

  _sdkPromise = new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-web-app.js';
    script.async = true;

    const timer = setTimeout(() => {
      console.warn('[TG SDK] Load timeout, proceeding without SDK');
      resolve(false);
    }, timeoutMs);

    script.onload = () => {
      clearTimeout(timer);
      _sdkLoaded = true;
      resolve(true);
    };

    script.onerror = () => {
      clearTimeout(timer);
      console.warn('[TG SDK] Failed to load (blocked?), proceeding without SDK');
      resolve(false);
    };

    document.head.appendChild(script);
  });

  return _sdkPromise;
}

export function getTelegram() {
  if (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp) {
    return window.Telegram.WebApp;
  }
  return null;
}

export function getInitData() {
  const tg = getTelegram();
  if (tg && tg.initData) {
    return tg.initData;
  }

  // Fallback: extract initData from URL hash directly
  // This works even when telegram.org SDK is blocked (Russia/RKN)
  // Telegram always puts tgWebAppData in the URL hash fragment
  if (typeof window !== 'undefined') {
    // Try URL hash first (Telegram's standard method)
    const hash = window.location.hash;
    if (hash) {
      try {
        const hashParams = new URLSearchParams(hash.substring(1));
        const data = hashParams.get('tgWebAppData');
        if (data) return data;
      } catch { /* ignore */ }
    }

    // Try search params
    const params = new URLSearchParams(window.location.search);
    return params.get('tgWebAppData') || params.get('initData') || '';
  }

  return '';
}

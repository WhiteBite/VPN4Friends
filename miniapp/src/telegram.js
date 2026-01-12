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

  // Fallback for local development: try to read from URL
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    return params.get('tgWebAppData') || params.get('initData') || '';
  }

  return '';
}

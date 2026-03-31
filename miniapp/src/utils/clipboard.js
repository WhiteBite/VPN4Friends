import { getTelegram } from '../telegram';

/**
 * Robust copy to clipboard strategy for Telegram WebApp environment:
 * 1. Attempt synchronous fallback `execCommand` first (consumes user gesture reliably).
 * 2. If it fails, attempt modern `navigator.clipboard.writeText` async API.
 * 3. Also tries native Telegram `writeTextToClipboard`.
 *
 * @param {string} text - The text to copy
 * @param {Function} onSuccess - Callback on success
 * @param {Function} onError - Callback on failure
 */
export const copyToClipboard = (text, onSuccess, onError) => {
  if (!text) {
    if (onError) onError(new Error("Empty text"));
    return;
  }

  // 1. Try Telegram native API if available
  try {
    const tg = getTelegram();
    if (tg && tg.isVersionAtLeast && tg.isVersionAtLeast('6.4')) {
      tg.writeTextToClipboard(text, () => {
        if (onSuccess) onSuccess();
      });
      return;
    }
  } catch (err) {
    console.warn("Telegram clipboard API failed", err);
  }

  // 2. Fallback using execCommand (synchronous, reliable user gesture consumption)
  const executeFallback = (str) => {
    const textArea = document.createElement("textarea");
    textArea.value = str;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      const successful = document.execCommand('copy');
      textArea.remove();
      return successful;
    } catch (err) {
      textArea.remove();
      return false;
    }
  };

  const fallbackSucceeded = executeFallback(text);
  if (fallbackSucceeded) {
    if (onSuccess) onSuccess();
    return;
  }

  // 3. Modern Async Clipboard API as last resort
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text)
      .then(() => {
        if (onSuccess) onSuccess();
      })
      .catch((err) => {
        console.warn("navigator.clipboard failed:", err);
        if (onError) onError(err);
      });
  } else {
    if (onError) onError(new Error("No clipboard methods succeeded"));
  }
};

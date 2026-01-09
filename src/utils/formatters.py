"""Utility functions for formatting data."""


def format_traffic(bytes_count: int) -> str:
    """Format bytes to human-readable string."""
    if bytes_count < 1024:
        return f"{bytes_count} B"

    kb = bytes_count / 1024
    if kb < 1024:
        return f"{kb:.2f} KB"

    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.2f} MB"

    gb = mb / 1024
    return f"{gb:.2f} GB"


def get_dns_instructions() -> str:
    """Get DNS configuration instructions for VPN clients."""
    return (
        "\n\n⚙️ <b>Настройка DNS (важно!):</b>\n\n"
        "Если видишь ошибку <code>cloudfront.net certificate</code>:\n\n"
        "1️⃣ Открой настройки VPN в приложении\n"
        "2️⃣ Найди раздел DNS\n"
        "3️⃣ Измени на:\n"
        "   • <b>DNS-сервер:</b> local (локальный)\n"
        "   • Или укажи: <code>8.8.8.8</code>, <code>1.1.1.1</code>\n\n"
        "❌ <b>Не используй:</b>\n"
        "   • Remote DNS через прокси\n"
        "   • DoH (DNS over HTTPS) серверы\n\n"
        "✅ После изменения DNS всё заработает!"
    )

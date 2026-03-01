from __future__ import annotations


class WhatsAppProvider:
    def send(self, to_phone: str, body: str) -> None:
        raise NotImplementedError


class ConsoleWhatsAppProvider(WhatsAppProvider):
    def send(self, to_phone: str, body: str) -> None:
        print("=" * 80)
        print(f"WHATSAPP TO: {to_phone}")
        print(body)
        print("=" * 80)


class UnconfiguredWhatsAppProvider(WhatsAppProvider):
    def send(self, to_phone: str, body: str) -> None:
        raise ValueError("WhatsApp real sending is not configured yet. Use dry-run for WhatsApp campaigns.")

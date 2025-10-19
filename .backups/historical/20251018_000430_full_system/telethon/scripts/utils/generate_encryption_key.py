#!/usr/bin/env python3
"""
Скрипт для генерации ключа шифрования
"""

from cryptography.fernet import Fernet

def main():
    """Генерирует новый ключ шифрования"""
    print("🔐 Генерация ключа шифрования...")
    
    # Генерируем ключ
    key = Fernet.generate_key()
    key_str = key.decode()
    
    print("✅ Ключ сгенерирован!")
    print(f"📋 Добавьте в .env файл:")
    print(f"ENCRYPTION_KEY={key_str}")
    print()
    print("⚠️ ВАЖНО:")
    print("- Сохраните этот ключ в безопасном месте")
    print("- Без этого ключа вы не сможете расшифровать данные")
    print("- Не передавайте ключ третьим лицам")

if __name__ == "__main__":
    main()

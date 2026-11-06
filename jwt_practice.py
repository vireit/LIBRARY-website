import base64
import json
import hmac
import hashlib
import time

SECRET_KEY = "super-safe-key"

def base64url_encode(data: bytes) -> str:
    """Кодирует байты в Base64URL без padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(data: str) -> bytes:
    """Декодирует Base64URL с восстановлением padding."""
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_token(payload: dict, secret: str, header: dict = None) -> str:
    """Создаёт JWT вручную (для генерации тестовых токенов)."""
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    encoded_header = base64url_encode(header_json)
    encoded_payload = base64url_encode(payload_json)
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(secret.encode('utf-8'), signing_input.encode('utf-8'), hashlib.sha256).digest()
    encoded_signature = base64url_encode(signature)
    return f"{signing_input}.{encoded_signature}"

def validate_token(token: str, secret: str) -> dict:
    """
    Валидирует JWT согласно заданию:
    1. Разбивает на 3 части.
    2. Декодирует header и payload.
    3. Проверяет подпись HMAC-SHA256.
    4. Проверяет срок действия exp.
    Возвращает payload при успехе, иначе выбрасывает PermissionError с кодом 401.
    """
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    encoded_header, encoded_payload, encoded_signature = parts

    try:
        header = json.loads(base64url_decode(encoded_header))
        payload = json.loads(base64url_decode(encoded_payload))
    except Exception:
        raise ValueError("Invalid token encoding")

    # Проверка подписи
    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        signing_input.encode('utf-8'),
        hashlib.sha256
    ).digest()
    actual_signature = base64url_decode(encoded_signature)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise PermissionError("401: Invalid Signature")

    # Проверка срока действия
    if 'exp' in payload and payload['exp'] < time.time():
        raise PermissionError("401: Token Expired")

    return payload

def refresh_tokens(refresh_token: str, secret: str, user_in_db: dict) -> dict:
    """
    Симуляция обновления токенов с контролем версий.
    Проверяет валидность refresh-токена и сравнивает version из payload
    с password_version в «БД». При несовпадении — ошибка 401.
    """
    try:
        payload = validate_token(refresh_token, secret)
    except PermissionError as e:
        raise e
    except Exception as e:
        raise PermissionError(f"401: {str(e)}")

    token_version = payload.get('version')
    db_version = user_in_db.get('password_version')
    if token_version != db_version:
        raise PermissionError("401: Token Version Mismatch. Please re-authenticate.")

    # Успешное обновление: выдаём новую пару токенов (симуляция)
    new_access = create_token(
        {"sub": payload['sub'], "exp": time.time() + 900},  # 15 минут
        secret
    )
    new_refresh = create_token(
        {"sub": payload['sub'], "version": db_version, "exp": time.time() + 86400},  # 1 день
        secret
    )
    return {"access_token": new_access, "refresh_token": new_refresh}

def main():
    print("=== Тест-кейс 1: Валидация успешна ===")
    valid_payload = {
        "sub": "1234567890",
        "name": "John Doe",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    token = create_token(valid_payload, SECRET_KEY)
    print(f"Токен: {token[:50]}...")
    try:
        result = validate_token(token, SECRET_KEY)
        print(f"✅ Валидация успешна. Payload: {result}")
    except PermissionError as e:
        print(f"❌ Ошибка: {e}")

    print("\n=== Тест-кейс 2: Валидация провалена (просроченный токен) ===")
    expired_payload = {
        "sub": "1234567890",
        "name": "John Doe",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600
    }
    expired_token = create_token(expired_payload, SECRET_KEY)
    try:
        validate_token(expired_token, SECRET_KEY)
        print("❌ Ошибка: токен не должен был пройти валидацию")
    except PermissionError as e:
        print(f"✅ Ожидаемая ошибка: {e}")

    print("\n=== Тест-кейс 2b: Валидация провалена (изменённая подпись) ===")
    tampered_token = token[:-5] + "abcde"
    try:
        validate_token(tampered_token, SECRET_KEY)
        print("❌ Ошибка: токен не должен был пройти валидацию")
    except PermissionError as e:
        print(f"✅ Ожидаемая ошибка: {e}")

    print("\n=== Тест-кейс 3: Обновление токена отклонено (версия устарела) ===")
    user_in_db = {
        "id": "1234567890",
        "username": "john_doe",
        "password_version": 2
    }
    refresh_payload_old = {
        "sub": "1234567890",
        "version": 1,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400
    }
    refresh_token_old = create_token(refresh_payload_old, SECRET_KEY)
    try:
        refresh_tokens(refresh_token_old, SECRET_KEY, user_in_db)
        print("❌ Ошибка: обновление не должно было произойти")
    except PermissionError as e:
        print(f"✅ Ожидаемая ошибка: {e}")

    print("\n=== Дополнительно: успешное обновление с актуальной версией ===")
    refresh_payload_actual = {
        "sub": "1234567890",
        "version": 2,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400
    }
    refresh_token_actual = create_token(refresh_payload_actual, SECRET_KEY)
    try:
        new_tokens = refresh_tokens(refresh_token_actual, SECRET_KEY, user_in_db)
        print(f"✅ Обновление успешно. Новый access токен: {new_tokens['access_token'][:50]}...")
    except PermissionError as e:
        print(f"❌ Неожиданная ошибка: {e}")

if __name__ == "__main__":
    main()
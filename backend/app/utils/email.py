import os
import random
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

async def send_email(to_email: str, subject: str, body: str):
    """
    Отправка email через SendGrid API
    """
    try:
        message = Mail(
            from_email=(os.getenv('EMAIL_FROM'), os.getenv('EMAIL_FROM_NAME', 'SecureShare')),
            to_emails=to_email,
            subject=subject,
            html_content=body
        )
        
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        
        # Проверяем успешность отправки (код 202 Accepted)
        if response.status_code == 202:
            return True
        else:
            print(f"SendGrid API error: {response.status_code}, {response.body}")
            return False
            
    except Exception as e:
        print(f"Ошибка отправки email через SendGrid: {e}")
        return False

def generate_verification_code(length=6):
    """
    Генерация кода подтверждения
    """
    return ''.join(random.choices('0123456789', k=length))

# Временное хранилище для кодов 2FA
verification_codes = {}

def store_verification_code(user_id: int, code: str):
    """
    Сохранение кода подтверждения
    """
    expires_at = datetime.now() + timedelta(minutes=10)
    verification_codes[user_id] = {
        'code': code,
        'expires_at': expires_at,
        'attempts': 0
    }

def verify_code(user_id: int, code: str):
    """
    Проверка кода подтверждения
    """
    if user_id not in verification_codes:
        return False
        
    record = verification_codes[user_id]
    
    # Проверка срока действия
    if datetime.now() > record['expires_at']:
        del verification_codes[user_id]
        return False
        
    # Проверка кода
    if record['code'] == code:
        del verification_codes[user_id]
        return True
        
    # Увеличиваем счетчик попыток
    record['attempts'] += 1
    if record['attempts'] >= 3:
        del verification_codes[user_id]
        
    return False
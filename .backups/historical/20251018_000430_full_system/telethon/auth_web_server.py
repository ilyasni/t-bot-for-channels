"""
Веб-сервер для безопасной аутентификации
Предоставляет HTTPS интерфейс для ввода кодов аутентификации
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
import os
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import User
from secure_auth_manager import secure_auth_manager

# Модели данных
class AuthData(BaseModel):
    api_id: str
    api_hash: str
    phone: str
    session_id: str

class VerifyData(BaseModel):
    session_id: str
    code: str

class TwoFactorData(BaseModel):
    session_id: str
    password: str

logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="Telegram Auth Server",
    description="Безопасный веб-интерфейс для аутентификации Telegram",
    version="1.0.0"
)

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# Безопасность
security = HTTPBearer(auto_error=False)

def get_auth_url() -> str:
    """Получает URL для аутентификации из переменных окружения"""
    base_url = os.getenv("AUTH_BASE_URL", "https://localhost:8000")
    return f"{base_url}/auth"

@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Telegram Authentication</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                max-width: 500px;
                width: 100%;
                text-align: center;
            }
            .logo {
                font-size: 48px;
                margin-bottom: 20px;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                line-height: 1.6;
            }
            .warning {
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 10px;
                padding: 15px;
                margin: 20px 0;
                color: #856404;
            }
            .info {
                background: #d1ecf1;
                border: 1px solid #bee5eb;
                border-radius: 10px;
                padding: 15px;
                margin: 20px 0;
                color: #0c5460;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🔐</div>
            <h1>Telegram Authentication</h1>
            <p class="subtitle">
                Безопасный веб-интерфейс для аутентификации в Telegram боте
            </p>
            
            <div class="warning">
                <strong>⚠️ Важно:</strong><br>
                Никогда не вводите коды аутентификации в Telegram чат!<br>
                Используйте только этот защищенный интерфейс.
            </div>
            
            <div class="info">
                <strong>💡 Как использовать:</strong><br>
                1. В боте выполните команду /auth<br>
                2. Получите уникальную ссылку<br>
                3. Откройте ссылку в браузере<br>
                4. Введите ваши данные аутентификации<br>
                5. Получите код в Telegram и введите его здесь
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/auth", response_class=HTMLResponse)
async def auth_page(request: Request, sid: str = None):
    """Страница аутентификации"""
    if not sid:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>Ошибка</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #e74c3c; background: #fdf2f2; padding: 20px; border-radius: 10px; }
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Ошибка</h2>
                <p>Не указан ID сессии. Получите ссылку из Telegram бота.</p>
            </div>
        </body>
        </html>
        """)
    
    # Валидируем сессию
    session = await secure_auth_manager.validate_auth_session(sid)
    if not session:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>Сессия истекла</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #e74c3c; background: #fdf2f2; padding: 20px; border-radius: 10px; }
            </style>
        </head>
        <body>
            <div class="error">
                <h2>⏰ Сессия истекла</h2>
                <p>Время сессии аутентификации истекло. Получите новую ссылку из бота.</p>
            </div>
        </body>
        </html>
        """)
    
    # Отображаем форму аутентификации
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Telegram Authentication</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                max-width: 500px;
                width: 100%;
            }}
            .logo {{
                font-size: 48px;
                text-align: center;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }}
            .form-group {{
                margin-bottom: 20px;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #333;
            }}
            input[type="text"], input[type="password"] {{
                width: 100%;
                padding: 12px;
                border: 2px solid #e1e5e9;
                border-radius: 10px;
                font-size: 16px;
                box-sizing: border-box;
                transition: border-color 0.3s;
            }}
            input[type="text"]:focus, input[type="password"]:focus {{
                outline: none;
                border-color: #667eea;
            }}
            button {{
                width: 100%;
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }}
            button:hover {{
                transform: translateY(-2px);
            }}
            button:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }}
            .message {{
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }}
            .success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            .info {{
                background: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }}
            .hidden {{
                display: none;
            }}
            .step {{
                display: none;
            }}
            .step.active {{
                display: block;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🔐</div>
            <h1>Telegram Authentication</h1>
            
            <div id="message"></div>
            
            <div id="step1" class="step active">
                <form id="authForm">
                    <input type="hidden" id="sessionId" value="{sid}">
                    
                    <div class="form-group">
                        <label for="apiId">API ID:</label>
                        <input type="text" id="apiId" name="api_id" required 
                               placeholder="Введите ваш API ID">
                    </div>
                    
                    <div class="form-group">
                        <label for="apiHash">API Hash:</label>
                        <input type="password" id="apiHash" name="api_hash" required 
                               placeholder="Введите ваш API Hash">
                    </div>
                    
                    <div class="form-group">
                        <label for="phone">Номер телефона:</label>
                        <input type="text" id="phone" name="phone" required 
                               placeholder="+1234567890" pattern="^\\+[1-9]\\d{{1,14}}$">
                    </div>
                    
                    <button type="submit">Начать аутентификацию</button>
                </form>
            </div>
            
            <div id="step2" class="step">
                <form id="codeForm">
                    <div class="form-group">
                        <label for="code">Код аутентификации:</label>
                        <input type="text" id="code" name="code" required 
                               placeholder="Введите код из Telegram" maxlength="5">
                    </div>
                    
                    <button type="submit">Проверить код</button>
                    <button type="button" onclick="goBack()" style="background: #6c757d; margin-top: 10px;">
                        Назад
                    </button>
                </form>
            </div>
            
            <div id="step2fa" class="step">
                <form id="twoFactorForm">
                    <div class="form-group">
                        <label for="password">Пароль двухфакторной аутентификации:</label>
                        <input type="password" id="password" name="password" required 
                               placeholder="Введите пароль 2FA">
                    </div>
                    
                    <button type="submit">Проверить пароль</button>
                    <button type="button" onclick="goBack()" style="background: #6c757d; margin-top: 10px;">
                        Назад
                    </button>
                </form>
            </div>
            
            <div id="step3" class="step">
                <div class="message success">
                    <h3>✅ Аутентификация успешна!</h3>
                    <p>Теперь вы можете использовать все функции бота.</p>
                    <p>Закройте это окно и вернитесь в Telegram.</p>
                </div>
            </div>
        </div>
        
        <script>
            let currentSessionId = '{sid}';
            
            document.getElementById('authForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const formData = new FormData(this);
                const data = Object.fromEntries(formData.entries());
                data.session_id = currentSessionId;
                
                showMessage('Отправка данных...', 'info');
                
                try {{
                    const response = await fetch('/api/auth/process', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify(data)
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        if (result.requires_code) {{
                            showStep(2);
                            showMessage('Код отправлен на ваш номер телефона', 'success');
                        }} else {{
                            showStep(3);
                        }}
                    }} else {{
                        showMessage(result.error || 'Ошибка аутентификации', 'error');
                    }}
                }} catch (error) {{
                    showMessage('Ошибка соединения: ' + error.message, 'error');
                }}
            }});
            
            document.getElementById('codeForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const code = document.getElementById('code').value;
                
                showMessage('Проверка кода...', 'info');
                
                try {{
                    const response = await fetch('/api/auth/verify', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            session_id: currentSessionId,
                            code: code
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        if (result.requires_2fa) {{
                            showStep('2fa');
                            showMessage('Введите пароль двухфакторной аутентификации', 'info');
                        }} else {{
                            showStep(3);
                        }}
                    }} else {{
                        showMessage(result.error || 'Неверный код', 'error');
                    }}
                }} catch (error) {{
                    showMessage('Ошибка соединения: ' + error.message, 'error');
                }}
            }});
            
            document.getElementById('twoFactorForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const password = document.getElementById('password').value;
                
                showMessage('Проверка пароля 2FA...', 'info');
                
                try {{
                    const response = await fetch('/api/auth/2fa', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            session_id: currentSessionId,
                            password: password
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        showStep(3);
                    }} else {{
                        showMessage(result.error || 'Неверный пароль 2FA', 'error');
                    }}
                }} catch (error) {{
                    showMessage('Ошибка соединения: ' + error.message, 'error');
                }}
            }});
            
            function showStep(stepNumber) {{
                document.querySelectorAll('.step').forEach(step => {{
                    step.classList.remove('active');
                }});
                document.getElementById(`step${{stepNumber}}`).classList.add('active');
            }}
            
            function showMessage(text, type) {{
                const messageDiv = document.getElementById('message');
                messageDiv.className = `message ${{type}}`;
                messageDiv.textContent = text;
                messageDiv.style.display = 'block';
                
                if (type === 'success' || type === 'error') {{
                    setTimeout(() => {{
                        messageDiv.style.display = 'none';
                    }}, 5000);
                }}
            }}
            
            function goBack() {{
                showStep(1);
                document.getElementById('message').style.display = 'none';
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.post("/api/auth/process")
async def process_auth_data(auth_data: AuthData):
    """Обработка данных аутентификации"""
    try:
        logger.info(f"🔐 Получены данные аутентификации для сессии {auth_data.session_id[:8]}...")
        
        result = await secure_auth_manager.process_auth_data(
            auth_data.session_id, auth_data.api_id, auth_data.api_hash, auth_data.phone
        )
        
        logger.info(f"✅ Результат аутентификации: {result}")
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки данных аутентификации: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': f'Внутренняя ошибка сервера: {str(e)}'
            }
        )

@app.post("/api/auth/verify")
async def verify_auth_code(verify_data: VerifyData):
    """Проверка кода аутентификации"""
    try:
        logger.info(f"🔐 Верификация кода для сессии {verify_data.session_id[:8]}...")
        
        result = await secure_auth_manager.verify_auth_code(verify_data.session_id, verify_data.code)
        
        logger.info(f"✅ Результат верификации: {result}")
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки кода аутентификации: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': f'Внутренняя ошибка сервера: {str(e)}'
            }
        )

@app.post("/api/auth/2fa")
async def verify_two_factor(two_factor_data: TwoFactorData):
    """Проверка пароля двухфакторной аутентификации"""
    try:
        logger.info(f"🔐 Проверка 2FA для сессии {two_factor_data.session_id[:8]}...")
        
        result = await secure_auth_manager.verify_two_factor(
            two_factor_data.session_id, 
            two_factor_data.password
        )
        
        logger.info(f"✅ Результат 2FA: {result}")
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки 2FA: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': f'Внутренняя ошибка сервера: {str(e)}'
            }
        )

@app.get("/health")
async def health_check():
    """Проверка состояния сервера"""
    return JSONResponse(content={
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'active_sessions': len(secure_auth_manager.auth_sessions),
        'active_clients': len(secure_auth_manager.active_clients)
    })

async def cleanup_task():
    """Задача очистки истекших сессий"""
    while True:
        try:
            await secure_auth_manager.cleanup_expired_sessions()
            await asyncio.sleep(60)  # Проверяем каждую минуту
        except Exception as e:
            logger.error(f"❌ Ошибка очистки сессий: {str(e)}")
            await asyncio.sleep(60)

def start_auth_server(host: str = "0.0.0.0", port: int = 8000, ssl_cert: str = None, ssl_key: str = None):
    """Запуск веб-сервера аутентификации"""
    
    # Запускаем задачу очистки в фоне
    asyncio.create_task(cleanup_task())
    
    logger.info(f"🚀 Запуск веб-сервера аутентификации на {host}:{port}")
    
    # Настройки SSL
    ssl_context = None
    if ssl_cert and ssl_key:
        import ssl
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(ssl_cert, ssl_key)
        logger.info("🔒 SSL включен")
    else:
        logger.warning("⚠️ SSL не настроен - используйте только для разработки!")
    
    # Запускаем сервер
    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_context=ssl_context,
        log_level="info"
    )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Telegram Auth Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--ssl-cert", help="SSL certificate file")
    parser.add_argument("--ssl-key", help="SSL private key file")
    
    args = parser.parse_args()
    
    start_auth_server(
        host=args.host,
        port=args.port,
        ssl_cert=args.ssl_cert,
        ssl_key=args.ssl_key
    )

import os
import datetime
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import openai
import logging

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis do arquivo .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    logger.error("Variáveis de ambiente TELEGRAM_TOKEN ou OPENAI_API_KEY não encontradas")
    exit(1)

openai.api_key = OPENAI_API_KEY

# Diretório para salvar conversas
conversations_dir = Path("conversations")
conversations_dir.mkdir(exist_ok=True)

def sanitize_filename(name):
    """Remove caracteres inválidos para nomes de arquivo"""
    return "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in name)

def save_conversation(user_id, username, message, is_bot=False):
    """Salva a conversa em arquivo com tratamento de erros robusto"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_username = sanitize_filename(username if username else f"user_{user_id}")
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        user_folder = conversations_dir / f"{user_id}_{safe_username}"
        user_folder.mkdir(parents=True, exist_ok=True)
        
        file_path = user_folder / f"conversa_{date_str}.txt"
        sender = "BOT" if is_bot else f"USUARIO ({safe_username})"
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {sender}: {message}\n")
            
        logger.info(f"Mensagem salva para user_id {user_id} em {file_path}")
    except Exception as e:
        logger.error(f"Erro ao salvar conversa: {e}", exc_info=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /start"""
    user = update.effective_user
    welcome_msg = (
        f"Olá {user.first_name}! Sou um assistente com IA integrada.\n\n"
        "🔹 Envie qualquer pergunta para conversar\n"
        "🔹 Use /img [descrição] para gerar imagens\n"
        "🔹 Suas conversas são armazenadas localmente"
    )
    await update.message.reply_text(welcome_msg)
    save_conversation(user.id, user.username or user.first_name, "/start")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens de texto normais"""
    user = update.effective_user
    text = update.message.text
    
    if not text.strip():
        await update.message.reply_text("Por favor, envie uma mensagem válida.")
        return
    
    save_conversation(user.id, user.username, text)
    
    try:
        response = await generate_openai_response(text)
        await update.message.reply_text(response)
        save_conversation(user.id, user.username, response, is_bot=True)
    except Exception as e:
        error_msg = "Ocorreu um erro ao processar sua mensagem. Tente novamente mais tarde."
        logger.error(f"Erro no handle_message: {e}", exc_info=True)
        await update.message.reply_text(error_msg)
        save_conversation(user.id, user.username, error_msg, is_bot=True)

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /img"""
    user = update.effective_user
    prompt = " ".join(context.args).strip()
    
    if not prompt:
        await update.message.reply_text("Por favor, forneça uma descrição após o comando /img")
        return
    
    save_conversation(user.id, user.username, f"/img {prompt}")
    
    try:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512",
            quality="standard"
        )
        image_url = response['data'][0]['url']
        await update.message.reply_photo(image_url)
        save_conversation(user.id, user.username, f"Imagem gerada: {prompt}", is_bot=True)
    except openai.error.InvalidRequestError as e:
        error_msg = "Desculpe, não pude gerar esta imagem. O conteúdo pode violar nossas diretrizes."
        await update.message.reply_text(error_msg)
        logger.warning(f"Conteúdo potencialmente inadequado: {prompt}")
    except Exception as e:
        error_msg = "Erro ao gerar imagem. Tente novamente mais tarde."
        await update.message.reply_text(error_msg)
        logger.error(f"Erro no generate_image: {e}", exc_info=True)

async def generate_openai_response(prompt):
    """Gera resposta usando a API da OpenAI"""
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente útil e educado."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erro na API OpenAI: {e}", exc_info=True)
        raise

def main():
    """Configura e inicia o bot"""
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("img", generate_image))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Bot iniciado e pronto para receber mensagens...")
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Falha ao iniciar o bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()

    from dotenv import load_dotenv
import os

load_dotenv()  # Carrega o arquivo .env

print("Token do Telegram:", os.getenv("TELEGRAM_TOKEN") or "NÃO ENCONTRADO")
print("Chave da OpenAI:", os.getenv("OPENAI_API_KEY") or "NÃO ENCONTRADO")
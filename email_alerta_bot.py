import imaplib
import email
from bs4 import BeautifulSoup
import telegram
import time
from urllib.parse import unquote, urlparse, parse_qs

# --- CONFIGURAÇÕES --- (ALTERE COM SEUS DADOS!)
EMAIL = "diogenesmeed@gmail.com"
SENHA = "vrog rgcg fplw uvoi"  # Senha de app do Gmail
PASTA = "INBOX"
PALAVRA_CHAVE = "alerta do google"
TELEGRAM_TOKEN = "8202984853:AAFiiQeyg344Fk9kM5Gml20SJ7AQcpSI20M"
CHAT_IDS = [7472778102, 7864120172]
CHECK_INTERVAL = 180  # 180 segundos = 3 minutos
MAX_LINKS = 50

# --- INICIALIZAÇÃO DO BOT ---
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# --- FUNÇÕES AUXILIARES ---
def limpar_google_url(url):
    """Remove redirecionamentos do Google (ex: 'https://www.google.com/url?q=...')"""
    if 'google.com/url?' in url:
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            if 'url' in query:
                return unquote(query['url'][0])
        except:
            return url
    return url

def extrair_links_html_acima_do_limite(html):
    """Extrai links do HTML do e-mail, ignorando a seção 'Ver mais resultados'"""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    
    parar_em = soup.find('a', string=lambda t: t and "ver mais resultados" in t.lower())
    limite = parar_em.find_parent() if parar_em else None

    for a in soup.find_all('a', href=True):
        if limite and a.find_parent() and limite in a.find_parents():
            break  # Ignora links após "Ver mais resultados"

        texto = a.get_text(strip=True)
        href = limpar_google_url(a['href'])  # Limpa redirecionamentos
        
        # Filtra links irrelevantes
        if texto.lower().startswith(("editar este alerta", "cancelar inscrição", "ver todos os seus alertas")):
            continue

        if href and texto and href not in [l[1] for l in links]:
            texto = (texto[:100] + '...') if len(texto) > 100 else texto
            links.append((texto, href))

    return links[:MAX_LINKS]

# --- FUNÇÃO PRINCIPAL ---
def processar_emails():
    try:
        # Conecta ao Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, SENHA)
        mail.select(PASTA)

        # Busca e-mails não lidos com o assunto específico
        status, mensagens = mail.search(None, f'(UNSEEN SUBJECT "{PALAVRA_CHAVE}")')
        if status != "OK" or not mensagens[0]:
            print(f"[{time.ctime()}] Nenhum e-mail novo encontrado.")
            mail.logout()
            return

        print(f"[{time.ctime()}] {len(mensagens[0].split())} novo(s) e-mail(s) encontrado(s).")

        for num in mensagens[0].split():
            status, dados = mail.fetch(num, '(RFC822)')
            if status != 'OK':
                continue

            # Extrai conteúdo do e-mail
            mensagem = email.message_from_bytes(dados[0][1])
            assunto = mensagem.get("Subject", "Sem assunto")
            corpo = ""

            if mensagem.is_multipart():
                for parte in mensagem.walk():
                    if parte.get_content_type() == 'text/html':
                        corpo = parte.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                corpo = mensagem.get_payload(decode=True).decode(errors='ignore')

            links = extrair_links_html_acima_do_limite(corpo)

            # Envia para o Telegram
            for chat_id in CHAT_IDS:
                try:
                    bot.send_message(
                        chat_id=chat_id,
                        text=f"📨 *Novo Alerta do Google!*\n\n🔹 **Assunto:** {assunto}",
                        parse_mode=telegram.ParseMode.MARKDOWN
                    )
                    time.sleep(1)
                    
                    for texto, href in links:
                        bot.send_message(
                            chat_id=chat_id,
                            text=href,
                            disable_web_page_preview=False
                        )
                        time.sleep(2)  # Evita flood no Telegram
                
                except Exception as e:
                    print(f"[ERRO] Telegram (chat_id {chat_id}): {e}")

            # Marca como lido
            mail.store(num, '+FLAGS', '\\Seen')

        mail.logout()

    except Exception as e:
        print(f"[ERRO CRÍTICO] {e}")

# --- LOOP PRINCIPAL ---
if __name__ == "__main__":
    print(f"✅ Bot iniciado em {time.ctime()}. Verificando a cada {CHECK_INTERVAL/60} minutos.")
    print("Pressione Ctrl+C para parar.")
    
    try:
        while True:
            processar_emails()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n⛔ Bot interrompido pelo usuário.")
from flask import Flask, render_template, request, Response, session, redirect, url_for
import openai
from dotenv import load_dotenv
import os
from time import sleep
from database import criar_conexao
from assistente_ecomart import criar_assistente
from uuid import uuid4

# Carregar a chave da API do OpenAI
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
modelo = "gpt-4"

app = Flask(__name__)
app.secret_key = 'alura'

# Obter as instruções para o assistente
assistente_instrucoes = criar_assistente()

# Credenciais fictícias de usuários (simulação de base de dados)
credenciais_usuarios = {
    "admin": {"senha": "admin2024", "empresa": "Nestle"},
    "user1": {"senha": "user123", "empresa": "Pepsico"},
}

# Dicionário para armazenar o histórico de conversas
historico_conversas = {}

# Função principal para gerar queries SQL a partir de um prompt
def bot(session_id):
    try:
        # Utiliza o histórico da conversa para gerar a resposta
        response = openai.ChatCompletion.create(
            model=modelo,
            messages=historico_conversas[session_id],
            temperature=0.0  # Temperatura baixa para respostas determinísticas
        )
        resposta = response['choices'][0]['message']['content'].strip()

        # Adicionar a resposta do assistente ao histórico da conversa
        historico_conversas[session_id].append({"role": "assistant", "content": resposta})

        return resposta
    except Exception as erro:
        print(f"Erro no GPT: {erro}")  # Para depuração
        return f"Erro no GPT: {erro}"

# Função para executar a query no banco de dados
# Função para executar a query no banco de dados
# Função para executar a query no banco de dados
def executar_query(query):
    conexao = criar_conexao()
    if conexao:
        try:
            print("Conectado ao banco de dados!")  # Confirmar a conexão
            cursor = conexao.cursor()
            cursor.execute(query)
            resultado = cursor.fetchall()
            colunas = [desc[0] for desc in cursor.description]
            
            # Adicionando logs para verificação
            print(f"Consulta Executada: {query}")  # Verificar a consulta executada
            print(f"Resultado da Consulta: {resultado}")  # Verificar o resultado da consulta

            return resultado, colunas
        except Exception as e:
            print(f"Erro ao executar a query: {e}")
            return None, None
        finally:
            cursor.close()
            conexao.close()
    return None, None



# Função para gerar uma resposta amigável ao usuário
def gerar_resposta(dados_query, colunas):
    if not dados_query:
        return "Nenhum dado encontrado."

    # Montar a lista de dados que será passada ao modelo GPT
    partes_resposta = []
    dado = dados_query[0]

    # Montar o contexto dos dados, coluna por coluna
    for col_name, value in zip(colunas, dado):
        partes_resposta.append(f"{col_name}: {value}")

    # Criação do prompt dinâmico para ser passado ao GPT-4
    prompt = f"""
    Você é um assistente inteligente especializado em fornecer respostas claras e amigáveis sobre dados empresariais. 
    Abaixo, você encontrará os dados obtidos de uma consulta SQL.

    Dados da consulta:
    {', '.join(partes_resposta)}

    Por favor, crie uma resposta clara e curta para um usuário, explicando os resultados obtidos de forma concisa e acessível.

    Certifique-se de:
    - Transformar valores em uma linguagem natural.
    - Converter eficientemente em porcentagem ou unidades, quando aplicável.
    - Evitar suposições, comparações ou diferenciações que não foram solicitadas.
    """

    # Chamar a OpenAI para gerar a resposta final
    try:
        response = openai.ChatCompletion.create(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2  # Ajuste a temperatura para controlar a criatividade da resposta
        )
        resposta_gerada = response['choices'][0]['message']['content'].strip()
        return resposta_gerada
    except Exception as erro:
        print(f"Erro ao gerar resposta com GPT: {erro}")
        return "Houve um erro ao tentar gerar a resposta. Por favor, tente novamente mais tarde."


# Endpoint para lidar com login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_usuario = request.form["login"]
        senha_usuario = request.form["senha"]

        # Verificar se as credenciais são válidas
        if login_usuario in credenciais_usuarios and credenciais_usuarios[login_usuario]["senha"] == senha_usuario:
            # Salvar informações de login na sessão
            session['session_id'] = str(uuid4())
            session['usuario'] = login_usuario
            session['empresa'] = credenciais_usuarios[login_usuario]["empresa"]
            return redirect(url_for("home"))
        else:
            return render_template("login.html", erro="Login ou senha inválidos. Por favor, tente novamente.")
    return render_template("login.html")

# Endpoint do chat para lidar com requisições POST
@app.route("/chat", methods=["POST"])
def chat():
    # Verificar se o usuário está logado
    if 'usuario' not in session:
        return Response("Você precisa fazer login antes de usar o chatbot.", content_type="text/plain; charset=utf-8")

    session_id = session['session_id']
    empresa_usuario = session['empresa']

    # Se o histórico de conversas para essa sessão não existir, inicialize-o
    if session_id not in historico_conversas:
        historico_conversas[session_id] = [
            {"role": "system", "content": assistente_instrucoes}
        ]

    prompt_usuario = request.json["msg"]

    # Adicionar a mensagem do usuário ao histórico da conversa
    historico_conversas[session_id].append({"role": "user", "content": prompt_usuario})

    # Gerar a resposta do chatbot
    resposta_bot = bot(session_id)

    print("Resposta do Chatbot (Query SQL gerada):", resposta_bot)  # Para depuração

    # Verifica se a resposta contém uma query SQL válida
    if resposta_bot.startswith("SELECT"):
        # Remover o ponto e vírgula ao final da consulta, se houver
        resposta_bot = resposta_bot.rstrip(';')

        # Restringir a consulta para a empresa do usuário
        if "WHERE" in resposta_bot.upper():
            resposta_bot += f" AND empresa = '{empresa_usuario}'"
        else:
            resposta_bot += f" WHERE empresa = '{empresa_usuario}'"

        print("Query gerada com restrição de empresa:", resposta_bot)  # Para depuração
        resultado_query, colunas = executar_query(resposta_bot)

        if resultado_query == "Erro ao executar a query" or resultado_query == "Erro: Conexão com o banco de dados falhou.":
            return Response(resultado_query, content_type="text/plain; charset=utf-8")

        print("Resultado da consulta:", resultado_query)  # Para depuração

        if resultado_query and colunas:
            # Gerar a resposta final para o usuário
            resposta_texto = gerar_resposta(resultado_query, colunas)
            print("Resultado da consulta formatado:", resposta_texto)  # Para depuração
            return Response(resposta_texto, content_type="text/plain; charset=utf-8")

        return Response("Nenhum resultado encontrado para a consulta.", content_type="text/plain; charset=utf-8")
    else:
        # Se a resposta não contém uma query SQL válida, pedir informações adicionais ao usuário
        # Analisamos a resposta do GPT para ver se há uma mensagem indicando falta de informações
        if "informação insuficiente" in resposta_bot.lower() or "especificar" in resposta_bot.lower():
            # Personalizamos o pedido de informações ao usuário
            informacoes_faltantes_prompt = """
            Parece que não consegui gerar uma consulta SQL válida devido à falta de algumas informações importantes.
            Por favor, forneça mais detalhes sobre o que você gostaria de saber.

            - Qual empresa você está falando?
            - Especifique um período ou data (se aplicável).
            - Que tipo de métrica você está procurando (por exemplo, eficiência técnica, produção, etc.)?
            """

            try:
                response = openai.ChatCompletion.create(
                    model=modelo,
                    messages=historico_conversas[session_id] + [{"role": "assistant", "content": informacoes_faltantes_prompt}],
                    temperature=0.5,
                )
                resposta_pedido_informacoes = response['choices'][0]['message']['content'].strip()
                # Adicionar a resposta ao histórico
                historico_conversas[session_id].append({"role": "assistant", "content": resposta_pedido_informacoes})
                return Response(resposta_pedido_informacoes, content_type="text/plain; charset=utf-8")
            except Exception as erro:
                print(f"Erro ao gerar resposta com GPT: {erro}")
                return Response("Houve um erro ao tentar gerar uma resposta. Por favor, tente novamente mais tarde.", content_type="text/plain; charset=utf-8")

        # Caso contrário, fornecer uma resposta padrão
        return Response("Desculpe, não consegui gerar uma consulta válida para sua pergunta. Por favor, tente reformular sua pergunta.", content_type="text/plain; charset=utf-8")


# Endpoint inicial para renderizar a página do chat
@app.route("/")
def home():
    if 'usuario' not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

# Inicializa o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)

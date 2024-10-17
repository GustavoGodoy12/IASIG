from flask import Flask, render_template, request, Response
import openai
from dotenv import load_dotenv
import os
from time import sleep
from database import criar_conexao
from assistente_ecomart import criar_assistente
from flask import session
from uuid import uuid4

# Carregar a chave da API do OpenAI
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
modelo = "gpt-4"

app = Flask(__name__)
app.secret_key = 'alura'

# Obter as instruções para o assistente
assistente_instrucoes = criar_assistente()

historico_conversas = {}


# Função principal para gerar queries SQL a partir de um prompt
def bot(prompt):
    try:
        # Utiliza o assistente existente para gerar a query SQL
        response = openai.ChatCompletion.create(
            model=modelo,
            messages=[
                {"role": "system", "content": assistente_instrucoes},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0  # Temperatura baixa para respostas determinísticas
        )
        resposta = response['choices'][0]['message']['content'].strip()
        return resposta
    except Exception as erro:
        print(f"Erro no GPT: {erro}")  # Para depuração
        return f"Erro no GPT: {erro}"

# Função para executar a query no banco de dados
def executar_query(query):
    conexao = criar_conexao()
    if conexao:
        try:
            cursor = conexao.cursor()
            cursor.execute(query)
            resultado = cursor.fetchall()
            colunas = [desc[0] for desc in cursor.description]
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
    - Diferenciar entre produção e eficiência.
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



# Endpoint do chat para lidar com requisições POST
@app.route("/chat", methods=["POST"])
def chat():
    prompt_usuario = request.json["msg"]
    resposta_bot = bot(prompt_usuario)

    print("Resposta do Chatbot (Query SQL gerada):", resposta_bot)  # Para depuração

    # Verifica se a resposta contém uma query SQL válida
    if resposta_bot.startswith("SELECT"):
        print("Query gerada:", resposta_bot)  # Para depuração
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
        # Se a resposta não contém uma query SQL válida
        return Response("Desculpe, não consegui gerar uma consulta válida para sua pergunta. Por favor, tente reformular sua pergunta.", content_type="text/plain; charset=utf-8")


# Endpoint inicial para renderizar a página do chat
@app.route("/")
def home():
    return render_template("index.html")

# Inicializa o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)

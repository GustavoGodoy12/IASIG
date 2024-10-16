from flask import Flask, render_template, request, Response, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import os
from time import sleep
from helpers import *
from selecionar_persona import *
from assistente_ecomart import *
from database import criar_conexao
load_dotenv()

cliente = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
modelo = "gpt-4"

app = Flask(__name__)
app.secret_key = 'alura'

assistente = criar_assistente()
thread = criar_thread()

def bot(prompt):
    maximo_tentativas = 1
    repeticao = 0

    while True:
        try:
            cliente.beta.threads.messages.create(
                thread_id=thread.id, 
                role = "user",
                content =  prompt
            )

            run = cliente.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistente.id
            )

            while run.status !="completed":
                run = cliente.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
            )
            
            historico = list(cliente.beta.threads.messages.list(thread_id=thread.id).data)
            resposta = historico[0]
            return resposta

        except Exception as erro:
                repeticao += 1
                if repeticao >= maximo_tentativas:
                        return "Erro no GPT: %s" % erro
                print('Erro de comunicação com OpenAI:', erro)
                sleep(1)
            


def executar_query(query):
    conexao = criar_conexao()
    if conexao:
        try:
            cursor = conexao.cursor()
            cursor.execute(query)
            resultado = cursor.fetchall()
            return resultado
        except Exception as e:
            print(f"Erro ao executar a query: {e}")
            return None
        finally:
            cursor.close()
            conexao.close()
    return None

def gerar_resposta(dados_query):
    if not dados_query:
        return "Nenhum dado encontrado."

    respostas_amigaveis = []
    for d in dados_query:
        eficiencia_tecnica = d.get('eficiencia_tecnica', 'N/A')
        producao = d.get('producao', 'N/A')
        
        # Mensagem personalizada
        resposta = (
            f"A eficiência técnica registrada é de {eficiencia_tecnica}%, "
            f"o que indica quão bem a empresa está utilizando seus recursos. "
            f"Além disso, a produção foi de {producao} unidades."
        )
        respostas_amigaveis.append(resposta)

    resposta_final = " | ".join(respostas_amigaveis)
    return f"Aqui estão os resultados que encontrei: {resposta_final}"

@app.route("/chat", methods=["POST"])
def chat():
    prompt = request.json["msg"]
    resposta = bot(prompt)
    texto_resposta = resposta.content[0].text.value

    print("Resposta do Chatbot:", texto_resposta)  # Para depuração

    # Verifica se a resposta contém uma query SQL
    if "SELECT" in texto_resposta:
        print("Query gerada:", texto_resposta)  # Para depuração
        resultado_query = executar_query(texto_resposta)

        # Adicione um print para verificar o resultado da consulta
        print("Resultado da consulta:", resultado_query)  # Para depuração

        if resultado_query:
            # Obter o número de colunas retornadas
            num_colunas = len(resultado_query[0])  # Número de colunas na primeira linha
            print(f"Número de colunas retornadas: {num_colunas}")  # Para depuração
            
            # Defina as colunas dinamicamente com base no resultado
            colunas = [f"coluna_{i+1}" for i in range(num_colunas)]  # Exemplo de nomes de colunas

            resposta_final = []
            
            for linha in resultado_query:
                # Cria um dicionário para armazenar os resultados
                resultado = {}
                for i in range(num_colunas):
                    resultado[colunas[i]] = linha[i]  # Adiciona cada coluna ao dicionário
                resposta_final.append(resultado)

            # Formatar a resposta para o usuário
            if resposta_final:  # Verifica se há resultados
                # Ajuste a lógica de formatação com base nas colunas retornadas
                dados_formatados = ", ".join([f"{colunas[i]}: {d[colunas[i]]}" for d in resposta_final for i in range(num_colunas)])
                resposta_texto = f"Resultados: {dados_formatados}"
                print("Resultado da consulta formatado:", resposta_texto)  # Para depuração
                return resposta_texto  # Retorna a resposta gerada
            
            return "Nenhum resultado encontrado para a consulta."
        else:
            return "Não foi possível executar a query."
    
    # Se a consulta não for válida ou não retornar resultados, peça mais informações
    prompt_erro = """
    Parece que não consegui entender sua pergunta ou não consegui gerar uma consulta SQL válida. 
    Por favor, forneça mais detalhes sobre o que você gostaria de saber. 
    Tente incluir informações como:
    - O nome da empresa
    - A data específica
    - O tipo de dados que você está procurando (por exemplo, eficiência técnica, produção, etc.)
    """
    
    # Chamar a OpenAI para gerar uma resposta amigável pedindo mais informações
    resposta_gerada = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "user", "content": prompt_erro}
        ],
        temperature=1,
    )
    
    return resposta_gerada.choices[0].message.content.strip()

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug = True)

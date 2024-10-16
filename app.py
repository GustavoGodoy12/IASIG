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
                role="user",
                content=prompt
            )

            run = cliente.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistente.id
            )

            while run.status != "completed":
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

    partes_resposta = []
    eficiencia_tecnica_total = 0
    contador_eficiencia = 0
    producao_total = 0
    contador_producao = 0

    # Itera sobre os dados da consulta para construir a resposta
    for dado in dados_query:
        data = dado.get('data', None)
        producao = dado.get('producao', None)
        eficiencia_tecnica = dado.get('eficiencia_tecnica', None)
        eficiencia_global = dado.get('eficiencia_global', None)
        empresa = dado.get('empresa', 'N/A')

        # Coletar dados de produção
        if producao is not None:
            producao_total += producao  # Soma para totalizar a produção
            contador_producao += 1  # Conta para produção
        
        # Coletar dados de eficiência técnica
        if eficiencia_tecnica is not None:
            eficiencia_tecnica_total += eficiencia_tecnica  # Soma para calcular a média
            contador_eficiencia += 1  # Conta para a média

    # Montar partes da resposta com base nos dados disponíveis
    if contador_producao > 0:
        partes_resposta.append(f"A produção total é de {producao_total:.2f} unidades.")

    if contador_eficiencia > 0:
        media_eficiencia_tecnica = eficiencia_tecnica_total / contador_eficiencia
        partes_resposta.append(f"A eficiência média é de {media_eficiencia_tecnica:.2f} %.")

    # Criação do prompt dinâmico
    prompt = f"""
    Você é um assistente inteligente especializado em fornecer dados e análises de produção e eficiência. Com base nas informações a seguir, crie uma resposta amigável e clara.

    Dados:
    {' '.join(partes_resposta)}

    Insutruções:
    Se a informação for sobre eficiência técnica ou global, deve ser apresentada em porcentagem. 
    Se for sobre produção, deve ser apresentada em unidades. 
    Foque na clareza e na diferenciação entre os dois temas na sua resposta.

    Exemplo de uso:

    Para dados referentes a produção:
    Pergunta: Qual foi a produção total da (empresa) no ano de (data)

    Olá! De acordo com os dados fornecidos, a produção atual é de (producao) unidades. Por favor, note que este valor é expresso em unidades,
    pois estamos falando sobre produção. Se estivéssemos discutindo eficiência técnica ou global, os valores seriam apresentados em porcentagem.
    Espero que isso seja útil e claro para você. Se você tiver mais perguntas ou precisar de mais detalhes, sinta-se à vontade para perguntar!

    Para dados referentes a eficiências:
    Quero saber a média da eficiência técnica da Nestlé no ano de 2024

    Olá! Com base nos dados fornecidos, a eficiência média é de (eficiencia_tecnica) %. Por favor, note que essa informação é apresentada em porcentagem, que é a medida padrão para eficiências.
    Se tivéssemos informações sobre produção, essas seriam apresentadas em unidades. Espero que isso seja útil e estou aqui para qualquer outra informação que você possa precisar!
    """

    # Chama a OpenAI para gerar uma resposta
    resposta_gerada = cliente.chat.completions.create(
        model=modelo, 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  # Ajuste a temperatura conforme necessário
    )

    return resposta_gerada.choices[0].message.content.strip()


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

        print("Resultado da consulta:", resultado_query)  # Para depuração

        if resultado_query:
            # Obter o número de colunas retornadas
            num_colunas = len(resultado_query[0])  # Número de colunas na primeira linha
            print(f"Número de colunas retornadas: {num_colunas}")  # Para depuração
            
            # Defina as colunas dinamicamente com base no resultado
            colunas = ["producao", "eficiencia_tecnica", "eficiencia_global", "data", "empresa"]  

            resposta_final = []
            
            for linha in resultado_query:
                # Cria um dicionário para armazenar os resultados
                resultado = {}
                for i in range(num_colunas):
                    resultado[colunas[i]] = linha[i]  # Adiciona cada coluna ao dicionário
                resposta_final.append(resultado)

            # Formatar a resposta para o usuário usando a função gerar_resposta
            if resposta_final:  # Verifica se há resultados
                resposta_texto = gerar_resposta(resposta_final)  # Chama a função para gerar a resposta
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
        messages=[{"role": "user", "content": prompt_erro}],
        temperature=1,
    )
    
    return resposta_gerada.choices[0].message.content.strip()

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
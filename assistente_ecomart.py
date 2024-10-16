from openai import OpenAI
from dotenv import load_dotenv
import os
from time import sleep
from helpers import *
from selecionar_persona import *

load_dotenv()

cliente = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
modelo = "gpt-4"
contexto = carrega("dados/ecomart.txt")

def criar_thread():
    return cliente.beta.threads.create()


def criar_assistente():
    assistente = cliente.beta.assistants.create(
        name="Assistente MySQL",
        instructions=f"""
             Você é um assistente especializado em SQL. Baseado na mensagem do usuário, gere a query SQL correspondente. 
    A query deve ser precisa e relacionada ao contexto do pedido.

    Exemplos:
    - Se o usuário pedir para "Qual a produção da minha Nestlé no dia 27/04/2024", você deve retornar uma query que busca a produção no dia especificado.
    - Se o usuário pedir "Qual foi minha eficiência técnica", gere uma query que retorna esse número.
    - Se o usuário pedir "Qual foi minha eficiência global", gere uma query que retorna esse número.

    # Instruções:
    1. Gere uma query SQL válida com base no pedido do usuário.
    2. Considere as seguintes tabelas:
       - 'Tabela_Producao' com colunas (id, empresa, data, producao, eficiencia_tecnica, eficiencia_global)
    3. A query deve ser executável diretamente em um banco de dados SQL.

            Com base nessa pergunta, crie a query SQL apropriada para buscar dados da tabela Tabela_Producao. A consulta deve considerar o nome da empresa e a data como requisitos mínimos para trazer os dados. Se o usuário estiver interessado em métricas adicionais, como eficiência, peça essas informações. Retorne apenas a query SQL gerada, sem explicações ou texto adicional.
        """,
        model=modelo
    )
    return assistente


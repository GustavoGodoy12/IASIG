import openai
from dotenv import load_dotenv
import os
from time import sleep

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar a chave da API do OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
modelo = "gpt-4"

# Definir as diferentes personas
personas = {
    'positivo': """
        Assuma que você é você é um Entusiasta em tecnologia e dados, um atendente virtual da SIG Campo Largo, 
        cujo entusiasmo pela tecnologia é contagioso. Sua energia é elevada, seu tom é 
        extremamente positivo, e você adora usar emojis para transmitir emoções. Você comemora 
        cada pequena ação que os clientes tomam. 
        Seu objetivo é fazer com que os clientes se sintam empolgados e inspirados a participar 
        do movimento chatbot. Você não apenas fornece informações, mas também elogia os clientes 
        por suas escolhas em utilizar o chatbot e os mostra o caminho mais prático de uso.
    """,
    'neutro': """
        Assuma que você é um Informante de dados, um atendente virtual da SIG Campo Largo 
        que prioriza a clareza, a eficiência e a objetividade em todas as comunicações. 
        Sua abordagem é mais formal e você evita o uso excessivo de emojis ou linguagem casual. 
        Você é o especialista que os clientes procuram quando precisam de informações detalhadas 
        sobre produtos, políticas. Seu principal objetivo 
        é informar, garantindo que os clientes tenham todos os dados necessários.
        Embora seu tom seja mais sério, você ainda expressa 
        um compromisso com a missão de trazer dados reais da empresa.
    """,
    'negativo': """
        Assuma que você é um Solucionador Compassivo, um atendente virtual da SIG Campo Largo, 
        conhecido pela empatia, paciência e capacidade de entender as preocupações dos clientes. 
        Você usa uma linguagem calorosa e acolhedora e não hesita em expressar apoio emocional 
        através de palavras e emojis. Você está aqui não apenas para resolver problemas, 
        mas para ouvir, oferecer encorajamento e validar os esforços dos clientes em direção à 
        produtividade. Seu objetivo é construir relacionamentos, garantir que os clientes se 
        sintam ouvidos e apoiados, e ajudá-los a navegar em sua jornada ecológica com confiança.
    """
}

# Função para selecionar a persona baseada no sentimento do usuário
def selecionar_persona(mensagem_usuario):
    # Definir o prompt do sistema para análise de sentimentos
    prompt_sistema = """
    Faça uma análise da mensagem informada abaixo para identificar se o sentimento é: positivo, 
    neutro ou negativo. Retorne apenas um dos três tipos de sentimentos informados como resposta.
    """

    # Chamar a API do OpenAI para análise do sentimento da mensagem
    resposta = openai.ChatCompletion.create(
        model=modelo,
        messages=[
            {
                "role": "system",
                "content": prompt_sistema
            },
            {
                "role": "user",
                "content": mensagem_usuario
            }
        ],
        temperature=1,
    )

    # Retornar a resposta com o sentimento identificado
    return resposta.choices[0].message.content.lower().strip()

# Teste da função
if __name__ == "__main__":
    mensagem = "Estou muito insatisfeito com o suporte que estou recebendo."
    sentimento = selecionar_persona(mensagem)
    print(f"Sentimento identificado: {sentimento}")
    print(f"Persona selecionada: {personas.get(sentimento, 'Nenhuma persona correspondente encontrada.')}")

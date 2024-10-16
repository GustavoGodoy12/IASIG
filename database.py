# database.py
import mysql.connector
from mysql.connector import Error

# Configurações de conexão
config = {
    'user': 'projetoNODE',
    'password': 'gustavinho1',
    'host': '127.0.0.1',
    'database': 'projetoNODE'
}

def criar_conexao():
    try:
        conexao = mysql.connector.connect(**config)
        if conexao.is_connected():
            print('Conectado ao banco de dados!')
            return conexao
    except Error as e:
        print(f'Erro ao conectar ao banco de dados: {e}')
        return None
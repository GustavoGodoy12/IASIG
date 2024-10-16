# test_connection.py
from database import criar_conexao

def testar_conexao():
    conexao = criar_conexao()  # Chama a função para criar a conexão
    if conexao:  # Verifica se a conexão foi bem-sucedida
        print("Conexão bem-sucedida!")
        # Aqui você pode adicionar lógica para executar uma consulta simples, se desejar
        conexao.close()  # Fecha a conexão após o teste
    else:
        print("Falha ao conectar ao banco de dados.")

if __name__ == "__main__":
    testar_conexao()
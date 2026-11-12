import socket  # método para a comunicação
import threading  # método para o multicliente
import json  # formato das mensagens
import time
from datetime import datetime

# Configurações do servidor
HOST = "127.0.0.1"
PORT = 8000

# Regras da casa
ARQUIVO_CONSUMO = "consumo.txt"   # "base de dados" das tomadas
TEMP_LIMITE = 28                  # acima disso, liga o ar-condicionado
TEMP_AR = 22                      # temperatura definida ao ligar o ar
TEMPO_SEM_PRESENCA = 600          # 10 minutos sem presença apaga as lâmpadas

# Armazena os dispositivos conectados
dispositivos = {}

# Última presença detectada por ambiente (ambiente -> timestamp)
ultima_presenca = {}

# Impede alterações simultâneas no cadastro
lock = threading.Lock()

# Impede escritas simultâneas no arquivo de consumo
lock_arquivo = threading.Lock()


def enviar_mensagem(conexao, mensagem):
    # Envia uma mensagem JSON terminada em quebra de linha.
    dados = json.dumps(mensagem, ensure_ascii=False) + "\n"
    conexao.sendall(dados.encode("utf-8"))


def receber_mensagem(leitor):
    # Recebe uma mensagem JSON completa.
    linha = leitor.readline()

    if not linha:
        return None

    return json.loads(linha)


def salvar_consumo(dispositivo_id, ambiente, valor):
    # Grava uma linha no arquivo de registro: data;id;ambiente;consumo
    linha = (
        f"{datetime.now():%Y-%m-%d %H:%M:%S};"
        f"{dispositivo_id};{ambiente};{valor}\n"
    )

    with lock_arquivo:
        with open(ARQUIVO_CONSUMO, "a", encoding="utf-8") as arquivo:
            arquivo.write(linha)


def comandar_ambiente(ambiente, tipo, comando, valor):
    # Envia um comando a todos os dispositivos de um tipo em um ambiente.
    with lock:
        ids = [
            dispositivo_id
            for dispositivo_id, dados in dispositivos.items()
            if dados["ambiente"] == ambiente and dados["tipo"] == tipo
        ]

    for dispositivo_id in ids:
        enviar_comando(dispositivo_id, comando, valor)


def monitorar_presenca():
    # Thread que apaga as lâmpadas de ambientes sem presença há muito tempo.
    while True:
        time.sleep(5)
        agora = time.time()

        with lock:
            vencidos = [
                ambiente
                for ambiente, instante in ultima_presenca.items()
                if agora - instante > TEMPO_SEM_PRESENCA
            ]

            for ambiente in vencidos:
                del ultima_presenca[ambiente]

        for ambiente in vencidos:
            print(f"[AUTO] Sem presença em '{ambiente}': apagando lâmpadas.")
            comandar_ambiente(ambiente, "lampada", "desligar", False)


def processar_mensagem(dispositivo_id, mensagem):

    if not isinstance(mensagem, dict):
        print("Mensagem inválida.")
        return

    if mensagem.get("id") != dispositivo_id:
        print("ID da mensagem não corresponde ao dispositivo.")
        return

    # O ambiente vem do cadastro feito no registro, não da mensagem
    with lock:
        dispositivo = dispositivos.get(dispositivo_id)

    if dispositivo is None:
        return

    ambiente = dispositivo["ambiente"]
    tipo = mensagem.get("tipo")
    comando = mensagem.get("comando")
    valor = mensagem.get("valor")

    if tipo == "presenca" and comando == "presenca":
        if str(valor) == "1":
            print(f"[AUTO] Presença em '{ambiente}': acendendo lâmpadas.")

            with lock:
                ultima_presenca[ambiente] = time.time()

            comandar_ambiente(ambiente, "lampada", "ligar", True)

    elif tipo == "termometro" and comando == "temperatura":
        try:
            temperatura = float(valor)
        except (TypeError, ValueError):
            print("Temperatura inválida.")
            return

        print(f"Temperatura em '{ambiente}': {temperatura} °C")

        if temperatura > TEMP_LIMITE:
            print(f"[AUTO] {temperatura} °C em '{ambiente}': "
                  "ligando ar-condicionado.")
            comandar_ambiente(ambiente, "ar_condicionado", "ligar", TEMP_AR)

    elif tipo == "tomada" and comando == "consumo":
        salvar_consumo(dispositivo_id, ambiente, valor)
        print(f"Consumo de {dispositivo_id} registrado: {valor}")

    else:
        print("Comando não reconhecido.")


def enviar_comando(dispositivo_id, comando, valor):

    # Procura o dispositivo pelo ID
    with lock:
        dispositivo = dispositivos.get(dispositivo_id)

    if dispositivo is None:
        print(f"Dispositivo {dispositivo_id} não encontrado.")
        return

    # Monta a mensagem que será enviada
    mensagem = {
        "id": dispositivo_id,
        "tipo": dispositivo["tipo"],
        "ambiente": dispositivo["ambiente"],
        "comando": comando,
        "valor": valor
    }

    # Bloqueia outros envios simultâneos para esse dispositivo
    try:
        with dispositivo["send_lock"]:
            enviar_mensagem(dispositivo["conexao"], mensagem)

        print(f"Comando '{comando}' enviado para {dispositivo_id}.")

    except OSError:
        print(f"Não foi possível enviar comando para {dispositivo_id}.")


def tratar_cliente(conexao, endereco):
    # Gerencia a comunicação com um dispositivo conectado.
    dispositivo_id = None
    registrado = False
    leitor = conexao.makefile("r", encoding="utf-8")

    try:
        print(f"\n[+] Nova conexão: {endereco}")

        # Recebe a identificação inicial
        identificacao = receber_mensagem(leitor)

        if identificacao is None:
            return

        if not isinstance(identificacao, dict):
            return

        if not all(isinstance(identificacao.get(campo), str)
                   and identificacao[campo].strip()
                   for campo in ("id", "tipo", "ambiente")):
            enviar_mensagem(conexao, {
                "comando": "erro",
                "valor": "Identificação inválida."
            })
            return

        dispositivo_id = identificacao["id"]
        tipo = identificacao["tipo"]
        ambiente = identificacao["ambiente"].strip().lower()

        with lock:
            if dispositivo_id in dispositivos:
                enviar_mensagem(conexao, {
                    "comando": "erro",
                    "valor": "ID já está conectado."
                })
                return

            dispositivos[dispositivo_id] = {
                "tipo": tipo,
                "ambiente": ambiente,
                "conexao": conexao,
                "send_lock": threading.Lock()
            }

        print(f"[+] Dispositivo registrado: {dispositivo_id}")
        print(f"    Tipo: {tipo} | Ambiente: {ambiente}")

        enviar_mensagem(conexao, {
            "comando": "registrado",
            "valor": "Dispositivo conectado com sucesso!"
        })
        registrado = True

        # Mantém a comunicação com o dispositivo
        while True:
            mensagem = receber_mensagem(leitor)

            if mensagem is None:
                break

            print(f"\n[{dispositivo_id}] Mensagem recebida:")
            print(mensagem)

            processar_mensagem(dispositivo_id, mensagem)

    except (ConnectionResetError, BrokenPipeError):
        print(f"[-] Conexão perdida: {endereco}")

    except (json.JSONDecodeError, KeyError, TypeError) as erro:
        print(f"[-] Mensagem inválida de {endereco}: {erro}")

    finally:
        if registrado:
            with lock:
                dispositivos.pop(dispositivo_id, None)

        leitor.close()
        conexao.close()

        print(f"[-] Conexão encerrada: {endereco}")


def comando_manual(opcao):
    # Trata as opções do menu que ligam/desligam lâmpada ou ar-condicionado.
    if opcao in ("2", "3"):
        tipo_esperado, nome = "lampada", "lâmpada"
    else:
        tipo_esperado, nome = "ar_condicionado", "ar-condicionado"

    dispositivo_id = input(f"Digite o ID do {nome}: ").strip()

    with lock:
        dispositivo = dispositivos.get(dispositivo_id)

    if dispositivo is None:
        print("Dispositivo não encontrado.")

    elif dispositivo["tipo"] != tipo_esperado:
        print(f"Esse dispositivo não é {'uma' if tipo_esperado == 'lampada' else 'um'} {nome}.")

    elif opcao == "2":
        enviar_comando(dispositivo_id, "ligar", True)

    elif opcao == "3":
        enviar_comando(dispositivo_id, "desligar", False)

    elif opcao == "4":
        enviar_comando(dispositivo_id, "ligar", TEMP_AR)

    else:
        enviar_comando(dispositivo_id, "desligar", None)


def menu_comandos():

    while True:
        print("\n======= CONTROLE SMART HOME =======")
        print("1 - Listar dispositivos conectados")
        print("2 - Ligar lâmpada")
        print("3 - Desligar lâmpada")
        print("4 - Ligar ar-condicionado")
        print("5 - Desligar ar-condicionado")
        print("0 - Fechar menu")

        try:
            opcao = input("\nEscolha uma opção: ").strip()
        except EOFError:
            break

        if opcao == "1":

            with lock:
                lista = list(dispositivos.items())

            if not lista:
                print("Nenhum dispositivo conectado.")

            for dispositivo_id, dados in lista:
                print(
                    f"ID: {dispositivo_id} | "
                    f"Tipo: {dados['tipo']} | "
                    f"Ambiente: {dados['ambiente']}"
                )

        elif opcao in ("2", "3", "4", "5"):
            comando_manual(opcao)

        elif opcao == "0":
            print("Menu de controle encerrado.")
            break

        else:
            print("Opção inválida.")


# a função principal do servidor
def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    servidor.bind((HOST, PORT))
    servidor.listen()

    print("===================================")
    print("       SERVIDOR SMART HOME")
    print("===================================")
    print(f"Servidor aguardando conexões em {HOST}:{PORT}")

    threading.Thread(target=menu_comandos, daemon=True).start()
    threading.Thread(target=monitorar_presenca, daemon=True).start()

    try:
        while True:
            conexao, endereco = servidor.accept()
            thread = threading.Thread(
                target=tratar_cliente,
                args=(conexao, endereco),
                daemon=True
            )
            thread.start()

    except KeyboardInterrupt:
        print("\n[!] Encerrando servidor...")

    finally:
        servidor.close()


# iniciando o programa pela função principal
if __name__ == "__main__":
    main()

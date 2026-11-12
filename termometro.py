import socket
import json
import threading

HOST = "127.0.0.1"
PORTA = 8000

TIPO = "termometro"
NOME = "Termômetro"


def enviar_mensagem(cliente, mensagem):
    """Envia uma mensagem JSON ao servidor."""
    dados = json.dumps(mensagem, ensure_ascii=False) + "\n"
    cliente.sendall(dados.encode("utf-8"))


def receber_mensagem(leitor):
    """Recebe uma mensagem JSON do servidor."""
    linha = leitor.readline()

    if not linha:
        return None

    return json.loads(linha)


def montar_mensagem(dispositivo_id, ambiente, comando, valor):
    """Monta uma mensagem do protocolo."""
    return {
        "id": dispositivo_id,
        "tipo": TIPO,
        "ambiente": ambiente,
        "comando": comando,
        "valor": valor
    }


def escutar_servidor(leitor):
    """Escuta os comandos enviados pelo servidor."""
    while True:
        try:
            mensagem = receber_mensagem(leitor)

            if mensagem is None:
                print("\n[-] Servidor encerrou a conexão.")
                break

            comando = mensagem.get("comando")
            valor = mensagem.get("valor")

            print(f"\n[Servidor] {valor}")

        except (ConnectionResetError, OSError):
            print("\n[-] Conexão com o servidor perdida.")
            break

        except json.JSONDecodeError:
            print("\n[-] Mensagem inválida recebida.")
            break


def main():

    print("======= SMART HOME - TERMÔMETRO =======")

    dispositivo_id = input("Digite o ID do dispositivo: ").strip()
    ambiente = input("Digite o ambiente: ").strip().lower()

    if not dispositivo_id or not ambiente:
        print("ID e ambiente são obrigatórios.")
        return

    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        cliente.connect((HOST, PORTA))

        leitor = cliente.makefile("r", encoding="utf-8")

        # Identificação inicial do dispositivo
        enviar_mensagem(
            cliente,
            montar_mensagem(dispositivo_id, ambiente, "registrar", None)
        )

        resposta = receber_mensagem(leitor)

        if resposta is None:
            print("Servidor encerrou a conexão.")
            return

        print(f"\nServidor: {resposta['valor']}")

        if resposta["comando"] != "registrado":
            return

        # Thread que escuta os comandos do servidor
        threading.Thread(
            target=escutar_servidor,
            args=(leitor,),
            daemon=True
        ).start()

        while True:
            entrada = input(
                "\nDigite a temperatura (°C) ou 'sair' para desconectar: "
            ).strip()

            if entrada.lower() == "sair":
                break

            try:
                temperatura = float(entrada.replace(",", "."))
            except ValueError:
                print("Valor inválido. Digite um número.")
                continue

            enviar_mensagem(
                cliente,
                montar_mensagem(dispositivo_id, ambiente, "temperatura", temperatura)
            )
            print(f"[TERMÔMETRO] {temperatura} °C informado ao servidor.")

        leitor.close()

    except ConnectionRefusedError:
        print("Não foi possível conectar. Verifique se o servidor está ativo.")

    except (ConnectionResetError, BrokenPipeError):
        print("A conexão com o servidor foi encerrada.")

    except (KeyboardInterrupt, EOFError):
        pass

    finally:
        cliente.close()
        print("\nDispositivo desconectado.")


if __name__ == "__main__":
    main()

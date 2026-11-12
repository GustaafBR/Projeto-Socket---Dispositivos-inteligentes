# 🏠 Smart Home – Programação Socket (TCP)

Trabalho da disciplina de **Lógica de Programação** (Prof. Márcio Clay).

Aplicação **cliente/servidor** em Python, usando a biblioteca `socket` e o protocolo **TCP**, que simula o controle de dispositivos inteligentes de uma residência. Cada dispositivo (lâmpada, tomada, sensor de presença, ar-condicionado e termômetro) é um **cliente** independente, e todos se comunicam com um **servidor central** multithread que aplica as regras de automação da casa.

**Autores:** _[Nome 1]_ e _[Nome 2]_

---

## 📑 Sumário

1. [Estrutura do projeto](#-estrutura-do-projeto)
2. [Requisitos](#-requisitos)
3. [Como executar](#-como-executar)
4. [Como usar cada dispositivo](#-como-usar-cada-dispositivo)
5. [Regras de automação](#-regras-de-automação)
6. [Protocolo de mensagens](#-protocolo-de-mensagens)
7. [Arquivo de registro (consumo)](#-arquivo-de-registro-de-consumo)
8. [Exemplo de demonstração](#-exemplo-de-demonstração)
9. [Como o sistema funciona por dentro](#-como-o-sistema-funciona-por-dentro)
10. [Configurações ajustáveis](#-configurações-ajustáveis)

---

## 📁 Estrutura do projeto

```
smart-home-socket/
├── mainserver.py      # Servidor central (multithread)
├── lampada.py         # Cliente: lâmpada
├── tomada.py          # Cliente: tomada
├── presenca.py        # Cliente: sensor de presença
├── arCondicionado.py  # Cliente: ar-condicionado
├── termometro.py      # Cliente: termômetro
├── consumo.txt        # Registro de consumo (gerado automaticamente)
└── README.md
```

| Arquivo | Dispositivo | Papel |
|---|---|---|
| `mainserver.py` | Servidor | Registra dispositivos, aplica regras, grava consumo, oferece menu manual |
| `lampada.py` | Lâmpada | Liga/desliga conforme comandos do servidor |
| `tomada.py` | Tomada | Envia consumo aleatório a cada 2 minutos |
| `presenca.py` | Sensor de presença | Informa presença de pessoas ao servidor |
| `arCondicionado.py` | Ar-condicionado | Liga/desliga conforme comandos do servidor |
| `termometro.py` | Termômetro | Informa a temperatura do ambiente ao servidor |

---

## ✅ Requisitos

- **Python 3.8+** (usa apenas a biblioteca padrão: `socket`, `threading`, `json`, `time`, `random`, `datetime`)
- Nenhuma instalação adicional de pacotes.
- Todos os programas rodam na mesma máquina (`127.0.0.1`, porta `8000`).

---

## ▶️ Como executar

Use **um terminal para cada programa**, dentro da pasta do projeto.

### 1. Iniciar o servidor (sempre primeiro)

```bash
python mainserver.py
```

O servidor passa a aguardar conexões em `127.0.0.1:8000` e exibe um menu de controle manual.

### 2. Iniciar os dispositivos (clientes)

Em outros terminais, execute os dispositivos desejados:

```bash
python lampada.py
python tomada.py
python presenca.py
python arCondicionado.py
python termometro.py
```

Cada cliente pergunta:

- **ID do dispositivo:** identificador único (ex.: `L1`, `AR1`). Não pode haver dois dispositivos conectados com o mesmo ID.
- **Ambiente:** local onde o dispositivo está (ex.: `sala`, `quarto`). Não diferencia maiúsculas de minúsculas (`Sala` = `sala`).

> 💡 Dispositivos do **mesmo ambiente** interagem entre si. Uma presença na `sala` acende as lâmpadas da `sala`, mas não as do `quarto`.

Para encerrar um cliente, digite `sair`. Para encerrar o servidor, use `Ctrl+C`.

---

## 🎮 Como usar cada dispositivo

| Dispositivo | O que o usuário faz | O que aparece no console |
|---|---|---|
| **Lâmpada** | Nada (apenas aguarda) | `[LÂMPADA] ligada` / `[LÂMPADA] desligada` |
| **Tomada** | Nada (envio automático a cada 2 min) | `[TOMADA] Consumo enviado: X A` |
| **Sensor de presença** | Digita `1` para simular presença | `[PRESENÇA] Presença informada ao servidor.` |
| **Ar-condicionado** | Nada (apenas aguarda) | `[AR-CONDICIONADO] ligado com temperatura 22 graus` / `[AR-CONDICIONADO] desligado` |
| **Termômetro** | Digita a temperatura (ex.: `30` ou `30,5`) | `[TERMÔMETRO] 30.0 °C informado ao servidor.` |

### Menu do servidor

O servidor possui um menu para controle manual:

```
1 - Listar dispositivos conectados
2 - Ligar lâmpada
3 - Desligar lâmpada
4 - Ligar ar-condicionado
5 - Desligar ar-condicionado
0 - Fechar menu
```

As opções 2 a 5 pedem o **ID** do dispositivo e validam se ele existe e se é do tipo correto.

---

## ⚙️ Regras de automação

O servidor aplica as seguintes regras, sempre **por ambiente**:

| Evento | Ação do servidor |
|---|---|
| Sensor de presença envia `1` | **Liga as lâmpadas** do ambiente e reinicia o contador de 10 minutos |
| 10 minutos sem nova presença no ambiente | **Desliga as lâmpadas** do ambiente |
| Termômetro informa temperatura **acima de 28 °C** | **Liga os ar-condicionados** do ambiente, com temperatura definida em **22 °C** |
| Tomada envia consumo | **Grava** o registro no arquivo `consumo.txt` |

Uma thread de monitoramento verifica a cada 5 segundos se algum ambiente ultrapassou o tempo sem presença.

---

## 📨 Protocolo de mensagens

As mensagens são objetos **JSON**, enviados **um por linha** (terminados em `\n`), o que permite ao receptor ler uma mensagem completa com `readline()`.

### Campos

| Campo | Descrição |
|---|---|
| `id` | ID do dispositivo *(obrigatório)* |
| `tipo` | `lampada`, `tomada`, `presenca`, `ar_condicionado` ou `termometro` |
| `ambiente` | Ambiente onde o dispositivo está instalado |
| `comando` | Mensagem de controle *(obrigatório)* |
| `valor` | Dado associado ao comando (número, booleano, texto ou `null`) |

### Comandos

| Comando | Sentido | `valor` | Descrição |
|---|---|---|---|
| `registrar` | cliente → servidor | `null` | Apresentação inicial: informa `id`, `tipo` e `ambiente` |
| `registrado` | servidor → cliente | texto | Confirma o registro do dispositivo |
| `erro` | servidor → cliente | texto | Registro recusado (ID duplicado ou identificação inválida) |
| `presenca` | cliente → servidor | `1` | Presença detectada no ambiente |
| `temperatura` | cliente → servidor | número (°C) | Temperatura atual do ambiente |
| `consumo` | cliente → servidor | número (A) | Corrente medida pela tomada |
| `ligar` | servidor → cliente | `true` (lâmpada) ou `22` (ar) | Liga o dispositivo; no ar, informa a temperatura |
| `desligar` | servidor → cliente | `false` ou `null` | Desliga o dispositivo |

### Exemplos

Registro de um dispositivo:

```json
{"id": "L1", "tipo": "lampada", "ambiente": "sala", "comando": "registrar", "valor": null}
```

Resposta do servidor:

```json
{"comando": "registrado", "valor": "Dispositivo conectado com sucesso!"}
```

Sensor de presença:

```json
{"id": "P1", "tipo": "presenca", "ambiente": "sala", "comando": "presenca", "valor": 1}
```

Termômetro:

```json
{"id": "T1", "tipo": "termometro", "ambiente": "sala", "comando": "temperatura", "valor": 30.5}
```

Comando do servidor para o ar-condicionado:

```json
{"id": "AR1", "tipo": "ar_condicionado", "ambiente": "sala", "comando": "ligar", "valor": 22}
```

---

## 📄 Arquivo de registro de consumo

O servidor grava o consumo enviado pelas tomadas em **`consumo.txt`**, criado automaticamente na pasta onde o servidor foi executado. Cada linha representa um relatório:

```
AAAA-MM-DD HH:MM:SS;id_da_tomada;ambiente;consumo_em_A
```

Exemplo:

```
2026-11-12 16:36:34;T1;sala;7.01
2026-11-12 16:36:37;T1;sala;1.76
```

Para visualizar, abra o arquivo em qualquer editor de texto ou use:

```bash
# Linux / macOS
cat consumo.txt

# Windows (PowerShell)
type consumo.txt
```

---

## 🎬 Exemplo de demonstração

Cenário completo com o ambiente `sala`:

1. Inicie `mainserver.py`.
2. Inicie `lampada.py` (ID `L1`, ambiente `sala`).
3. Inicie `arCondicionado.py` (ID `AR1`, ambiente `sala`).
4. Inicie `presenca.py` (ID `P1`, ambiente `sala`).
5. Inicie `termometro.py` (ID `T1`, ambiente `sala`).
6. Inicie `tomada.py` (ID `TM1`, ambiente `sala`).

Em seguida:

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | Em `presenca.py`, digite `1` | Lâmpada exibe `ligada` |
| 2 | Em `termometro.py`, digite `25` | Nada acontece (abaixo de 28 °C) |
| 3 | Em `termometro.py`, digite `30` | Ar exibe `ligado com temperatura 22 graus` |
| 4 | Aguarde 2 min | Tomada envia consumo e o servidor grava em `consumo.txt` |
| 5 | Aguarde 10 min sem presença | Lâmpada exibe `desligada` |
| 6 | No menu do servidor, opção `1` | Lista os dispositivos conectados |
| 7 | No menu do servidor, opção `2` | Liga a lâmpada manualmente |

> Para testar mais rápido, veja [Configurações ajustáveis](#-configurações-ajustáveis).

---

## 🔧 Como o sistema funciona por dentro

### Fluxo de conexão

```
Dispositivo                         Servidor
    |------ connect (TCP) ------------>|
    |------ "registrar" (id,tipo,amb)->|  valida e cadastra o dispositivo
    |<----- "registrado" / "erro" -----|
    |                                  |
    |======= modo de operação ========|
    |------ presenca/temperatura/consumo ->|  aplica regras de automação
    |<----- ligar/desligar ------------|
```

### Pontos principais da implementação

- **Multithread:** o servidor cria uma thread para cada dispositivo conectado (`tratar_cliente`), além de uma thread para o menu manual e outra para monitorar a presença.
- **Cadastro protegido:** o dicionário `dispositivos` é protegido por um `Lock`, evitando condições de corrida entre threads.
- **Envio protegido:** cada dispositivo tem seu próprio `send_lock`, impedindo que duas threads enviem mensagens simultâneas pela mesma conexão.
- **Clientes com duas threads:** uma escuta os comandos do servidor enquanto a principal lê o teclado (e, na tomada, uma terceira envia o consumo periodicamente).
- **Ambiente vem do cadastro:** o servidor usa o ambiente informado no registro, não o que vem em cada mensagem, o que evita inconsistências.
- **Validações:** ID duplicado, identificação incompleta, JSON inválido e temperaturas não numéricas são tratados sem derrubar o servidor.

---

## 🛠 Configurações ajustáveis

No início do `mainserver.py`:

| Constante | Valor padrão | Função |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Endereço e porta do servidor |
| `ARQUIVO_CONSUMO` | `consumo.txt` | Arquivo de registro de consumo |
| `TEMP_LIMITE` | `28` | Temperatura acima da qual o ar é ligado |
| `TEMP_AR` | `22` | Temperatura definida ao ligar o ar |
| `TEMPO_SEM_PRESENCA` | `600` | Segundos sem presença para apagar as lâmpadas (10 min) |

Em `tomada.py`:

| Constante | Valor padrão | Função |
|---|---|---|
| `INTERVALO_CONSUMO` | `120` | Segundos entre os relatórios de consumo (2 min) |

> ⚠️ Para **testes rápidos**, reduza `TEMPO_SEM_PRESENCA` (ex.: `10`) e `INTERVALO_CONSUMO` (ex.: `5`). Lembre-se de restaurar os valores originais (`600` e `120`) antes da entrega.

Se os clientes forem executados em outra máquina, altere `HOST` nos arquivos dos clientes para o IP do servidor (e `HOST` do servidor para `0.0.0.0`).

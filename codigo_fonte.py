# -*- coding: utf-8 -*-
"""
============================================================================
 SIGIC - Sistema Inteligente de Gerenciamento da Infraestrutura da Colonia
 Colonia Aurora Siger  |  Fase 4 - "Energia para sobreviver"
============================================================================

============================================================================
"""

import math
import os
import json
import sys

# Tenta usar UTF-8 na saida do terminal para exibir acentos corretamente.
# (Nao afeta a logica; apenas a apresentacao no terminal.)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

INF = float("inf")  # "infinito" usado como distancia inicial no Dijkstra


# ===========================================================================
# 1. DADOS DA INFRAESTRUTURA DA COLONIA
# ===========================================================================
# Os dados ficam em 'arquivos_auxiliares/dados_colonia.json' (unica fonte de
# dados do sistema) e sao carregados em DICIONARIOS (cada modulo e
# identificado por uma CHAVE, o seu codigo curto) e TUPLAS (a posicao (x, y)
# de cada modulo no mapa, e cada conexao na forma (origem, destino, peso)).
#
# Atributos de cada modulo:
#   nome        -> nome por extenso do modulo
#   consumo     -> consumo energetico, em kW
#   prioridade  -> prioridade operacional de 1 (baixa) a 5 (vital)
#   capacidade  -> capacidade de armazenamento de energia, em kWh
#   comunicacao -> necessidade de comunicacao (Baixa / Media / Alta)
#   status      -> situacao atual: ativo / manutencao / alerta
#   pos         -> TUPLA (x, y) com a posicao no mapa da base
# ---------------------------------------------------------------------------

CAMINHO_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "arquivos_auxiliares", "dados_colonia.json")

# Parametros didaticos usados nas simulacoes e na modelagem matematica.
COEF_PERDA = 0.0003   # coeficiente de perda na transmissao, por metro de cabo
# Modelo logistico de crescimento do consumo (ver opcao 7 do menu):
MODELO_K = 1200.0     # K  -> capacidade maxima de geracao sustentavel (kW)
MODELO_E0 = 120.0     # E0 -> demanda inicial da colonia (kW)
MODELO_R = 0.15       # r  -> taxa de crescimento da demanda (por mes marciano)


# ===========================================================================
# 2. CARGA DOS DADOS (arquivo auxiliar)
# ===========================================================================
def carregar_dados():
    """Carrega os dados da colonia a partir de
    'arquivos_auxiliares/dados_colonia.json' (unica fonte de dados do
    sistema).
    """
    with open(CAMINHO_DADOS, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    modulos = {}
    for codigo, info in dados["modulos"].items():
        info = dict(info)
        info["pos"] = tuple(info["pos"])   # lista do JSON -> tupla
        modulos[codigo] = info
    arestas = [tuple(a) for a in dados["arestas"]]
    return modulos, arestas


# ===========================================================================
# 3. CONSTRUCAO DO GRAFO (lista e matriz de adjacencia)
# ===========================================================================
def construir_grafo(modulos, arestas):
    """Monta a LISTA DE ADJACENCIA como um dicionario de dicionarios:
        grafo[u][v] = peso da conexao entre u e v.
    O grafo e NAO-DIRECIONADO, entao cada aresta e registrada nos dois sentidos.
    """
    grafo = {codigo: {} for codigo in modulos}
    for (u, v, peso) in arestas:
        # Validacao defensiva: ignora conexoes invalidas para que o sistema
        # nao quebre caso os dados tenham algum erro de digitacao.
        if u not in grafo or v not in grafo:
            ausente = u if u not in grafo else v
            print("[aviso] Conexao ignorada: o modulo '%s' nao existe na base." % ausente)
            continue
        if u == v:
            print("[aviso] Conexao ignorada: '%s' ligado a ele mesmo (laco)." % u)
            continue
        grafo[u][v] = peso
        grafo[v][u] = peso
    return grafo


def construir_matriz(modulos, grafo):
    """Monta a MATRIZ DE ADJACENCIA como uma lista de listas.
    M[i][j] = peso da conexao entre o modulo i e o modulo j (0 se nao houver).
    Retorna a lista de codigos (define a ordem das linhas/colunas) e a matriz.
    """
    codigos = list(modulos.keys())
    indice = {codigo: i for i, codigo in enumerate(codigos)}
    n = len(codigos)
    matriz = [[0] * n for _ in range(n)]   # matriz n x n preenchida com zeros
    for u in grafo:
        for v, peso in grafo[u].items():
            matriz[indice[u]][indice[v]] = peso
    return codigos, matriz


# ===========================================================================
# 4. ALGORITMOS DE REDE
# ===========================================================================
def bfs(grafo, origem):
    """Busca em Largura (BFS).

    Explora a rede por niveis a partir da 'origem' usando uma FILA (implementada
    com uma LISTA e um ponteiro de leitura). Retorna:
        ordem  -> lista com a ordem de visita dos modulos
        nivel  -> dicionario {modulo: distancia em numero de saltos ate a origem}
        anterior -> dicionario {modulo: modulo de onde se chegou}
    """
    visitado = {origem}
    nivel = {origem: 0}
    anterior = {origem: None}
    ordem = []
    fila = [origem]
    i = 0  # ponteiro para o inicio da fila (evita remover do inicio da lista)
    while i < len(fila):
        atual = fila[i]
        i += 1
        ordem.append(atual)
        # vizinhos em ordem alfabetica -> resultado sempre reproduzivel
        for vizinho in sorted(grafo[atual]):
            if vizinho not in visitado:
                visitado.add(vizinho)
                nivel[vizinho] = nivel[atual] + 1
                anterior[vizinho] = atual
                fila.append(vizinho)
    return ordem, nivel, anterior


def dfs(grafo, origem):
    """Busca em Profundidade (DFS).

    Caminha o mais fundo possivel antes de retroceder, usando uma PILHA
    (lista com append/pop). Retorna a ordem de visita e o dicionario 'anterior'.
    """
    visitado = set()
    anterior = {origem: None}
    ordem = []
    pilha = [origem]
    while pilha:
        atual = pilha.pop()
        if atual in visitado:
            continue
        visitado.add(atual)
        ordem.append(atual)
        # 'reversed' faz a visita seguir a ordem alfabetica crescente
        for vizinho in sorted(grafo[atual], reverse=True):
            if vizinho not in visitado:
                if vizinho not in anterior:
                    anterior[vizinho] = atual
                pilha.append(vizinho)
    return ordem, anterior


def dijkstra(grafo, origem):
    """Algoritmo de Dijkstra para caminhos minimos.

    Calcula o menor custo (distancia) da 'origem' ate todos os demais modulos.
    Implementacao classica O(V^2): a cada passo escolhe o modulo nao visitado
    de menor distancia. Funciona bem para redes pequenas como a da colonia e
    usa apenas dicionarios e listas. Retorna:
        dist     -> dicionario {modulo: menor custo a partir da origem}
        anterior -> dicionario para reconstruir o caminho
    """
    dist = {v: INF for v in grafo}
    anterior = {v: None for v in grafo}
    dist[origem] = 0
    visitado = set()

    while len(visitado) < len(grafo):
        # 1) escolhe o modulo nao visitado com a menor distancia conhecida
        atual = None
        menor = INF
        for v in grafo:
            if v not in visitado and dist[v] < menor:
                menor = dist[v]
                atual = v
        if atual is None:
            break  # os modulos restantes sao inacessiveis a partir da origem

        # 2) "fecha" o modulo escolhido e relaxa as arestas vizinhas
        visitado.add(atual)
        for vizinho, peso in grafo[atual].items():
            novo = dist[atual] + peso
            if novo < dist[vizinho]:
                dist[vizinho] = novo
                anterior[vizinho] = atual
    return dist, anterior


def reconstruir_caminho(anterior, origem, destino):
    """Reconstroi o caminho origem -> destino a partir do dicionario 'anterior'.
    Retorna a lista de modulos do caminho, ou lista vazia se nao houver caminho.
    """
    caminho = []
    atual = destino
    while atual is not None:
        caminho.append(atual)
        if atual == origem:
            break
        atual = anterior.get(atual)
    caminho.reverse()
    if caminho and caminho[0] == origem:
        return caminho
    return []


# --- Conectividade, pontes e pontos de articulacao -------------------------
def contar_componentes(grafo, no_excluido=None, aresta_excluida=None):
    """Conta quantos COMPONENTES CONEXOS o grafo possui (via BFS), podendo
    ignorar um vertice (no_excluido) ou uma aresta (aresta_excluida, um conjunto
    {u, v}). E a base para detectar conexoes criticas e pontos de articulacao.
    """
    nos = [v for v in grafo if v != no_excluido]
    conjunto_nos = set(nos)
    visitado = set()
    componentes = 0
    for inicio in nos:
        if inicio in visitado:
            continue
        componentes += 1
        fila = [inicio]
        visitado.add(inicio)
        i = 0
        while i < len(fila):
            atual = fila[i]
            i += 1
            for vizinho in grafo[atual]:
                if vizinho not in conjunto_nos or vizinho in visitado:
                    continue
                if aresta_excluida is not None and {atual, vizinho} == aresta_excluida:
                    continue
                visitado.add(vizinho)
                fila.append(vizinho)
    return componentes


def esta_conexo(grafo):
    """Retorna True se a rede inteira esta conectada (um unico componente)."""
    return contar_componentes(grafo) <= 1


def detectar_pontes(grafo, arestas):
    """Detecta as PONTES (conexoes criticas): arestas cuja remocao aumenta o
    numero de componentes, ou seja, parte a rede em pedacos. Estrategia direta:
    remove cada aresta e verifica se a rede se desconecta.
    """
    base = contar_componentes(grafo)
    pontes = []
    for (u, v, peso) in arestas:
        if contar_componentes(grafo, aresta_excluida={u, v}) > base:
            pontes.append((u, v, peso))
    return pontes


def detectar_articulacoes(grafo):
    """Detecta os PONTOS DE ARTICULACAO: modulos cuja falha desconecta a rede
    (isola outros modulos). Remove cada vertice e verifica a conectividade.
    """
    base = contar_componentes(grafo)
    articulacoes = []
    for v in grafo:
        if contar_componentes(grafo, no_excluido=v) > base:
            articulacoes.append(v)
    return articulacoes


# ===========================================================================
# 5. MODELAGEM MATEMATICA (modelo logistico + calculo diferencial)
# ===========================================================================
# Fenomeno modelado: CRESCIMENTO DO CONSUMO ENERGETICO da colonia ao longo do
# tempo, conforme novos modulos sao ativados. Usa-se a funcao LOGISTICA, pois o
# crescimento e rapido no inicio e desacelera ao se aproximar do limite de
# geracao sustentavel (K). Formula:
#
#       E(t) = K / (1 + A * e^(-r * t))        com  A = (K - E0) / E0
#
#   E(t) -> demanda de energia no tempo t (kW)
#   K    -> capacidade maxima de geracao sustentavel (kW)
#   E0   -> demanda inicial da colonia (kW)
#   r    -> taxa de crescimento
#   t    -> tempo (meses marcianos)
#
# Derivada (taxa de variacao da demanda):
#       dE/dt = r * E(t) * (1 - E(t)/K)
#
# A derivada e maxima no PONTO DE INFLEXAO, quando E = K/2, no instante
#       t* = ln(A) / r
# Esse instante e o momento de maior pressao sobre a rede e serve de alerta
# para planejar a ampliacao da geracao antes da saturacao.
# ---------------------------------------------------------------------------
def consumo_E(t):
    A = (MODELO_K - MODELO_E0) / MODELO_E0
    return MODELO_K / (1.0 + A * math.exp(-MODELO_R * t))


def derivada_E(t):
    E = consumo_E(t)
    return MODELO_R * E * (1.0 - E / MODELO_K)


def tempo_para_fracao(fracao):
    """Tempo necessario para a demanda atingir uma fracao da capacidade K."""
    A = (MODELO_K - MODELO_E0) / MODELO_E0
    valor = ((1.0 / fracao) - 1.0) / A
    if valor <= 0:
        return 0.0
    return -math.log(valor) / MODELO_R


def tempo_inflexao():
    """Instante t* do ponto de inflexao (onde a demanda cresce mais rapido)."""
    A = (MODELO_K - MODELO_E0) / MODELO_E0
    return math.log(A) / MODELO_R


# ===========================================================================
# 6. FUNCOES DE INTERFACE (menu e leitura de dados do usuario)
# ===========================================================================
def linha(caractere="=", largura=74):
    print(caractere * largura)


def cabecalho(titulo):
    print()
    linha()
    print(" " + titulo)
    linha()


def pausar():
    try:
        input("\nPressione ENTER para voltar ao menu...")
    except EOFError:
        pass


def ler_inteiro(prompt, minimo, maximo):
    """Le um numero inteiro dentro de um intervalo. Retorna None se o usuario
    encerrar a entrada (Ctrl+Z / EOF)."""
    while True:
        try:
            texto = input(prompt).strip()
        except EOFError:
            print()
            return None
        if texto == "":
            print("  >> Entrada vazia. Digite um numero.")
            continue
        try:
            valor = int(texto)
        except ValueError:
            print("  >> Valor invalido. Digite um numero inteiro.")
            continue
        if valor < minimo or valor > maximo:
            print("  >> Fora do intervalo permitido (%d a %d)." % (minimo, maximo))
            continue
        return valor


def ler_float(prompt, minimo, maximo, padrao):
    """Le um numero real dentro de um intervalo. ENTER vazio usa o 'padrao'."""
    while True:
        try:
            texto = input(prompt).strip().replace(",", ".")
        except EOFError:
            print()
            return padrao
        if texto == "":
            return padrao
        try:
            valor = float(texto)
        except ValueError:
            print("  >> Valor invalido. Digite um numero.")
            continue
        if valor < minimo or valor > maximo:
            print("  >> Fora do intervalo permitido (%s a %s)." % (minimo, maximo))
            continue
        return valor


def escolher_modulo(modulos, prompt="Escolha um modulo:"):
    """Mostra a lista numerada de modulos e retorna o codigo escolhido (ou None)."""
    codigos = list(modulos.keys())
    print(prompt)
    for i, codigo in enumerate(codigos, 1):
        print("   %2d. %-26s [%s]" % (i, modulos[codigo]["nome"], codigo))
    n = ler_inteiro("Numero do modulo (0 para cancelar): ", 0, len(codigos))
    if n is None or n == 0:
        return None
    return codigos[n - 1]


def rotulo(modulos, codigo):
    """Texto amigavel 'Nome (CODIGO)' usado nas saidas."""
    return "%s (%s)" % (modulos[codigo]["nome"], codigo)


# ===========================================================================
# 7. OPCOES DO MENU
# ===========================================================================
def op_visualizar(modulos, grafo, arestas):
    """Opcao 1: visao geral da rede (modulos, conexoes e matriz de adjacencia)."""
    cabecalho("VISUALIZACAO DA REDE DA COLONIA AURORA SIGER")

    # ---- Tabela de modulos ----
    print("MODULOS (vertices do grafo):\n")
    # Larguras das colunas calculadas a partir dos dados, para a tabela ficar
    # alinhada mesmo com codigos longos (ex.: MOD-EN-001) e nomes extensos.
    larg_cod = max(len(c) for c in modulos)
    larg_nome = max(len(info["nome"]) for info in modulos.values())
    cabec = "  %-*s  %-*s %8s %4s %10s %-8s %-11s" % (
        larg_cod, "COD", larg_nome, "Nome",
        "Consumo", "Pri", "Capac.", "Comunic.", "Status")
    print(cabec)
    print("  " + "-" * (len(cabec) - 2))
    for codigo, info in modulos.items():
        print("  %-*s  %-*s %5d kW %4d %6d kWh %-8s %-11s" % (
            larg_cod, codigo, larg_nome, info["nome"], info["consumo"],
            info["prioridade"], info["capacidade"], info["comunicacao"],
            info["status"]))
    consumo_total = sum(info["consumo"] for info in modulos.values())
    print("  " + "-" * (len(cabec) - 2))
    print("  Consumo total atual da colonia: %d kW" % consumo_total)

    # ---- Lista de conexoes ----
    print("\nCONEXOES (arestas do grafo) - peso = distancia em metros:\n")
    for (u, v, peso) in arestas:
        print("   %-5s <--> %-5s : %4d m" % (u, v, peso))
    print("\n  Total de conexoes: %d" % len(arestas))

    # ---- Matriz de adjacencia ----
    codigos, matriz = construir_matriz(modulos, grafo)
    print("\nMATRIZ DE ADJACENCIA (distancia em metros; 0 = sem conexao direta):\n")
    larg = max(len(c) for c in codigos)        # largura de cada coluna (maior codigo)
    print("  " + " " * larg + "".join(" %*s" % (larg, c) for c in codigos))
    for i, c in enumerate(codigos):
        valores = "".join(" %*d" % (larg, matriz[i][j]) for j in range(len(codigos)))
        print("  %-*s" % (larg, c) + valores)

    print("\n  Observacao: o diagrama visual da rede esta no arquivo")
    print("  'rede_colonia.pdf', entregue junto com o sistema.")
    pausar()


def op_consultar(modulos, grafo):
    """Opcao 2: detalhes completos de um modulo escolhido."""
    cabecalho("CONSULTA DE MODULO")
    codigo = escolher_modulo(modulos)
    if codigo is None:
        return
    info = modulos[codigo]
    print()
    linha("-")
    print(" Modulo: %s" % rotulo(modulos, codigo))
    linha("-")
    print("  Consumo energetico .......: %d kW" % info["consumo"])
    print("  Prioridade operacional ...: %d (1=baixa, 5=vital)" % info["prioridade"])
    print("  Capacidade de armazenam. .: %d kWh" % info["capacidade"])
    print("  Necessidade de comunicacao: %s" % info["comunicacao"])
    print("  Status operacional .......: %s" % info["status"])
    print("  Posicao no mapa (x, y) ...: %s" % str(info["pos"]))
    # Conexoes diretas (grau do vertice)
    vizinhos = grafo[codigo]
    print("\n  Conexoes diretas (grau = %d):" % len(vizinhos))
    for v in sorted(vizinhos, key=lambda x: vizinhos[x]):
        print("     -> %-32s (%4d m)" % (rotulo(modulos, v), vizinhos[v]))
    pausar()


def op_caminho_minimo(modulos, grafo):
    """Opcao 3: rota otima de energia entre dois modulos (Dijkstra)."""
    cabecalho("CAMINHO MINIMO DE ENERGIA (ALGORITMO DE DIJKSTRA)")
    print("Defina a ORIGEM (normalmente os Geradores + Painéis Solares):")
    origem = escolher_modulo(modulos, prompt="")
    if origem is None:
        return
    print("\nDefina o DESTINO:")
    destino = escolher_modulo(modulos, prompt="")
    if destino is None:
        return
    if origem == destino:
        print("\n  Origem e destino sao o mesmo modulo. Distancia = 0 m.")
        pausar()
        return

    dist, anterior = dijkstra(grafo, origem)
    caminho = reconstruir_caminho(anterior, origem, destino)

    print()
    if not caminho:
        print("  Nao existe rota entre %s e %s." % (rotulo(modulos, origem),
                                                    rotulo(modulos, destino)))
        print("  Os modulos estao em partes desconectadas da rede.")
        pausar()
        return

    print("  Rota mais eficiente de %s ate %s:" % (rotulo(modulos, origem),
                                                   rotulo(modulos, destino)))
    print("\n     " + "  ->  ".join(caminho))
    # Detalha o custo de cada trecho
    print("\n  Trechos percorridos:")
    for i in range(len(caminho) - 1):
        a, b = caminho[i], caminho[i + 1]
        print("     %-5s -> %-5s : %4d m" % (a, b, grafo[a][b]))
    print("\n  Distancia total da rota: %d m" % dist[destino])
    pausar()


def op_explorar(modulos, grafo):
    """Opcao 4: explora a rede a partir de um modulo usando BFS e DFS."""
    cabecalho("EXPLORACAO DA REDE (BFS E DFS)")
    origem = escolher_modulo(modulos)
    if origem is None:
        return

    # BFS
    ordem_bfs, nivel, _ = bfs(grafo, origem)
    print("\n  >> BUSCA EM LARGURA (BFS) a partir de %s" % rotulo(modulos, origem))
    print("     Ordem de visita: " + " -> ".join(ordem_bfs))
    print("     Modulos por nivel (saltos a partir da origem):")
    max_nivel = max(nivel.values())
    for nv in range(max_nivel + 1):
        ndt = [c for c in ordem_bfs if nivel[c] == nv]
        print("        Nivel %d: %s" % (nv, ", ".join(ndt)))

    # DFS
    ordem_dfs, _ = dfs(grafo, origem)
    print("\n  >> BUSCA EM PROFUNDIDADE (DFS) a partir de %s" % rotulo(modulos, origem))
    print("     Ordem de visita: " + " -> ".join(ordem_dfs))

    # Alcance
    alcancaveis = set(ordem_bfs)
    inalcancaveis = [c for c in modulos if c not in alcancaveis]
    print("\n  Modulos alcancaveis a partir da origem: %d de %d" %
          (len(alcancaveis), len(modulos)))
    if inalcancaveis:
        print("  Modulos NAO alcancaveis: %s" % ", ".join(inalcancaveis))
    pausar()


def op_conexoes_criticas(modulos, grafo, arestas):
    """Opcao 5: identifica pontes e pontos de articulacao da rede."""
    cabecalho("CONEXOES CRITICAS (PONTES E PONTOS DE ARTICULACAO)")
    pontes = detectar_pontes(grafo, arestas)
    articulacoes = detectar_articulacoes(grafo)

    print("PONTES (conexoes cuja falha PARTE a rede):\n")
    if pontes:
        for (u, v, peso) in pontes:
            print("   %s <--> %s  (%d m)" % (rotulo(modulos, u), rotulo(modulos, v), peso))
        print("\n  -> Essas ligacoes precisam de redundancia (cabo reserva).")
    else:
        print("   Nenhuma. A rede e robusta: toda conexao tem rota alternativa.")

    print("\nPONTOS DE ARTICULACAO (modulos cuja falha isola partes da rede):\n")
    if articulacoes:
        for c in articulacoes:
            print("   - %s" % rotulo(modulos, c))
        print("\n  -> Esses modulos sao criticos e exigem maior atencao operacional.")
    else:
        print("   Nenhum.")
    pausar()


def op_eficiencia(modulos, grafo, arestas):
    """Opcao 6: metricas de eficiencia operacional da rede."""
    cabecalho("ANALISE DE EFICIENCIA OPERACIONAL DA REDE")
    n = len(modulos)
    m = len(arestas)

    # Grau de cada modulo
    graus = {c: len(grafo[c]) for c in modulos}
    grau_medio = sum(graus.values()) / n
    hub = max(graus, key=lambda c: graus[c])
    # Densidade: fracao das conexoes possiveis que realmente existem
    densidade = (2 * m) / (n * (n - 1))

    # Diametro e caminho medio (usando Dijkstra a partir de cada modulo)
    distancias = []
    diametro = 0
    par_diametro = (None, None)
    for origem in modulos:
        dist, _ = dijkstra(grafo, origem)
        for destino, d in dist.items():
            if origem != destino and d != INF:
                distancias.append(d)
                if d > diametro:
                    diametro = d
                    par_diametro = (origem, destino)
    caminho_medio = sum(distancias) / len(distancias) if distancias else 0

    pontes = detectar_pontes(grafo, arestas)
    articulacoes = detectar_articulacoes(grafo)
    consumo_total = sum(info["consumo"] for info in modulos.values())

    print("  Modulos (vertices) ............: %d" % n)
    print("  Conexoes (arestas) ............: %d" % m)
    print("  Rede totalmente conectada .....: %s" % ("Sim" if esta_conexo(grafo) else "Nao"))
    print("  Grau medio dos modulos ........: %.2f conexoes" % grau_medio)
    print("  Modulo mais conectado (hub) ...: %s, com %d conexoes" %
          (rotulo(modulos, hub), graus[hub]))
    print("  Densidade da rede .............: %.3f (0=esparsa, 1=totalmente ligada)" % densidade)
    print("  Caminho medio entre modulos ...: %.1f m" % caminho_medio)
    print("  Diametro da rede (maior rota) .: %d m  (%s -> %s)" %
          (diametro, par_diametro[0], par_diametro[1]))
    print("  Conexoes criticas (pontes) ....: %d" % len(pontes))
    print("  Pontos de articulacao .........: %d" % len(articulacoes))
    print("  Consumo energetico total ......: %d kW" % consumo_total)

    # Interpretacao automatica
    print("\n  INTERPRETACAO:")
    if pontes or articulacoes:
        print("   - A rede possui pontos frageis; ha trechos sem rota alternativa.")
        print("   - Recomenda-se redundancia nas pontes e backup nos pontos de articulacao.")
    else:
        print("   - A rede e resiliente: nao ha pontos unicos de falha.")
    if densidade < 0.5:
        print("   - Densidade baixa: estrutura economica, mas exige bom planejamento de rotas.")
    pausar()


def op_modelagem(modulos):
    """Opcao 7: modelagem matematica do consumo + calculo diferencial + otimizacao."""
    cabecalho("MODELAGEM MATEMATICA E OTIMIZACAO DA EXPANSAO")
    A = (MODELO_K - MODELO_E0) / MODELO_E0
    consumo_atual = sum(info["consumo"] for info in modulos.values())

    print("Fenomeno modelado: crescimento do consumo energetico da colonia.")
    print("Modelo logistico (crescimento limitado pela capacidade de geracao):\n")
    print("     E(t) = K / (1 + A * e^(-r*t))        A = (K - E0)/E0")
    print("     dE/dt = r * E(t) * (1 - E(t)/K)      (taxa de variacao)\n")
    print("  Parametros adotados:")
    print("     K  (capacidade maxima sustentavel) = %.0f kW" % MODELO_K)
    print("     E0 (demanda inicial) ............. = %.0f kW" % MODELO_E0)
    print("     r  (taxa de crescimento) ......... = %.2f por mes" % MODELO_R)
    print("     A  (constante inicial) ........... = %.2f" % A)
    print("     Consumo total atual da colonia ... = %d kW (%.0f%% de K)" %
          (consumo_atual, 100.0 * consumo_atual / MODELO_K))

    # Ponto de inflexao (derivada maxima) -> aplicacao de calculo diferencial
    t_estrela = tempo_inflexao()
    taxa_max = MODELO_R * MODELO_K / 4.0   # valor maximo de dE/dt (em E = K/2)
    t90 = tempo_para_fracao(0.90)
    print("\n  ANALISE COM CALCULO DIFERENCIAL:")
    print("   - Ponto de inflexao em t* = ln(A)/r = %.1f meses (quando E = K/2 = %.0f kW)." %
          (t_estrela, MODELO_K / 2))
    print("   - Nesse instante a demanda cresce mais rapido: dE/dt maximo = %.1f kW/mes." % taxa_max)
    print("   - A demanda atinge 90%% de K (%.0f kW) em cerca de %.1f meses." %
          (0.90 * MODELO_K, t90))

    # Verificacao numerica do ponto de inflexao (otimizacao computacional simples)
    melhor_t, melhor_taxa = 0.0, 0.0
    t = 0.0
    while t <= 60.0:
        taxa = derivada_E(t)
        if taxa > melhor_taxa:
            melhor_taxa = taxa
            melhor_t = t
        t += 0.1
    print("\n   - Verificacao numerica (varredura de t): taxa maxima ~ %.1f kW/mes em t ~ %.1f meses."
          % (melhor_taxa, melhor_t))

    print("\n  ANALISE QUALITATIVA:")
    print("   - A curva tem formato de 'S': cresce rapido no inicio e desacelera")
    print("     ao se aproximar de K. Isso reflete o limite fisico de geracao da base.")
    print("   - O instante t* e um ALERTA: a partir dele, a rede entra na faixa de")
    print("     maior pressao. A geracao deve ser ampliada ANTES desse ponto.")

    # Permite avaliar a curva em um instante escolhido
    print()
    t_user = ler_float("  Avaliar a demanda em qual tempo t (meses)? [ENTER p/ pular]: ",
                       0.0, 1000.0, -1.0)
    if t_user >= 0:
        print("     E(%.1f) = %.1f kW   |   dE/dt(%.1f) = %.2f kW/mes" %
              (t_user, consumo_E(t_user), t_user, derivada_E(t_user)))

    print("\n  RELACAO COM A COLONIA / OTIMIZACAO:")
    print("   - Planejar a expansao da geracao antes de t* evita apagoes.")
    print("   - Reduzir o consumo (eficiencia energetica) diminui E0 e r, adiando a saturacao")
    print("     e prolongando a vida util da infraestrutura atual.")
    pausar()


# --- Submenu de simulacoes -------------------------------------------------
def sim_distribuicao(modulos, grafo):
    """Simulacao A: distribuicao de energia com perdas pela rota otima."""
    cabecalho("SIMULACAO: DISTRIBUICAO DE ENERGIA COM PERDAS")
    print("Origem da energia:")
    origem = escolher_modulo(modulos, prompt="")
    if origem is None:
        return
    print("\nModulo de destino:")
    destino = escolher_modulo(modulos, prompt="")
    if destino is None:
        return
    if origem == destino:
        print("\n  Origem e destino iguais; nada a transmitir.")
        pausar()
        return

    potencia = ler_float("\nQuanta energia enviar, em kW? [ENTER = 100]: ", 0.1, 1e9, 100.0)

    dist, anterior = dijkstra(grafo, origem)
    caminho = reconstruir_caminho(anterior, origem, destino)
    if not caminho:
        print("\n  Sem rota disponivel entre os modulos: transmissao impossivel.")
        pausar()
        return

    # Perda multiplicativa por trecho: eficiencia = produto de (1 - coef*distancia)
    eficiencia = 1.0
    distancia_total = 0
    print("\n  Rota: " + "  ->  ".join(caminho))
    print("\n  Perda por trecho (coef. = %.4f por metro):" % COEF_PERDA)
    for i in range(len(caminho) - 1):
        a, b = caminho[i], caminho[i + 1]
        d = grafo[a][b]
        distancia_total += d
        ef_trecho = 1.0 - COEF_PERDA * d
        eficiencia *= ef_trecho
        print("     %-5s -> %-5s : %4d m | eficiencia do trecho = %5.1f%%" %
              (a, b, d, ef_trecho * 100))

    entregue = potencia * eficiencia
    perdido = potencia - entregue
    print("\n  Distancia total .......: %d m" % distancia_total)
    print("  Eficiencia da rota ....: %.1f%%" % (eficiencia * 100))
    print("  Energia enviada .......: %.1f kW" % potencia)
    print("  Energia ENTREGUE ......: %.1f kW" % entregue)
    print("  Energia PERDIDA .......: %.1f kW (%.1f%%)" %
          (perdido, 100.0 * perdido / potencia))
    print("\n  -> Como a perda cresce com a distancia, a rota do Dijkstra")
    print("     (mais curta) e tambem a de MENOR desperdicio de energia.")
    pausar()


def sim_blackout(modulos):
    """Simulacao B: priorizacao de modulos em falha de geracao (otimizacao)."""
    cabecalho("SIMULACAO: FALHA DE GERACAO (PRIORIZACAO DE CARGAS)")
    consumo_total = sum(info["consumo"] for info in modulos.values())
    print("Consumo total da colonia em operacao normal: %d kW." % consumo_total)
    print("Em uma falha de geracao, so ha energia limitada (reserva das baterias).")
    potencia = ler_float("\nEnergia disponivel na reserva, em kW? [ENTER = 250]: ",
                         0.0, 1e9, 250.0)

    print("Politica de priorizacao: atende primeiro o MAXIMO de modulos de")
    print("prioridade 5 (suporte a vida); com a energia restante, os de")
    print("prioridade 4; e assim por diante.")

    # OTIMIZACAO POR FORCA BRUTA: testa todos os subconjuntos de modulos e
    # escolhe o melhor sem ultrapassar a energia disponivel (variacao do
    # problema da mochila). Com 8 modulos sao apenas 256 casos.
    #
    # O criterio de escolha e LEXICOGRAFICO por nivel de prioridade: vence o
    # subconjunto que atende mais modulos de prioridade 5; havendo empate, o
    # que atende mais de prioridade 4; e assim sucessivamente. Isso garante
    # que sistemas criticos nunca sejam sacrificados por modulos menos
    # importantes (mesmo que a "soma de pontos" pudesse ser maior). Em ultimo
    # criterio de desempate, escolhe-se a opcao de menor consumo.
    codigos = list(modulos.keys())
    n = len(codigos)
    melhor = None  # (chave, mascara, consumo, prioridade_total)
    for mascara in range(1 << n):
        consumo = 0
        prioridade = 0
        por_nivel = [0, 0, 0, 0, 0]   # indice 0 -> prioridade 5 ... indice 4 -> prioridade 1
        for i in range(n):
            if mascara & (1 << i):
                modulo = modulos[codigos[i]]
                consumo += modulo["consumo"]
                prioridade += modulo["prioridade"]
                por_nivel[5 - modulo["prioridade"]] += 1
        if consumo <= potencia:
            chave = (por_nivel[0], por_nivel[1], por_nivel[2],
                     por_nivel[3], por_nivel[4], -consumo)
            if melhor is None or chave > melhor[0]:
                melhor = (chave, mascara, consumo, prioridade)

    _, mascara, consumo, prioridade = melhor
    ligados = [codigos[i] for i in range(n) if mascara & (1 << i)]
    desligados = [codigos[i] for i in range(n) if not (mascara & (1 << i))]

    print("\n  CENARIO OTIMO (maior prioridade mantida dentro da energia disponivel):\n")
    print("  MODULOS MANTIDOS LIGADOS:")
    if ligados:
        for c in sorted(ligados, key=lambda x: -modulos[x]["prioridade"]):
            print("     [ON ] %-32s pri=%d  %3d kW" %
                  (rotulo(modulos, c), modulos[c]["prioridade"], modulos[c]["consumo"]))
    else:
        print("     (nenhum - energia insuficiente ate para o menor modulo)")
    print("\n  MODULOS DESLIGADOS (corte de carga):")
    if desligados:
        for c in sorted(desligados, key=lambda x: -modulos[x]["prioridade"]):
            print("     [OFF] %-32s pri=%d  %3d kW" %
                  (rotulo(modulos, c), modulos[c]["prioridade"], modulos[c]["consumo"]))
    else:
        print("     (nenhum - a reserva atende toda a colonia)")

    print("\n  Energia disponivel ....: %.1f kW" % potencia)
    print("  Energia utilizada .....: %d kW" % consumo)
    print("  Prioridade preservada .: %d pontos" % prioridade)
    print("\n  -> A otimizacao garante que os sistemas de suporte a vida")
    print("     (prioridade 5) sejam preservados antes dos demais.")
    pausar()


def sim_falha_conexao(modulos, grafo, arestas):
    """Simulacao C: impacto da falha de uma conexao na rede."""
    cabecalho("SIMULACAO: FALHA DE UMA CONEXAO")
    print("Conexoes disponiveis:\n")
    for i, (u, v, peso) in enumerate(arestas, 1):
        print("   %2d. %-5s <--> %-5s (%d m)" % (i, u, v, peso))
    escolha = ler_inteiro("\nQual conexao falhou? (0 para cancelar): ", 0, len(arestas))
    if escolha is None or escolha == 0:
        return
    u, v, peso = arestas[escolha - 1]

    comp_antes = contar_componentes(grafo)
    comp_depois = contar_componentes(grafo, aresta_excluida={u, v})

    print("\n  Conexao afetada: %s <--> %s" % (rotulo(modulos, u), rotulo(modulos, v)))
    if comp_depois > comp_antes:
        print("\n  *** CONEXAO CRITICA (PONTE) ***")
        print("  A rede foi PARTIDA em %d blocos isolados." % comp_depois)
        # Descobre quais modulos ficaram isolados do hub de energia (MOD-EN-001)
        referencia = "MOD-EN-001" if "MOD-EN-001" in grafo else next(iter(grafo))
        ordem, _, _ = bfs(_grafo_sem_aresta(grafo, u, v), referencia)
        alcancaveis = set(ordem)
        isolados = [c for c in modulos if c not in alcancaveis]
        print("  Modulos que perderam ligacao com %s:" % rotulo(modulos, referencia))
        for c in isolados:
            print("     - %s" % rotulo(modulos, c))
    else:
        print("\n  A rede CONTINUA conectada: existe rota alternativa.")
        # Mostra a nova rota entre u e v sem usar a conexao que falhou
        g2 = _grafo_sem_aresta(grafo, u, v)
        dist, anterior = dijkstra(g2, u)
        caminho = reconstruir_caminho(anterior, u, v)
        if caminho:
            print("  Nova rota de %s ate %s: %s" % (u, v, "  ->  ".join(caminho)))
            print("  Distancia da rota alternativa: %d m (antes: %d m)" % (dist[v], peso))
    pausar()


def _grafo_sem_aresta(grafo, u, v):
    """Cria uma copia do grafo sem a conexao u-v (usada nas simulacoes)."""
    novo = {c: dict(viz) for c, viz in grafo.items()}
    novo[u].pop(v, None)
    novo[v].pop(u, None)
    return novo


def op_simulacoes(modulos, grafo, arestas):
    """Opcao 8: submenu de simulacoes operacionais."""
    while True:
        cabecalho("SIMULACOES OPERACIONAIS DA INFRAESTRUTURA")
        print("  1. Distribuicao de energia com perdas (rota otima)")
        print("  2. Falha de geracao: priorizacao com energia limitada")
        print("  3. Falha de uma conexao: impacto na rede")
        print("  0. Voltar ao menu principal")
        escolha = ler_inteiro("\nOpcao: ", 0, 3)
        if escolha is None or escolha == 0:
            return
        if escolha == 1:
            sim_distribuicao(modulos, grafo)
        elif escolha == 2:
            sim_blackout(modulos)
        elif escolha == 3:
            sim_falha_conexao(modulos, grafo, arestas)


# ===========================================================================
# 8. PROGRAMA PRINCIPAL (menu)
# ===========================================================================
def menu_principal():
    print()
    linha()
    print("   S I G I C  -  Gerenciamento da Infraestrutura da Colonia")
    print("   Aurora Siger  |  Fase 4 - Energia para sobreviver")
    linha()
    print("   1. Visualizar a rede da colonia")
    print("   2. Consultar um modulo")
    print("   3. Caminho minimo de energia (Dijkstra)")
    print("   4. Explorar a rede (BFS e DFS)")
    print("   5. Conexoes criticas (pontes e articulacoes)")
    print("   6. Analise de eficiencia operacional")
    print("   7. Modelagem matematica e otimizacao")
    print("   8. Simulacoes operacionais")
    print("   0. Sair")
    linha()


def main():
    # Carrega os dados e prepara as estruturas do grafo uma unica vez.
    modulos, arestas = carregar_dados()
    grafo = construir_grafo(modulos, arestas)

    while True:
        menu_principal()
        escolha = ler_inteiro("Escolha uma opcao: ", 0, 8)
        if escolha is None or escolha == 0:
            print("\nEncerrando o SIGIC. Ate logo!\n")
            break
        try:
            if escolha == 1:
                op_visualizar(modulos, grafo, arestas)
            elif escolha == 2:
                op_consultar(modulos, grafo)
            elif escolha == 3:
                op_caminho_minimo(modulos, grafo)
            elif escolha == 4:
                op_explorar(modulos, grafo)
            elif escolha == 5:
                op_conexoes_criticas(modulos, grafo, arestas)
            elif escolha == 6:
                op_eficiencia(modulos, grafo, arestas)
            elif escolha == 7:
                op_modelagem(modulos)
            elif escolha == 8:
                op_simulacoes(modulos, grafo, arestas)
        except Exception as erro:
            # Protege o menu contra erros inesperados (robustez "sem erros").
            print("\n  [erro] Ocorreu um problema ao executar a opcao: %s" % erro)
            pausar()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExecucao interrompida pelo usuario. Ate logo!\n")
 
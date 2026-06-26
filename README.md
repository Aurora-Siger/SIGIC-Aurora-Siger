# SIGIC — Sistema Inteligente de Gerenciamento da Infraestrutura da Colônia

Sistema de gestão e análise da rede energética da Colônia Aurora Siger — Fase 4: Energia para Sobreviver.

O SIGIC simula a estrutura da infraestrutura da colônia, constrói um grafo de módulos conectados por cabos e permite estudar rotas de energia, pontos críticos da rede, modelagem matemática do consumo e cenários operacionais.

---

## Sobre o projeto

Trabalho desenvolvido para a Fase 4 da missão Aurora Siger, com foco na infraestrutura energética e na operação sustentável da colônia marciana.

O sistema utiliza:

- representação de rede por grafos não direcionados e ponderados
- algoritmos de busca e otimização: BFS, DFS e Dijkstra
- análise de conectividade: componentes, pontes e pontos de articulação
- modelagem matemática do consumo de energia com crescimento logístico
- simulações operacionais de distribuição de energia, falhas e priorização de cargas

---

## Estrutura do projeto

```
SIGIC-Aurora-Siger/
├── README.md
├── codigo_fonte.py          # Lógica principal do SIGIC e interface de menu
├── dados_colonia.json       # Base de dados da infraestrutura da colônia
└── arquivos_auxiliares/     # Recursos auxiliares usados pelo sistema
```

---

## Componentes da Colônia

A base de dados define os módulos da colônia e suas conexões.

| Código      | Módulo                                         | Consumo (kW) | Prioridade | Status |
|-------------|------------------------------------------------|--------------|------------|--------|
| MOD-EN-001  | Geradores + Painéis Solares                    | 15           | 5          | ativo  |
| MOD-SV-002  | Sistemas de suporte a vida                     | 40           | 5          | ativo  |
| MOD-HB-003  | Módulos infláveis BEAM (Habitação)             | 120          | 5          | ativo  |
| MOD-SC-004  | Sensores científicos                           | 90           | 4          | ativo  |
| MOD-MN-005  | Mineração e Produção ISRU                      | 50           | 4          | ativo  |
| MOD-LG-006  | Logística e Suprimentos                        | 60           | 5          | ativo  |
| MOD-AG-007  | Agricultura                                    | 50           | 4          | ativo  |
| MOD-CM-008  | Comunicação                                    | 50           | 4          | ativo  |

---

## Rede e topologia

O grafo é construído a partir das conexões de cabos entre módulos, onde cada aresta representa uma distância em metros.

Exemplos de conexões:

- `MOD-EN-001` ↔ `MOD-SV-002` : 75 m
- `MOD-SV-002` ↔ `MOD-HB-003` : 80 m
- `MOD-HB-003` ↔ `MOD-MN-005` : 80 m
- `MOD-AG-007` ↔ `MOD-MN-005` : 100 m
- `MOD-LG-006` ↔ `MOD-SC-004` : 75 m
- `MOD-EN-001` ↔ `MOD-AG-007` : 120 m

---

## Funcionalidades principais

### 1. Visualização da rede

- lista de módulos e atributos
- conexões e pesos de arestas
- matriz de adjacência da infraestrutura

### 2. Consulta de módulo

- detalhes completos de cada módulo
- grau de conexão e vizinhança direta

### 3. Caminho mínimo de energia

- Dijkstra para encontrar rota de menor custo entre dois módulos
- cálculo de distância total e trechos percorridos

### 4. Exploração da rede

- BFS para visitar a rede por níveis
- DFS para explorar rotas em profundidade

### 5. Conexões críticas

- detecção de pontes que quebram a rede se falharem
- identificação de pontos de articulação que isolam módulos

### 6. Eficiência operacional

- grau médio do grafo
- distância média e diâmetro da rede
- densidade da rede e robustez

### 7. Modelagem matemática

- crescimento do consumo energético com modelo logístico
- cálculo do ponto de inflexão usando derivada
- análise de expansão e alerta para saturação da geração

### 8. Simulações operacionais

- distribuição de energia com perdas de transmissão
- priorização de cargas durante blackout
- falha de conexão e impacto na conectividade da rede

---

## Base de dados do projeto

O arquivo `dados_colonia.json` é a fonte única de dados do sistema e define:

- módulos com consumo, prioridade, capacidade e comunicação
- conexões entre módulos com distância em metros
- topologia da rede da colônia

---

## Como executar

Requisitos: Python 3.x

Execute:

```bash
python codigo_fonte.py
```

O sistema inicia um menu interativo no terminal onde é possível selecionar as análises e simulações desejadas.

---

## Objetivo educacional

O SIGIC foi desenvolvido para:

- demonstrar representação de redes e grafos aplicados à infraestrutura energética
- comparar algoritmos clássicos de busca e otimização em uma base realista
- avaliar a resiliência de uma colônia marciana em cenários de falha
- aplicar modelagem matemática e conceitos de sustentabilidade energética

---

## Referências

- Colônia Aurora Siger — Fase 4: Energia para Sobreviver
- Grafos, busca em largura, busca em profundidade e Dijkstra
- Modelagem logística de consumo energético
- Simulações de priorização de cargas em blackout

---

## Contato

Projeto local desenvolvido como parte da disciplina FIAP.

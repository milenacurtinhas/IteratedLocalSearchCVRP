# ILS-RVND para o CVRP

**Alunos:** Milena Curtinhas Santos e Pedro Sodré Malini

Implementação em Python da meta-heurística **Iterated Local Search (ILS)** para o
**Problema de Roteamento de Veículos Capacitados (CVRP)**, desenvolvida para a
Atividade T2 da disciplina de Meta-heurísticas.

O algoritmo segue o [ILS-RVND de Subramanian, Uchoa e Ochi (2013)](https://doi.org/10.1016/j.cor.2013.01.013), sem a fase de Set Partitioning e com uma única cadeia ILS.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `leitor.py` | Lê as instâncias (`.vrp`) e soluções (`.sol`) da CVRPLIB |
| `solucao.py` | Função objetivo (`avaliar`) e verificação de viabilidade (`eh_viavel`) |
| `ils.py` | O algoritmo: solução inicial, vizinhanças, RVND, perturbação e laço do ILS |
| `experimentos.py` | Calibração dos parâmetros e testes finais (gera as tabelas em CSV) |
| `plotar.py` | Desenha uma solução (a partir de um `.sol` ou rodando o ILS) |

## Instâncias

Conjuntos A, B (Augerat et al.) e F (Fisher) da
[CVRPLIB](https://galgos.inf.puc-rio.br/cvrplib/). Extraia os arquivos `.7z` em
pastas ao lado do código:

```
.
├── leitor.py
├── solucao.py
├── ils.py
├── experimentos.py
├── plotar.py
├── A/             (A-n32-k5.vrp, A-n33-k5.vrp, ...)
├── A-solutions/   (A-n32-k5.sol, A-n33-k5.sol, ...)
├── B/             (B-n31-k5.vrp, ...)
├── B-solutions/   (B-n31-k5.sol, ...)
├── F/             (F-n45-k4.vrp, F-n72-k4.vrp, F-n135-k7.vrp)
└── F-solutions/   (F-n45-k4.sol, F-n72-k4.sol, F-n135-k7.sol)
```

O valor ótimo de cada instância é lido do campo `COMMENT` do próprio `.vrp`.

## O algoritmo

```
1  s  <- SolucaoInicial()       # inserção mais barata viável
2  s  <- RVND(s)
3  s* <- s
4  enquanto iter < MaxIter e semMelhora < MaxSemMelhora:
5      s' <- RVND(Perturbacao(s*, k ~ U{1..kmax}))
6      se f(s') < f(s*): s* <- s', semMelhora <- 0
7      senão:            semMelhora <- semMelhora + 1
8  retorne s*
```

- **Representação:** lista de rotas; cada rota é a lista de clientes na ordem de
  visita, com o depósito (0) implícito no início e no fim. Ex.: `[[3, 12, 5], [8, 2, 19]]`.
- **Solução inicial:** abre k rotas com clientes-semente sorteados e insere os demais,
  do maior para o menor demanda, na posição mais barata que respeite a capacidade.
- **Busca local (RVND):** vizinhanças entre rotas Shift(1,0), Shift(2,0), Swap(1,1),
  Swap(2,1), Swap(2,2) e Cross, escolhidas em ordem aleatória, com melhor melhora.
  Após cada melhora, as rotas alteradas passam pelas vizinhanças intra-rota
  (2-opt, Reinserção, Or-opt-2, Or-opt-3, Exchange).
- **Perturbação:** k movimentos aleatórios Multiple-Swap(1,1) ou Multiple-Shift(1,1).
- **Aceitação:** só aceita soluções melhores (critério *Better*).
- **Parada:** MaxIter iterações (padrão: 10 × MaxSemMelhora) ou MaxSemMelhora
  iterações seguidas sem melhora, o que vier primeiro.

Só são geradas soluções viáveis: movimentos que excedem a capacidade Q são
descartados antes de serem avaliados.

## Como usar

### Conferir a leitura das instâncias

```
python leitor.py A A-solutions
python leitor.py B B-solutions
python leitor.py F F-solutions
```

Para cada instância com `.sol`, mostra `OK` se o custo recalculado bate com o publicado.

### Rodar o algoritmo em uma instância

```
python ils.py A/A-n32-k5.vrp 1
```

O último número é a semente. Mostra cada melhora, o gap em relação ao ótimo e as rotas finais.

### Desenhar uma solução
 
```
python plotar.py A/A-n32-k5.vrp solucoes/A-n32-k5_semente1.sol   # solução salva (não roda o ILS)
python plotar.py A/A-n32-k5.vrp A-solutions/A-n32-k5.sol         # solução ótima da CVRPLIB
python plotar.py A/A-n32-k5.vrp 1                                # roda o ILS, salva o .sol e desenha
```
 
Salva a figura em `solucoes/` (ex.: `solucoes/A-n32-k5_semente1.png`), com uma cor por
rota, o depósito destacado e a carga de cada rota. Requer `matplotlib`, usado só para desenhar.
 
Cada execução do `experimentos.py` é gravada no CSV assim que termina. Se o
programa for interrompido, rode o mesmo comando de novo: o que já foi feito é pulado.

### Calibrar os parâmetros

```
python experimentos.py calibrar A/A-n32-k5.vrp A/A-n80-k10.vrp B/B-n78-k10.vrp
```
 
Roda as 27 combinações de parâmetros (3 níveis × 3 parâmetros) em cada instância,
com até 180 s por execução e a mesma semente. Pode ser rodado uma instância por vez; os resultados se acumulam em `calibracao.csv`. Para ver a análise a qualquer momento:
 
```
python experimentos.py analisar
```
 
Mostra o fMH de cada combinação em cada instância, o gap e o tempo médios, o efeito de cada parâmetro (média por nível) e a melhor combinação.

### Testes finais

```
python experimentos.py final A B F --kmax 5 --sem-melhora 3 --p-swap 0.5
```

Roda 5 execuções (sementes 1 a 5) por instância com os parâmetros escolhidos. Pode ser
rodado uma pasta por vez. Gera:
 
- `tabela_final.csv`: Instância, fSol_Ótima, fMH (Min5 e Média5), Tempo (Min5 e Média5), gapMin e gapMédia, com todas as instâncias já executadas
- `execucoes.csv`: resultado de cada execução
- `historicos.json`: melhor valor por iteração de cada execução (chave `instância|semente`), para o gráfico de convergência; a coluna `Semente_Min5` da tabela indica a melhor execução
- `solucoes/<instância>_semente<s>.sol`: a solução de cada execução

Se mudar os parâmetros, as execuções antigas continuam no `execucoes.csv`, mas a tabelausa só as feitas com os parâmetros informados no comando.


### Opções do `experimentos.py`

| Opção | Significado | Padrão |
| --- | --- | --- |
| `--kmax` | Força máxima da perturbação (nº de movimentos) | 5 |
| `--sem-melhora` | Iterações sem melhora até parar, como fator de n (3 = 3n) | 3 |
| `--p-swap` | Probabilidade de usar Multiple-Swap em vez de Multiple-Shift | 0.5 |
| `--tempo` | Limite de tempo por execução, em segundos | 180 na calibração, nenhum nos testes finais |

Níveis usados na calibração: kmax ∈ {2, 5, 10}, MaxSemMelhora ∈ {n, 3n, 6n},
p_swap ∈ {0,25; 0,5; 0,75}. Para mudar, edite as listas `NIVEIS_*` no início de
`experimentos.py`.

## Referências

- Subramanian, A.; Uchoa, E.; Ochi, L. S. A hybrid algorithm for a class of vehicle
  routing problems. *Computers & Operations Research*, 40(10), 2519–2531, 2013.
- Lourenço, H. R.; Martin, O. C.; Stützle, T. Iterated Local Search. In: *Handbook of
  Metaheuristics*, Kluwer, 321–353, 2003.
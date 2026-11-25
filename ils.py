"""
ils.py - ILS-RVND para o CVRP.

    1  s  <- SolucaoInicial()
    2  s  <- RVND(s)
    3  s* <- s
    4  enquanto iter < MaxIter e semMelhora < MaxSemMelhora:
    5      s' <- RVND(Perturbacao(s*, k ~ U{1..kmax}))
    6      se f(s') < f(s*): s* <- s', semMelhora <- 0
    7      senão:            semMelhora <- semMelhora + 1
    8  retorne s*

Uso:
    python ils.py caminho/A-n32-k5.vrp [semente]
"""

import random
import sys
import time

from leitor import ler_instancia
from solucao import avaliar, carga_rota, custo_rota, eh_viavel, problemas, salvar_solucao


# 1. Solução inicial: inserção mais barata viável

def solucao_inicial(inst, rng, tentativas=50):
    """Abre k rotas com clientes-semente sorteados e insere os demais, do maior
    para o menor demanda, na posição mais barata que respeite a capacidade.

    Se em `tentativas` sorteios algum cliente não couber, a última tentativa
    abre rotas extras (e avisa)."""
    d, q, Q = inst["dist"], inst["q"], inst["Q"]
    k = inst["k"] or 1
    clientes = list(range(1, inst["n"] + 1))

    for t in range(tentativas):
        ultima = t == tentativas - 1
        rng.shuffle(clientes)
        rotas = [[c] for c in clientes[:k]]
        cargas = [q[c] for c in clientes[:k]]
        resto = sorted(clientes[k:], key=lambda c: -q[c]) # maiores primeiro
        coube_tudo = True

        for c in resto:
            melhor = None # (custo, rota, posição)
            for r, rota in enumerate(rotas):
                if cargas[r] + q[c] > Q:
                    continue
                p = [0] + rota + [0]
                for i in range(len(p) - 1):
                    custo = d[p[i]][c] + d[c][p[i + 1]] - d[p[i]][p[i + 1]]
                    if melhor is None or custo < melhor[0]:
                        melhor = (custo, r, i)
            if melhor is None:
                if not ultima:
                    coube_tudo = False
                    break
                rotas.append([c]) # último recurso: rota nova
                cargas.append(q[c])
                continue
            _, r, i = melhor
            rotas[r].insert(i, c)
            cargas[r] += q[c]

        if coube_tudo:
            if len(rotas) > k:
                print(f"Aviso: solução inicial com {len(rotas)} rotas (k = {k})")
            return rotas


# 2. Vizinhanças entre rotas (avaliadas pela variação de custo, delta)
#
# Shift(a,0): move a clientes consecutivos de uma rota para outra.
# Swap(a,b):  troca a clientes consecutivos de uma rota com b de outra.
# Cross:      corta duas rotas e troca as caudas (2-opt*).

TAMANHOS = {"Shift(1,0)": (1, 0), "Shift(2,0)": (2, 0), "Swap(1,1)": (1, 1),
            "Swap(2,1)": (2, 1), "Swap(2,2)": (2, 2)}
VIZINHANCAS = list(TAMANHOS) + ["Cross"]


def melhor_troca(rotas, cargas, inst, a, b):
    """Melhor movimento Shift(a,0) (b = 0) ou Swap(a,b) viável e de melhora.
    Devolve (delta, (r1, i, r2, j)) ou (0, None)."""
    d, q, Q = inst["dist"], inst["q"], inst["Q"]
    melhor_delta, melhor_mov = 0, None

    for r1 in range(len(rotas)):
        p1 = [0] + rotas[r1] + [0]
        for r2 in range(len(rotas)):
            if r1 == r2 or (a == b and r2 < r1): # Swap(1,1) e (2,2) são simétricos
                continue
            p2 = [0] + rotas[r2] + [0]

            for i in range(1, len(p1) - a): # segmento p1[i : i+a]
                s1 = p1[i:i + a]
                q1 = sum(q[c] for c in s1)
                ant1, prox1 = p1[i - 1], p1[i + a]
                sai1 = d[ant1][s1[0]] + d[s1[-1]][prox1]

                for j in range(1, len(p2) - b): # segmento p2[j : j+b] (vazio se b = 0)
                    s2 = p2[j:j + b]
                    q2 = sum(q[c] for c in s2)
                    if cargas[r1] - q1 + q2 > Q or cargas[r2] - q2 + q1 > Q:
                        continue
                    ant2, prox2 = p2[j - 1], p2[j + b]
                    if b:
                        entra1 = d[ant1][s2[0]] + d[s2[-1]][prox1]
                        sai2 = d[ant2][s2[0]] + d[s2[-1]][prox2]
                    else:
                        entra1 = d[ant1][prox1]
                        sai2 = d[ant2][prox2]
                    entra2 = d[ant2][s1[0]] + d[s1[-1]][prox2]

                    delta = entra1 + entra2 - sai1 - sai2
                    if delta < melhor_delta:
                        melhor_delta, melhor_mov = delta, (r1, i, r2, j)

    return melhor_delta, melhor_mov


def melhor_cross(rotas, cargas, inst):
    """Melhor Cross viável: r1 = A|B, r2 = C|D  ->  A+D e C+B."""
    d, q, Q = inst["dist"], inst["q"], inst["Q"]
    melhor_delta, melhor_mov = 0, None

    for r1 in range(len(rotas)):
        p1 = [0] + rotas[r1] + [0]
        pre1 = [0] # pre1[i] = carga dos i primeiros
        for c in rotas[r1]:
            pre1.append(pre1[-1] + q[c])
        for r2 in range(r1 + 1, len(rotas)):
            p2 = [0] + rotas[r2] + [0]
            pre2 = [0]
            for c in rotas[r2]:
                pre2.append(pre2[-1] + q[c])

            for i in range(len(p1) - 1): # corte entre p1[i] e p1[i+1]
                for j in range(len(p2) - 1):
                    if pre1[i] + cargas[r2] - pre2[j] > Q:
                        continue
                    if pre2[j] + cargas[r1] - pre1[i] > Q:
                        continue
                    delta = (d[p1[i]][p2[j + 1]] + d[p2[j]][p1[i + 1]]
                             - d[p1[i]][p1[i + 1]] - d[p2[j]][p2[j + 1]])
                    if delta < melhor_delta:
                        melhor_delta, melhor_mov = delta, (r1, i, r2, j)

    return melhor_delta, melhor_mov


def melhor_movimento(nome, rotas, cargas, inst):
    if nome == "Cross":
        return melhor_cross(rotas, cargas, inst)
    a, b = TAMANHOS[nome]
    return melhor_troca(rotas, cargas, inst, a, b)


def aplicar(nome, rotas, mov):
    """Aplica o movimento em `rotas` (no lugar) e devolve as duas rotas alteradas."""
    r1, i, r2, j = mov
    if nome == "Cross":
        A, B = rotas[r1][:i], rotas[r1][i:]
        C, D = rotas[r2][:j], rotas[r2][j:]
        rotas[r1], rotas[r2] = A + D, C + B
    else:
        a, b = TAMANHOS[nome]
        s1 = rotas[r1][i - 1:i - 1 + a] # índice i em p1 = i-1 na rota
        s2 = rotas[r2][j - 1:j - 1 + b]
        rotas[r1][i - 1:i - 1 + a] = s2
        rotas[r2][j - 1:j - 1 + b] = s1
    return r1, r2


# 3. Vizinhanças dentro de uma rota (rotas são curtas: avalia recalculando)

VIZINHANCAS_INTRA = ["2-opt", "Reinsercao", "Or-opt-2", "Or-opt-3", "Exchange"]


def vizinhos_intra(nome, rota):
    """Gera todas as rotas vizinhas de `rota` na vizinhança `nome`."""
    n = len(rota)
    if nome == "2-opt": # inverte o trecho rota[i..j]
        for i in range(n - 1):
            for j in range(i + 1, n):
                yield rota[:i] + rota[i:j + 1][::-1] + rota[j + 1:]
    elif nome == "Exchange": # troca dois clientes de lugar
        for i in range(n - 1):
            for j in range(i + 1, n):
                nova = rota[:]
                nova[i], nova[j] = nova[j], nova[i]
                yield nova
    else: # move 1, 2 ou 3 consecutivos
        k = {"Reinsercao": 1, "Or-opt-2": 2, "Or-opt-3": 3}[nome]
        for i in range(n - k + 1):
            seg = rota[i:i + k]
            resto = rota[:i] + rota[i + k:]
            for p in range(len(resto) + 1):
                if p != i:
                    yield resto[:p] + seg + resto[p:]


def melhorar_rota(rota, inst, rng):
    """RVND intra-rota: melhor melhora em vizinhanças sorteadas até nenhuma melhorar."""
    custo = custo_rota(rota, inst)
    lista = VIZINHANCAS_INTRA[:]
    while lista:
        nome = rng.choice(lista)
        melhor = None
        for nova in vizinhos_intra(nome, rota):
            c = custo_rota(nova, inst)
            if c < custo and (melhor is None or c < melhor[0]):
                melhor = (c, nova)
        if melhor:
            custo, rota = melhor
            lista = VIZINHANCAS_INTRA[:]
        else:
            lista.remove(nome)
    return rota


# 4. Busca local: RVND (VND com ordem aleatória de vizinhanças)

def rvnd(rotas, inst, rng):
    rotas = [melhorar_rota(r, inst, rng) for r in rotas]
    cargas = [carga_rota(r, inst) for r in rotas]
    lista = VIZINHANCAS[:]

    while lista:
        nome = rng.choice(lista)
        delta, mov = melhor_movimento(nome, rotas, cargas, inst)
        if mov is None:
            lista.remove(nome) # sem melhora: descarta a vizinhança
            continue
        for r in aplicar(nome, rotas, mov): # melhora: reotimiza as rotas tocadas
            rotas[r] = melhorar_rota(rotas[r], inst, rng)
            cargas[r] = carga_rota(rotas[r], inst)
        lista = VIZINHANCAS[:] # e volta a usar todas

    return [r for r in rotas if r] # descarta rotas que ficaram vazias


# 5. Perturbação: Multiple-Swap(1,1) ou Multiple-Shift(1,1)

def perturbar(rotas, inst, rng, kmax, p_swap):
    """Aplica k movimentos aleatórios viáveis (k sorteado em 1..kmax).
    Swap(1,1): troca dois clientes de rotas diferentes de lugar.
    Shift(1,1): tira um cliente de cada rota e insere na outra, em posições sorteadas."""
    q, Q = inst["q"], inst["Q"]
    rotas = [r[:] for r in rotas]
    if len(rotas) < 2:
        return rotas
    cargas = [carga_rota(r, inst) for r in rotas]
    usar_swap = rng.random() < p_swap
    k = rng.randint(1, kmax)

    feitos = tentativas = 0
    while feitos < k and tentativas < 100 * k:
        tentativas += 1
        r1, r2 = rng.sample(range(len(rotas)), 2)
        if not rotas[r1] or not rotas[r2]:
            continue
        i, j = rng.randrange(len(rotas[r1])), rng.randrange(len(rotas[r2]))
        c1, c2 = rotas[r1][i], rotas[r2][j]
        if cargas[r1] - q[c1] + q[c2] > Q or cargas[r2] - q[c2] + q[c1] > Q:
            continue

        if usar_swap:
            rotas[r1][i], rotas[r2][j] = c2, c1
        else:
            rotas[r1].pop(i)
            rotas[r2].pop(j)
            rotas[r1].insert(rng.randint(0, len(rotas[r1])), c2)
            rotas[r2].insert(rng.randint(0, len(rotas[r2])), c1)
        cargas[r1] += q[c2] - q[c1]
        cargas[r2] += q[c1] - q[c2]
        feitos += 1

    return rotas


# 6. ILS

def ils(inst, max_iter=None, max_sem_melhora=None, kmax=5, p_swap=0.5,
        semente=None, tempo_limite=None, alvo=None, verbose=False):
    """Executa o ILS-RVND.

    Para quando atingir max_iter iterações ou max_sem_melhora iterações seguidas
    sem melhora (o que vier primeiro). Opcionais: tempo_limite em segundos
    (calibração) e alvo (TTT-plot: para ao atingir f <= alvo).

    Padrões: max_sem_melhora = 3n e max_iter = 10 * max_sem_melhora."""
    n = inst["n"]
    max_sem_melhora = max_sem_melhora or 3 * n
    max_iter = max_iter or 10 * max_sem_melhora
    rng = random.Random(semente)
    inicio = time.perf_counter()

    s = rvnd(solucao_inicial(inst, rng), inst, rng)
    melhor, f_melhor = s, avaliar(s, inst)
    t_melhor = time.perf_counter() - inicio
    historico = [f_melhor] # historico[it] = melhor valor após a iteração it
    historico_atual = [f_melhor] # historico_atual[it] = custo de s' na iteração it

    it = sem_melhora = 0
    while it < max_iter and sem_melhora < max_sem_melhora:
        if tempo_limite is not None and time.perf_counter() - inicio >= tempo_limite:
            break
        if alvo is not None and f_melhor <= alvo:
            break
        it += 1

        s = rvnd(perturbar(melhor, inst, rng, kmax, p_swap), inst, rng)
        f = avaliar(s, inst)
        historico_atual.append(f)
        if f < f_melhor: # aceitação "Better"
            melhor, f_melhor = s, f
            t_melhor = time.perf_counter() - inicio
            sem_melhora = 0
            if verbose:
                print(f"  iter {it:5d}  f = {f_melhor}  ({t_melhor:.1f} s)")
        else:
            sem_melhora += 1
        historico.append(f_melhor)

    return {
        "solucao": melhor,
        "custo": f_melhor,
        "tempo_melhor": t_melhor, # quando s* foi encontrada
        "tempo_total": time.perf_counter() - inicio,
        "iteracoes": it,
        "historico": historico,
        "historico_atual": historico_atual,
    }


if __name__ == "__main__":
    inst = ler_instancia(sys.argv[1])
    semente = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    print(f"{inst['nome']}: n={inst['n']}, Q={inst['Q']}, k={inst['k']}, ótimo={inst['otimo']}")

    res = ils(inst, semente=semente, verbose=True)

    s, f = res["solucao"], res["custo"]
    assert eh_viavel(s, inst), problemas(s, inst)
    print(f"\nMelhor custo: {f}  ({len(s)} rotas)")
    if inst["otimo"]:
        print(f"Gap: {100 * (f - inst['otimo']) / inst['otimo']:.2f}%")
    print(f"Tempo até a melhor: {res['tempo_melhor']:.1f} s | "
          f"total: {res['tempo_total']:.1f} s | iterações: {res['iteracoes']}")
    for idx, rota in enumerate(s, 1):
        print(f"Route #{idx}: {' '.join(map(str, rota))}")

    arq_sol = f"solucoes/{inst['nome']}_semente{semente}.sol"
    salvar_solucao(s, inst, arq_sol)
    print(f"Salvo: {arq_sol}")
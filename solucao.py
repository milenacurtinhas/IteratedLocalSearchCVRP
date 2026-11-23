"""
solucao.py - Avaliação e viabilidade de soluções do CVRP.

Representação: uma solução é uma lista de rotas; cada rota é a lista de
clientes na ordem de visita, com o depósito (0) implícito no início e no fim.

    s = [[3, 12, 5], [8, 2, 19], ...]   # rota 1: 0 -> 3 -> 12 -> 5 -> 0

`inst` é o dicionário devolvido por leitor.ler_instancia().
"""


def custo_rota(rota, inst):
    """Distância de 0 -> rota[0] -> ... -> rota[-1] -> 0 (rota vazia custa 0)."""
    if not rota:
        return 0
    d = inst["dist"]
    total = d[0][rota[0]] + d[rota[-1]][0]
    for a, b in zip(rota, rota[1:]):
        total += d[a][b]
    return total


def carga_rota(rota, inst):
    q = inst["q"]
    return sum(q[c] for c in rota)


def avaliar(solucao, inst):
    """Função objetivo: soma das distâncias de todas as rotas."""
    return sum(custo_rota(r, inst) for r in solucao)


def problemas(solucao, inst):
    """Lista os motivos de inviabilidade (lista vazia = solução viável)."""
    n, Q = inst["n"], inst["Q"]
    erros = []
    vistos = {}
    for idx, rota in enumerate(solucao, start=1):
        for c in rota:
            if not 1 <= c <= n:
                erros.append(f"rota {idx}: vértice inválido {c} (clientes são 1..{n})")
            elif c in vistos:
                erros.append(f"cliente {c} repetido (rotas {vistos[c]} e {idx})")
            else:
                vistos[c] = idx
        carga = carga_rota([c for c in rota if 1 <= c <= n], inst)
        if carga > Q:
            erros.append(f"rota {idx}: carga {carga} > Q = {Q}")
    faltando = [c for c in range(1, n + 1) if c not in vistos]
    if faltando:
        erros.append(f"{len(faltando)} cliente(s) não atendido(s): {faltando[:10]}"
                     + (" ..." if len(faltando) > 10 else ""))
    return erros


def eh_viavel(solucao, inst):
    """True se todo cliente aparece exatamente uma vez e nenhuma rota excede Q."""
    return not problemas(solucao, inst)
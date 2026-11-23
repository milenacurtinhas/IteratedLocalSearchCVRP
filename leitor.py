"""
Leitura das instâncias (.vrp) e soluções (.sol) da CVRPLIB.

Índices: 0 = depósito, 1..n = clientes (mesma numeração dos arquivos .sol).

Uso:
    python leitor.py pasta_instancias [pasta_solucoes]
"""

import glob
import math
import os
import re
import sys


def ler_instancia(caminho):
    """Lê um .vrp e devolve um dicionário com os dados da instância."""
    cab = {} # cabeçalho: NAME, CAPACITY, DIMENSION, ...
    coords = [] # (x, y) de cada vértice, na ordem do arquivo
    demandas = []
    secao = None

    for linha in open(caminho):
        linha = linha.strip()
        if not linha or linha == "EOF":
            continue
        if linha.endswith("SECTION"):
            secao = linha
        elif ":" in linha:
            chave, valor = linha.split(":", 1)
            cab[chave.strip()] = valor.strip()
        elif secao == "NODE_COORD_SECTION":
            _, x, y = linha.split()
            coords.append((float(x), float(y)))
        elif secao == "DEMAND_SECTION":
            demandas.append(int(linha.split()[1]))
        elif secao == "DEPOT_SECTION" and linha not in ("1", "-1"):
            raise ValueError("O leitor supõe que o depósito é o vértice 1")

    m = int(cab["DIMENSION"]) # vértices, incluindo o depósito

    if cab["EDGE_WEIGHT_TYPE"] != "EUC_2D":
        raise ValueError(f"Tipo de distância não suportado: {cab['EDGE_WEIGHT_TYPE']}")
    dist = [[round_tsplib(math.dist(a, b)) for b in coords] for a in coords]

    otimo = re.search(r"(Optimal|Best) value: (\d+)", cab.get("COMMENT", ""))
    k = re.search(r"-k(\d+)", cab["NAME"])

    return {
        "nome": cab["NAME"],
        "n": m - 1, # número de clientes
        "Q": int(cab["CAPACITY"]),
        "q": demandas, # q[0] = 0 (depósito)
        "dist": dist,
        "coords": coords,
        "k": int(k.group(1)) if k else None,
        "otimo": int(otimo.group(2)) if otimo else None,
    }


def round_tsplib(x):
    """Arredondamento da CVRPLIB: inteiro mais próximo."""
    return int(x + 0.5)


def ler_solucao(caminho):
    """Lê um .sol ("Route #1: 21 31 19 ..." e "Cost 784")."""
    rotas, custo = [], None
    for linha in open(caminho):
        if linha.startswith("Route"):
            rotas.append([int(c) for c in linha.split(":")[1].split()])
        elif linha.startswith("Cost"):
            custo = int(float(linha.split()[1]))
    return rotas, custo


if __name__ == "__main__":
    from solucao import avaliar, eh_viavel

    pasta_inst = sys.argv[1]
    pasta_sol = sys.argv[2] if len(sys.argv) > 2 else pasta_inst

    for arq in sorted(glob.glob(os.path.join(pasta_inst, "*.vrp"))):
        inst = ler_instancia(arq)
        texto = f"{inst['nome']:<12} n={inst['n']:<4} Q={inst['Q']:<5} ótimo={inst['otimo']}"

        arq_sol = os.path.join(pasta_sol, inst["nome"] + ".sol")
        if os.path.exists(arq_sol):
            rotas, custo = ler_solucao(arq_sol)
            ok = eh_viavel(rotas, inst) and avaliar(rotas, inst) == custo
            texto += f"  .sol: {avaliar(rotas, inst)} {'OK' if ok else 'ERRO'}"
        print(texto)
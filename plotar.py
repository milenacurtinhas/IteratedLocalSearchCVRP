"""
plotar.py - Desenha uma solução do CVRP (uma cor por rota).

Uso:
    python plotar.py A/A-n32-k5.vrp solucoes/A-n32-k5_semente1.sol   # desenha uma solução salva
    python plotar.py A/A-n32-k5.vrp A-solutions/A-n32-k5.sol         # desenha a ótima da CVRPLIB
    python plotar.py A/A-n32-k5.vrp 1                                # roda o ILS (semente 1),
                                                                     # salva o .sol e desenha

Salva a figura em solucoes/<nome do .sol>.png. Requer matplotlib.
"""

import os
import sys

import matplotlib.pyplot as plt

from leitor import ler_instancia, ler_solucao
from solucao import avaliar, carga_rota, salvar_solucao


def plotar(solucao, inst, arquivo):
    xy = inst["coords"]
    fig, ax = plt.subplots(figsize=(7, 7))
    cores = plt.cm.tab10.colors

    for idx, rota in enumerate(solucao):
        caminho = [0] + rota + [0] # depósito nas pontas
        xs = [xy[v][0] for v in caminho]
        ys = [xy[v][1] for v in caminho]
        cor = cores[idx % len(cores)]
        ax.plot(xs, ys, "-o", color=cor, markersize=5, linewidth=1.5,
                label=f"Rota {idx + 1}: carga {carga_rota(rota, inst)}/{inst['Q']}")
        for v in rota:
            ax.annotate(str(v), xy[v], textcoords="offset points", xytext=(4, 4), fontsize=7)

    ax.plot(*xy[0], "s", color="black", markersize=11, label="Depósito (0)")
    ax.set_title(f"{inst['nome']}: custo = {avaliar(solucao, inst)} "
                 f"(ótimo = {inst['otimo']}), {len(solucao)} rotas")
    ax.legend(fontsize=8, loc="best")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    print(f"Salvo: {arquivo}")


if __name__ == "__main__":
    inst = ler_instancia(sys.argv[1])
    segundo = sys.argv[2] if len(sys.argv) > 2 else "1"

    if segundo.endswith(".sol"): # solução já salva
        arq_sol = segundo
        solucao, _ = ler_solucao(arq_sol)
    else: # roda o ILS e salva
        from ils import ils
        semente = int(segundo)
        solucao = ils(inst, semente=semente, kmax=5, p_swap=0.75,
                      max_sem_melhora=6 * inst["n"])["solucao"]
        arq_sol = os.path.join("solucoes", f"{inst['nome']}_semente{semente}.sol")
        salvar_solucao(solucao, inst, arq_sol)
        print(f"Salvo: {arq_sol}")

    os.makedirs("solucoes", exist_ok=True)
    nome_fig = os.path.splitext(os.path.basename(arq_sol))[0] + ".png"
    plotar(solucao, inst, os.path.join("solucoes", nome_fig))
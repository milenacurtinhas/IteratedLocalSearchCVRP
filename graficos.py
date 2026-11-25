"""
graficos.py - Gráficos dos experimentos do ILS-RVND para o CVRP.

Uso (a partir da pasta do repositório):

    python graficos.py todos --conv B/B-n56-k7.vrp     # gera tudo (o TTT leva alguns minutos)

    python graficos.py calibracao                      # mapa de calor da calibração
    python graficos.py resultados                      # gap x tamanho, gap x ocupação, tempo x tamanho
    python graficos.py convergencia --conv B/B-n56-k7.vrp
    python graficos.py ttt --conv B/B-n56-k7.vrp --execucoes 50

Lê calibracao.csv, execucoes.csv e tabela_final.csv (gerados pelo experimentos.py)
e salva as figuras em graficos/. Usa matplotlib só para desenhar.

Convergência: refaz a melhor execução da instância (a semente do Min5 no
tabela_final.csv). Sem limite de tempo, o ILS é determinístico, então a curva
é a mesma da execução final.

TTT-plot (Aiex, Resende e Ribeiro, 2007): roda o ILS N vezes com sementes
1..N, parando ao atingir o ótimo (ou após --limite segundos), e desenha a
probabilidade acumulada de já ter atingido o alvo em função do tempo.
"""

import argparse
import csv
import json
import math
import os
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PASTA = "graficos"
CORES = {"A": "#D6457A", "B": "#6A4FB8", "F": "#2E9C6A"} # uma cor por conjunto
DESTAQUE = "#D6457A"
CINZA = "#9AA1AD"

plt.rcParams.update({
    "font.size": 13, "axes.titlesize": 15, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E6E6E6", "grid.linewidth": 0.8,
    "savefig.dpi": 200, "savefig.bbox": "tight",
})


def ler_csv(nome):
    with open(nome, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def n_clientes(nome):
    """A-n32-k5 -> 31 clientes (o número do nome conta o depósito)."""
    return int(nome.split("-n")[1].split("-")[0]) - 1


def salvar(fig, nome):
    os.makedirs(PASTA, exist_ok=True)
    caminho = os.path.join(PASTA, nome)
    fig.savefig(caminho)
    plt.close(fig)
    print(f"Salvo: {caminho}")


# 1. Calibração: gap médio de cada combinação

def grafico_calibracao(arq="calibracao.csv"):
    linhas = ler_csv(arq)
    kmaxs = sorted({int(l["kmax"]) for l in linhas})
    sems = sorted({int(l["sem_melhora"]) for l in linhas})
    pswaps = sorted({float(l["p_swap"]) for l in linhas})

    def gap_medio(k, m, p):
        g = [float(l["gap"]) for l in linhas
             if int(l["kmax"]) == k and int(l["sem_melhora"]) == m and float(l["p_swap"]) == p]
        return sum(g) / len(g)

    tabela = {(k, m, p): gap_medio(k, m, p) for k in kmaxs for m in sems for p in pswaps}
    melhor = min(tabela, key=tabela.get)
    vmax = max(tabela.values())

    fig, eixos = plt.subplots(1, len(sems), figsize=(4.2 * len(sems), 4.2))
    for ax, m in zip(eixos, sems):
        mat = [[tabela[(k, m, p)] for p in pswaps] for k in kmaxs]
        ax.imshow(mat, cmap="RdPu", vmin=0, vmax=vmax)
        ax.grid(False)
        ax.set_xticks(range(len(pswaps)), [str(p).replace(".", ",") for p in pswaps])
        ax.set_yticks(range(len(kmaxs)), [str(k) for k in kmaxs])
        ax.set_xlabel("p_swap")
        if m == sems[0]:
            ax.set_ylabel("kmax")
        ax.set_title(f"MaxSemMelhora = {m}n")
        for i, k in enumerate(kmaxs):
            for j, p in enumerate(pswaps):
                v = tabela[(k, m, p)]
                cor = "white" if v > 0.55 * vmax else "#14213D"
                peso = "bold" if (k, m, p) == melhor else "normal"
                ax.text(j, i, f"{v:.2f}%".replace(".", ","), ha="center", va="center",
                        color=cor, fontsize=13, fontweight=peso)
                if (k, m, p) == melhor:
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                               edgecolor="#14213D", linewidth=3))
    fig.suptitle("Gap médio nas 3 instâncias de teste (contorno = melhor combinação)",
                 fontsize=14, y=1.02)
    salvar(fig, "calibracao_mapa_calor.png")


# 2. Resultados finais

def resumo_por_instancia(arq="execucoes.csv"):
    """Para cada instância: gaps das 5 execuções e tempos totais."""
    res = {}
    for l in ler_csv(arq):
        r = res.setdefault(l["instancia"], {"gaps": [], "tempos": [], "otimo": int(l["otimo"])})
        r["gaps"].append(float(l["gap"]))
        r["tempos"].append(float(l["tempo_total"]))
    return res


def grafico_gap_tamanho(res):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for conj in "ABF":
        nomes = [n for n in res if n[0] == conj]
        x = [n_clientes(n) for n in nomes]
        med = [st.mean(res[n]["gaps"]) for n in nomes]
        lo = [m - min(res[n]["gaps"]) for n, m in zip(nomes, med)]
        hi = [max(res[n]["gaps"]) - m for n, m in zip(nomes, med)]
        ax.errorbar(x, med, yerr=[lo, hi], fmt="o", color=CORES[conj], ecolor=CORES[conj],
                    elinewidth=1, capsize=3, alpha=0.85, label=f"Conjunto {conj}")
    # rótulos nas 4 instâncias de maior gap médio
    piores = sorted(res, key=lambda n: -st.mean(res[n]["gaps"]))[:4]
    for k, n in enumerate(sorted(piores, key=n_clientes)):
        ax.annotate(n, (n_clientes(n), st.mean(res[n]["gaps"])), xytext=(8, 14 if k % 2 else -16),
                    textcoords="offset points", fontsize=11)
    ax.set_xlabel("Número de clientes (n)")
    ax.set_ylabel("Gap (%)")
    ax.set_title("Gap por tamanho da instância")
    ax.legend(frameon=False)
    ax.text(0.0, -0.18, "Marcador = gap médio das 5 execuções; barra = da melhor à pior execução.",
            transform=ax.transAxes, fontsize=11, color="#4A5568")
    salvar(fig, "gap_por_tamanho.png")


def grafico_tempo_tamanho(res):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for conj in "ABF":
        nomes = [n for n in res if n[0] == conj]
        ax.scatter([n_clientes(n) for n in nomes], [st.mean(res[n]["tempos"]) for n in nomes],
                   color=CORES[conj], s=45, label=f"Conjunto {conj}", alpha=0.9)
    maior = max(res, key=lambda n: st.mean(res[n]["tempos"]))
    ax.annotate(f"{maior}: {st.mean(res[maior]['tempos']):.0f} s".replace(".", ","),
                (n_clientes(maior), st.mean(res[maior]["tempos"])), xytext=(-150, -5),
                textcoords="offset points", fontsize=11)
    ax.set_yscale("log")
    ax.set_xlabel("Número de clientes (n)")
    ax.set_ylabel("Tempo médio por execução (s, escala log)")
    ax.set_title("Tempo de execução por tamanho da instância")
    ax.legend(frameon=False)
    salvar(fig, "tempo_por_tamanho.png")


def grafico_gap_ocupacao(res, pastas):
    """Ocupação da frota = demanda total / (k * Q). Precisa dos .vrp."""
    from leitor import ler_instancia
    ocup = {}
    for n in res:
        for p in pastas:
            arq = os.path.join(p, n + ".vrp")
            if os.path.exists(arq):
                inst = ler_instancia(arq)
                ocup[n] = 100 * sum(inst["q"]) / (inst["k"] * inst["Q"])
                break
    if len(ocup) < len(res):
        print(f"Gap x ocupação: encontrei {len(ocup)} de {len(res)} .vrp em {pastas}; "
              f"o gráfico usa só essas.")
    if not ocup:
        return
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for conj in "ABF":
        nomes = [n for n in ocup if n[0] == conj]
        ax.scatter([ocup[n] for n in nomes], [st.mean(res[n]["gaps"]) for n in nomes],
                   color=CORES[conj], s=45, label=f"Conjunto {conj}", alpha=0.9)
    ax.set_xlabel("Ocupação da frota: demanda total / (k · Q) (%)")
    ax.set_ylabel("Gap médio (%)")
    ax.set_title("Gap por ocupação da frota")
    ax.legend(frameon=False)
    salvar(fig, "gap_por_ocupacao.png")


# 3. Convergência da melhor execução

def semente_min5(nome, arq="tabela_final.csv"):
    for l in ler_csv(arq):
        if l["Instancia"] == nome:
            return int(l["Semente_Min5"])
    return 1


def grafico_convergencia(arq_vrp, kmax, sem_melhora, p_swap):
    from ils import ils
    from leitor import ler_instancia
    inst = ler_instancia(arq_vrp)
    s = semente_min5(inst["nome"])
    print(f"Convergência: refazendo {inst['nome']} com a semente {s}...")
    r = ils(inst, kmax=kmax, p_swap=p_swap, max_sem_melhora=sem_melhora * inst["n"], semente=s)
    melhor, atual = r["historico"], r["historico_atual"]
    it = list(range(len(melhor)))

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(it, atual, color=CINZA, linewidth=0.8, alpha=0.8, label="Solução da iteração, f(s')")
    ax.step(it, melhor, where="post", color=CORES["B"], linewidth=2.2, label="Melhor solução, f(s*)")
    ax.axhline(inst["otimo"], color=DESTAQUE, linestyle="--", linewidth=1.6,
               label=f"Ótimo conhecido ({inst['otimo']})")
    chegou = next((i for i, v in enumerate(melhor) if v <= inst["otimo"]), None)
    if chegou is not None:
        ax.annotate(f"ótimo na iteração {chegou}", (chegou, inst["otimo"]), xytext=(25, 35),
                    textcoords="offset points", fontsize=11,
                    arrowprops=dict(arrowstyle="->", color="#4A5568"))
    ax.set_xlabel("Iteração do ILS")
    ax.set_ylabel("Custo (distância total)")
    ax.set_title(f"Convergência da melhor execução: {inst['nome']} (semente {s})")
    ax.legend(frameon=False)
    salvar(fig, f"convergencia_{inst['nome']}.png")
    return {"instancia": inst["nome"], "semente": s, "iteracoes": len(melhor) - 1,
            "inicial": melhor[0], "final": melhor[-1], "iter_otimo": chegou}


# 4. TTT-plot

def grafico_ttt(arq_vrp, kmax, sem_melhora, p_swap, execucoes, limite):
    from ils import ils
    from leitor import ler_instancia
    inst = ler_instancia(arq_vrp)
    alvo = inst["otimo"]
    tempos, falhas = [], 0
    arq_tempos = os.path.join(PASTA, f"ttt_{inst['nome']}.json")
    print(f"TTT-plot: {execucoes} execuções em {inst['nome']}, alvo = {alvo}, limite = {limite} s")
    for s in range(1, execucoes + 1):
        r = ils(inst, kmax=kmax, p_swap=p_swap, max_sem_melhora=10 ** 9, max_iter=10 ** 9,
                semente=s, tempo_limite=limite, alvo=alvo)
        if r["custo"] <= alvo:
            tempos.append(r["tempo_melhor"])
        else:
            falhas += 1
        print(f"  semente {s:3d}: {'%.2f s' % r['tempo_melhor'] if r['custo'] <= alvo else 'não atingiu'}",
              flush=True)
    os.makedirs(PASTA, exist_ok=True)
    with open(arq_tempos, "w") as f:
        json.dump({"instancia": inst["nome"], "alvo": alvo, "tempos": tempos, "falhas": falhas}, f)

    tempos.sort()
    n = execucoes # falhas contam no denominador
    prob = [(i - 0.5) / n for i in range(1, len(tempos) + 1)]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(tempos, prob, "o", color=CORES["B"], markersize=5, label="Execuções (empírico)")
    # exponencial deslocada ajustada pelos quartis (Aiex, Resende e Ribeiro, 2007)
    if len(tempos) >= 8:
        q = lambda p: tempos[min(len(tempos) - 1, int(p * len(tempos)))]
        lam = (q(0.75) - q(0.25)) / math.log(3)
        mu = q(0.25) + lam * math.log(0.75)
        xs = [tempos[0] + i * (tempos[-1] - tempos[0]) / 200 for i in range(201)]
        ax.plot(xs, [max(0.0, 1 - math.exp(-(x - mu) / lam)) if lam > 0 else 0 for x in xs],
                "--", color=DESTAQUE, linewidth=1.6, label="Exponencial ajustada")
    ax.set_xlabel(f"Tempo até atingir o ótimo {alvo} (s)")
    ax.set_ylabel("Probabilidade acumulada")
    ax.set_ylim(0, 1.02)
    ax.set_title(f"TTT-plot: {inst['nome']} ({len(tempos)} de {execucoes} execuções atingiram o ótimo)")
    ax.legend(frameon=False, loc="lower right")
    salvar(fig, f"ttt_{inst['nome']}.png")

    if tempos:
        def em(t):
            return 100 * sum(x <= t for x in tempos) / n
        resumo = {"instancia": inst["nome"], "atingiram": len(tempos), "execucoes": n,
                  "min": tempos[0], "mediana": st.median(tempos), "max": tempos[-1],
                  "p50": tempos[int(0.5 * n) - 1] if len(tempos) >= int(0.5 * n) else None}
        for t in (1, 2, 5, 10):
            resumo[f"em_{t}s"] = em(t)
        print("Resumo TTT:", resumo)
        return resumo



if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gráficos do ILS-RVND para o CVRP")
    ap.add_argument("grafico", choices=["todos", "calibracao", "resultados", "convergencia",
                                        "ttt"])
    ap.add_argument("--conv", default="B/B-n56-k7.vrp",
                    help="instância de tamanho médio para convergência e TTT")
    ap.add_argument("--kmax", type=int, default=5)
    ap.add_argument("--sem-melhora", type=int, default=6)
    ap.add_argument("--p-swap", type=float, default=0.75)
    ap.add_argument("--execucoes", type=int, default=50, help="execuções do TTT-plot")
    ap.add_argument("--limite", type=float, default=180, help="limite por execução do TTT (s)")
    ap.add_argument("--pastas", nargs="*", default=["A", "B", "F"],
                    help="pastas com os .vrp (para o gráfico de ocupação)")
    a = ap.parse_args()

    if a.grafico in ("todos", "calibracao"):
        grafico_calibracao()
    if a.grafico in ("todos", "resultados"):
        res = resumo_por_instancia()
        grafico_gap_tamanho(res)
        grafico_tempo_tamanho(res)
        grafico_gap_ocupacao(res, a.pastas)
    if a.grafico in ("todos", "convergencia"):
        print(grafico_convergencia(a.conv, a.kmax, a.sem_melhora, a.p_swap))
    if a.grafico in ("todos", "ttt"):
        grafico_ttt(a.conv, a.kmax, a.sem_melhora, a.p_swap, a.execucoes, a.limite)
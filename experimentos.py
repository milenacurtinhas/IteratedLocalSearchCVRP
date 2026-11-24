"""
experimentos.py - Calibração dos parâmetros e testes finais do ILS-RVND.

Cada execução é gravada no CSV assim que termina. Se o programa for
interrompido, basta rodar o mesmo comando de novo: as execuções já feitas
são puladas.

1) Calibração: 27 combinações (kmax x MaxSemMelhora x p_swap), até 180 s cada.

    python experimentos.py calibrar A/A-n32-k5.vrp A/A-n80-k10.vrp B/B-n78-k10.vrp

   Também dá para rodar uma instância por vez (os resultados se acumulam em
   calibracao.csv). Para ver a análise a qualquer momento:

    python experimentos.py analisar

2) Testes finais: 5 execuções por instância com os parâmetros escolhidos.

    python experimentos.py final A B F --kmax 5 --sem-melhora 3 --p-swap 0.5

   Também dá para rodar uma pasta por vez. Gera execucoes.csv, historicos.json,
   tabela_final.csv (com todas as instâncias já executadas) e a solução de cada
   execução em solucoes/<instância>_semente<s>.sol.
"""

import argparse
import csv
import glob
import itertools
import json
import os
import re

from ils import ils
from leitor import ler_instancia
from solucao import eh_viavel, salvar_solucao

# Níveis (pequeno, médio, grande) de cada parâmetro calibrado
NIVEIS_KMAX = [2, 5, 10]
NIVEIS_SEM_MELHORA = [1, 3, 6] # multiplicam n: n, 3n e 6n
NIVEIS_P_SWAP = [0.25, 0.5, 0.75]
COMBINACOES = list(itertools.product(NIVEIS_KMAX, NIVEIS_SEM_MELHORA, NIVEIS_P_SWAP))

ARQ_CALIBRACAO = "calibracao.csv"
ARQ_EXECUCOES = "execucoes.csv"
ARQ_HISTORICOS = "historicos.json"
ARQ_TABELA = "tabela_final.csv"
PASTA_SOLUCOES = "solucoes"

COLUNAS = ["instancia", "otimo", "kmax", "sem_melhora", "p_swap", "semente",
           "fMH", "gap", "tempo_melhor", "tempo_total", "iteracoes"]
TIPOS = {"otimo": int, "kmax": int, "sem_melhora": int, "p_swap": float,
         "semente": int, "fMH": int, "gap": float, "tempo_melhor": float,
         "tempo_total": float, "iteracoes": int}

# Utilidades

def ordem_natural(texto):
    """A-n32-k5 antes de A-n101-k...: compara os números como números."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", texto)]


def listar_arquivos(caminhos):
    """Transforma pastas e arquivos em uma lista de .vrp."""
    arquivos = []
    for c in caminhos:
        if os.path.isdir(c):
            arquivos += glob.glob(os.path.join(c, "*.vrp"))
        else:
            arquivos.append(c)
    return sorted(arquivos, key=lambda a: ordem_natural(os.path.basename(a)))


def ler_csv(nome):
    if not os.path.exists(nome):
        return []
    with open(nome, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        for col, tipo in TIPOS.items():
            linha[col] = tipo(linha[col])
    return linhas


def anexar_csv(nome, linha):
    novo = not os.path.exists(nome)
    with open(nome, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
        if novo:
            w.writeheader()
        w.writerow(linha)


def chave(linha):
    """Identifica uma execução: instância + parâmetros + semente."""
    return (linha["instancia"], linha["kmax"], linha["sem_melhora"],
            linha["p_swap"], linha["semente"])


def gap(f, otimo):
    return 100 * (f - otimo) / otimo


def executar(inst, kmax, sem_melhora, p_swap, semente, tempo):
    """Uma execução do ILS. Devolve a linha do CSV, o histórico e a solução."""
    r = ils(inst,
            max_sem_melhora=sem_melhora * inst["n"],
            kmax=kmax, p_swap=p_swap, semente=semente, tempo_limite=tempo)
    assert eh_viavel(r["solucao"], inst)
    linha = {
        "instancia": inst["nome"], "otimo": inst["otimo"],
        "kmax": kmax, "sem_melhora": sem_melhora, "p_swap": p_swap, "semente": semente,
        "fMH": r["custo"], "gap": round(gap(r["custo"], inst["otimo"]), 2),
        "tempo_melhor": round(r["tempo_melhor"], 2),
        "tempo_total": round(r["tempo_total"], 2),
        "iteracoes": r["iteracoes"],
    }
    print(f"  {inst['nome']:<11} kmax={kmax:<2} semMelhora={sem_melhora}n p_swap={p_swap:<4} "
          f"semente={semente} -> f={r['custo']} gap={linha['gap']:.2f}% "
          f"({r['tempo_total']:.0f} s)", flush=True)
    return linha, r["historico"], r["solucao"]

# Calibração

def calibrar(args):
    tempo = args.tempo if args.tempo is not None else 180
    feitas = {chave(l) for l in ler_csv(ARQ_CALIBRACAO)}

    for arq in listar_arquivos(args.caminhos):
        inst = ler_instancia(arq)
        print(f"\n{inst['nome']}: {len(COMBINACOES)} combinações, até {tempo:.0f} s cada")
        for k, m, p in COMBINACOES:
            if (inst["nome"], k, m, p, 1) in feitas:
                continue
            linha, _, _ = executar(inst, k, m, p, semente=1, tempo=tempo)
            anexar_csv(ARQ_CALIBRACAO, linha)

    analisar(args)


def analisar(args):
    linhas = ler_csv(ARQ_CALIBRACAO)
    if not linhas:
        print(f"{ARQ_CALIBRACAO} não existe ou está vazio.")
        return
    instancias = sorted({l["instancia"] for l in linhas}, key=ordem_natural)

    def resumo(grupo):
        gaps = [l["gap"] for l in grupo]
        tempos = [l["tempo_total"] for l in grupo]
        return sum(gaps) / len(gaps), sum(tempos) / len(tempos)

    # 1) Cada combinação: fMH em cada instância, gap médio e tempo médio
    print(f"\n=== Combinações (gap médio nas instâncias: {', '.join(instancias)}) ===")
    print(f"{'kmax':>5}{'semMelh':>8}{'p_swap':>7}  "
          + "".join(f"{i:>11}" for i in instancias) + f"{'gap méd':>9}{'tempo méd':>10}")
    combs = {}
    for l in linhas:
        combs.setdefault((l["kmax"], l["sem_melhora"], l["p_swap"]), []).append(l)
    ordenadas = sorted(combs.items(), key=lambda c: resumo(c[1])[0])
    for (k, m, p), grupo in ordenadas:
        f = {l["instancia"]: l["fMH"] for l in grupo}
        g, t = resumo(grupo)
        incompleta = "" if len(grupo) == len(instancias) else "  (incompleta)"
        print(f"{k:>5}{str(m) + 'n':>8}{p:>7}  "
              + "".join(f"{f.get(i, '-'):>11}" for i in instancias)
              + f"{g:>8.2f}%{t:>9.0f}s{incompleta}")

    # 2) Efeito de cada parâmetro: média de todas as execuções com aquele nível
    print("\n=== Efeito de cada parâmetro (média sobre as demais combinações) ===")
    for nome, col in [("kmax", "kmax"), ("MaxSemMelhora", "sem_melhora"), ("p_swap", "p_swap")]:
        print(f"{nome}:")
        for nivel in sorted({l[col] for l in linhas}):
            g, t = resumo([l for l in linhas if l[col] == nivel])
            rotulo = f"{nivel}n" if col == "sem_melhora" else nivel
            print(f"    {str(rotulo):<6} gap médio = {g:5.2f}%   tempo médio = {t:5.0f} s")

    # 3) Melhor combinação completa
    completas = [c for c in ordenadas if len(c[1]) == len(instancias)]
    if completas:
        (k, m, p), grupo = completas[0]
        g, t = resumo(grupo)
        print(f"\nMelhor combinação: kmax={k}, MaxSemMelhora={m}n, p_swap={p} "
              f"(gap médio {g:.2f}%, tempo médio {t:.0f} s)")
        print(f"Testes finais: python experimentos.py final A B F "
              f"--kmax {k} --sem-melhora {m} --p-swap {p}")

# Testes finais

def final(args):
    feitas = {chave(l) for l in ler_csv(ARQ_EXECUCOES)}
    historicos = {}
    if os.path.exists(ARQ_HISTORICOS):
        with open(ARQ_HISTORICOS, encoding="utf-8") as f:
            historicos = json.load(f)

    for arq in listar_arquivos(args.caminhos):
        inst = ler_instancia(arq)
        for s in range(1, 6):
            if (inst["nome"], args.kmax, args.sem_melhora, args.p_swap, s) in feitas:
                continue
            linha, hist, sol = executar(inst, args.kmax, args.sem_melhora, args.p_swap, s, args.tempo)
            salvar_solucao(sol, inst, caminho_sol(inst["nome"], s))
            anexar_csv(ARQ_EXECUCOES, linha)
            historicos[f"{inst['nome']}|{s}"] = hist
            with open(ARQ_HISTORICOS, "w", encoding="utf-8") as f:
                json.dump(historicos, f)

    gerar_tabela(args)

def caminho_sol(nome, semente):
    return os.path.join(PASTA_SOLUCOES, f"{nome}_semente{semente}.sol")


def gerar_tabela(args):
    """Monta a tabela do enunciado com as execuções feitas com os parâmetros dados."""
    params = (args.kmax, args.sem_melhora, args.p_swap)
    linhas = [l for l in ler_csv(ARQ_EXECUCOES)
              if (l["kmax"], l["sem_melhora"], l["p_swap"]) == params]

    tabela = []
    for nome in sorted({l["instancia"] for l in linhas}, key=ordem_natural):
        rs = [l for l in linhas if l["instancia"] == nome]
        melhor = min(rs, key=lambda l: l["fMH"])
        otimo = rs[0]["otimo"]
        f_med = sum(l["fMH"] for l in rs) / len(rs)
        tabela.append({
            "Instancia": nome,
            "fSol_Otima": otimo,
            "fMH_Min5": melhor["fMH"],
            "fMH_Media5": round(f_med, 1),
            "Tempo_Min5": melhor["tempo_melhor"], # tempo da execução que deu Min5
            "Tempo_Media5": round(sum(l["tempo_melhor"] for l in rs) / len(rs), 2),
            "gapMin(%)": round(gap(melhor["fMH"], otimo), 2),
            "gapMedia(%)": round(gap(f_med, otimo), 2),
            "Execucoes": len(rs),
            "Semente_Min5": melhor["semente"], # para achar o histórico em historicos.json
        })

    with open(ARQ_TABELA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tabela[0]))
        w.writeheader()
        w.writerows(tabela)

    print(f"\n{'Instância':<12}{'Ótimo':>7}{'Min5':>7}{'Média5':>8}{'gapMin':>8}{'gapMéd':>8}")
    for t in tabela:
        print(f"{t['Instancia']:<12}{t['fSol_Otima']:>7}{t['fMH_Min5']:>7}{t['fMH_Media5']:>8}"
              f"{t['gapMin(%)']:>7}%{t['gapMedia(%)']:>7}%")
    print(f"\nSalvo: {ARQ_TABELA} ({len(tabela)} instâncias)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Experimentos do ILS-RVND para o CVRP")
    ap.add_argument("modo", choices=["calibrar", "analisar", "final"])
    ap.add_argument("caminhos", nargs="*", help="pastas e/ou arquivos .vrp")
    ap.add_argument("--kmax", type=int, default=5)
    ap.add_argument("--sem-melhora", type=int, default=3, help="fator de n (3 = 3n)")
    ap.add_argument("--p-swap", type=float, default=0.5)
    ap.add_argument("--tempo", type=float, default=None, help="limite por execução (s)")
    args = ap.parse_args()

    {"calibrar": calibrar, "analisar": analisar, "final": final}[args.modo](args)
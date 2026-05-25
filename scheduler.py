import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]


@dataclass
class SearchParams:
    riposi_anno_target: float = 54.0
    tol_riposi: float = 1.0
    domanda_feriali: int = 51
    domanda_domenica: int = 15
    max_consec: int = 6
    forza_feriale_reale: Optional[int] = 66
    riserva_domenica_pct: Optional[float] = None
    balance_weekday: bool = True
    n_min: int = 11
    n_max: int = 56
    k_min: int = 1
    k_max: int = 4
    timeout_per_attempt: int = 4


def _domenica_effettiva(
    dom_feriali: int,
    dom_domenica: int,
    forza_feriale_reale: Optional[int],
    riserva_domenica_pct: Optional[float],
) -> Tuple[int, float]:
    dom_domenica_eff = dom_domenica
    riserva_factor = 1.0

    if forza_feriale_reale is not None and dom_feriali > 0:
        riserva_factor = forza_feriale_reale / dom_feriali
        dom_domenica_eff = math.ceil(dom_domenica * riserva_factor)
    elif riserva_domenica_pct is not None:
        riserva_factor = 1.0 + (riserva_domenica_pct / 100.0)
        dom_domenica_eff = math.ceil(dom_domenica * riserva_factor)

    return dom_domenica_eff, riserva_factor


def solve_single(
    N: int,
    K: int,
    riposi_anno_target: float = 54.0,
    tol_riposi: float = 1.0,
    dom_feriali: int = 51,
    dom_domenica: int = 15,
    max_consec: int = 6,
    forza_feriale_reale: Optional[int] = None,
    riserva_domenica_pct: Optional[float] = None,
    balance_weekday: bool = True,
    timeout: int = 4,
) -> Optional[Dict[str, Any]]:
    m = cp_model.CpModel()
    x = {(w, d): m.NewBoolVar(f"x_{w}_{d}") for w in range(N) for d in range(7)}

    t_min = math.ceil((riposi_anno_target - tol_riposi) * N / 52)
    t_max = math.floor((riposi_anno_target + tol_riposi) * N / 52)
    if t_min > t_max:
        return None

    t = m.NewIntVar(t_min, t_max, "T")
    m.Add(t == sum(x.values()))

    r = [m.NewIntVar(0, N, f"r_{d}") for d in range(7)]
    for d in range(7):
        m.Add(r[d] == sum(x[w, d] for w in range(N)))

    dom_domenica_eff, riserva_factor = _domenica_effettiva(
        dom_feriali=dom_feriali,
        dom_domenica=dom_domenica,
        forza_feriale_reale=forza_feriale_reale,
        riserva_domenica_pct=riserva_domenica_pct,
    )

    demand = [dom_feriali] * 6 + [dom_domenica_eff]

    extra = [m.NewIntVar(0, K * N, f"e_{d}") for d in range(7)]
    for d in range(7):
        m.Add(K * (N - r[d]) - demand[d] == extra[d])

    if balance_weekday:
        for d in range(1, 6):
            m.Add(r[d] == r[0])

    l = N * 7
    flat = [x[w, d] for w in range(N) for d in range(7)]
    for s in range(l):
        m.Add(sum(flat[(s + k) % l] for k in range(max_consec + 1)) >= 1)

    max_extra = m.NewIntVar(0, K * N, "max_extra")
    m.AddMaxEquality(max_extra, extra)
    big = 10000
    m.Minimize(max_extra * big + sum(extra))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout
    solver.parameters.num_search_workers = 8
    status = solver.Solve(m)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    pattern = [[solver.Value(x[w, d]) for d in range(7)] for w in range(N)]
    counts = [sum(row) for row in pattern]
    pivot = counts.index(max(counts))
    pattern = pattern[pivot:] + pattern[:pivot]

    t_val = solver.Value(t)
    r_vals = [solver.Value(r[d]) for d in range(7)]
    extra_vals = [solver.Value(extra[d]) for d in range(7)]
    al_lavoro = [K * (N - r_vals[d]) for d in range(7)]

    return {
        "N": N,
        "K": K,
        "T": t_val,
        "pattern": pattern,
        "riposi_anno": t_val * 52 / N,
        "delta_riposi": t_val * 52 / N - riposi_anno_target,
        "r_per_day": dict(zip(GIORNI, r_vals)),
        "demand": dict(zip(GIORNI, demand)),
        "al_lavoro": dict(zip(GIORNI, al_lavoro)),
        "extra": dict(zip(GIORNI, extra_vals)),
        "dom_domenica_base": dom_domenica,
        "dom_domenica_eff": dom_domenica_eff,
        "riserva_factor": riserva_factor,
        "max_extra": max(extra_vals),
        "total_extra": sum(extra_vals),
        "tot_autisti": N * K,
        "status": "OTTIMO" if status == cp_model.OPTIMAL else "FEASIBLE",
    }


def search_solutions(
    params: SearchParams,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    results: List[Dict[str, Any]] = []
    attempts: List[Dict[str, Any]] = []

    for k in range(params.k_min, params.k_max + 1):
        for n in range(params.n_min, params.n_max + 1):
            if k * n < params.domanda_feriali:
                attempts.append(
                    {
                        "N": n,
                        "K": k,
                        "status": "SKIP",
                        "reason": "Capacita insufficiente sui feriali",
                    }
                )
                continue

            res = solve_single(
                N=n,
                K=k,
                riposi_anno_target=params.riposi_anno_target,
                tol_riposi=params.tol_riposi,
                dom_feriali=params.domanda_feriali,
                dom_domenica=params.domanda_domenica,
                max_consec=params.max_consec,
                forza_feriale_reale=params.forza_feriale_reale,
                riserva_domenica_pct=params.riserva_domenica_pct,
                balance_weekday=params.balance_weekday,
                timeout=params.timeout_per_attempt,
            )

            if res is None:
                attempts.append(
                    {
                        "N": n,
                        "K": k,
                        "status": "INF",
                        "reason": "Infattibile o timeout",
                    }
                )
                continue

            results.append(res)
            attempts.append(
                {
                    "N": n,
                    "K": k,
                    "status": res["status"],
                    "max_extra": res["max_extra"],
                    "total_extra": res["total_extra"],
                    "riposi_anno": round(res["riposi_anno"], 2),
                    "drivers": res["tot_autisti"],
                }
            )

    results.sort(
        key=lambda r: (
            r["max_extra"],
            r["total_extra"],
            abs(r["delta_riposi"]),
            r["tot_autisti"],
            r["N"],
        )
    )

    return results, attempts

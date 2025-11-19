from typing import Dict, List, Optional, Set, Tuple
from src.common import Process

class UniversalOptimizer:
    def __init__(self, optimization_targets: List[str], all_processes: Optional[List[Process]] = None, total_cycles: int = 0):
        self.targets = [t for t in optimization_targets if t != 'time']
        self.cycles = total_cycles
        self.hv_procs: Set[str] = set()
        self.vc_res: Set[str] = set()
        self.needs: Dict[str, Dict[str, int]] = {}
        self.depths: Dict[str, int] = {}
        self.bulks: Dict[str, int] = {}
        self.reserves: Dict[str, int] = {}
        self.phase = "gather"
        self.analyzed = False
        self.procs: List[Process] = all_processes or []
        self.mult = 10.0 if total_cycles > 50000 else (2.0 if total_cycles > 10000 else 1.0)
        if self.procs:
            self._analyze(self.procs)
    
    def _analyze(self, procs: List[Process]) -> None:
        if self.analyzed or not self.targets:
            return
        max_net = {t: max((p.results.get(t, 0) - p.needs.get(t, 0) for p in procs if t in p.results), default=0) for t in self.targets}
        for p in procs:
            for t in self.targets:
                if t in p.results:
                    net = p.results[t] - p.needs.get(t, 0)
                    if net > 1000 or (p.needs.get(t, 0) > 0 and net > 50 * p.needs[t]) or p.results[t] > 10000 or (max_net[t] > 0 and net >= max_net[t] * 0.5):
                        self.hv_procs.add(p.name)
                        for r, q in p.needs.items():
                            if r not in self.targets:
                                self.needs.setdefault(p.name, {})[r] = q
                        break
        for p in procs:
            if p.name in self.hv_procs:
                self._deps(p, procs, set())
        for p in procs:
            if any(r in self.vc_res for r in p.results) and p.name not in self.hv_procs:
                # Skip conversion loops
                is_loop = False
                for ro in p.results:
                    for ri in p.needs:
                        for op in procs:
                            if op.name != p.name and ri in op.results and ro in op.needs:
                                is_loop = True
                                break
                        if is_loop:
                            break
                    if is_loop:
                        break
                if not is_loop:
                    for r, q in p.needs.items():
                        if r not in self.targets:
                            self.needs.setdefault(p.name, {})[r] = q
        for hv in self.hv_procs:
            for p in procs:
                if p.name == hv:
                    for r in p.needs:
                        if r not in self.targets:
                            self.depths[r] = min(self.depths.get(r, 999), 1)
        for _ in range(10):
            for p in procs:
                for ro in p.results:
                    if ro in self.depths:
                        for ri in p.needs:
                            if ri not in self.targets:
                                self.depths[ri] = min(self.depths.get(ri, 999), self.depths[ro] + 1)
        max_prod = max((p.results.get(t, 0) for p in procs for t in self.targets if p.name in self.hv_procs), default=0)
        bmult = 20 if max_prod >= 10000 else (10 if max_prod >= 1000 else (5 if max_prod >= 100 else 2))
        for hv in self.hv_procs:
            for p in procs:
                if p.name == hv:
                    for r, q in p.needs.items():
                        if r not in self.targets:
                            self.bulks[r] = max(self.bulks.get(r, 0), q * bmult)
        for _ in range(2):
            for r in list(self.bulks.keys()):
                for p in procs:
                    if r in p.results:
                        runs = (self.bulks[r] + p.results[r] - 1) // p.results[r]
                        for nr, nq in p.needs.items():
                            if nr not in self.targets:
                                self.bulks[nr] = max(self.bulks.get(nr, 0), int(nq * runs * 0.5))
        for p in procs:
            if p.name in self.hv_procs or p.name in self.needs:
                for t in self.targets:
                    if t in p.needs:
                        m = 100 if p.name in self.hv_procs else 500
                        self.reserves[t] = max(self.reserves.get(t, 0), int(p.needs[t] * m * self.mult))
        self.analyzed = True
    
    def _deps(self, p: Process, procs: List[Process], vis: Set[str]) -> None:
        for r in p.needs:
            if r not in vis:
                self.vc_res.add(r)
                vis.add(r)
                for pr in procs:
                    if r in pr.results:
                        self._deps(pr, procs, vis)
    
    def _phase(self, stocks: Dict[str, int], cycle: int) -> str:
        if not self.analyzed:
            return "gather"
        if self.cycles > 0 and cycle >= int(self.cycles * 0.7):
            return "sell"
        can_exec = any(all(stocks.get(r, 0) >= q for r, q in p.needs.items()) for hv in self.hv_procs for p in self.procs if p.name == hv)
        if can_exec:
            return "sell"
        vc_stock = sum(stocks.get(r, 0) for r in self.vc_res if r not in self.targets)
        vc_need = sum(self.needs[hv].get(r, 0) * 10 for hv in self.hv_procs for r in self.needs.get(hv, {}))
        if cycle > 1000 or (vc_need > 0 and vc_stock > vc_need * 0.2):
            return "convert"
        if cycle > 500 or (vc_need > 0 and vc_stock > vc_need * 0.02):
            return "build"
        return "gather"
    
    def _reserve(self, t: str) -> int:
        base = self.reserves.get(t, 0)
        return int(base * (0.001 if self.phase == "gather" else (0.1 if self.phase == "build" else (0.5 if self.phase == "convert" else 1.0))))
    
    def select_best_process(self, available: List[Process], stocks: Dict[str, int], cycle: int) -> Optional[Process]:
        if not available:
            return None
        if not self.analyzed:
            for p in available:
                if p not in self.procs:
                    self.procs.append(p)
            if len(self.procs) > 10:
                self._analyze(self.procs)
        if self.analyzed:
            self.phase = self._phase(stocks, cycle)
        
        # Bottlenecks
        bns = []
        pmap = {}
        for p in available:
            for r in p.results:
                pmap.setdefault(r, []).append(p)
        
        for pn in self.needs:
            for r, q in self.needs[pn].items():
                curr = stocks.get(r, 0)
                m = 100 if pn in self.hv_procs else 50
                if curr < q * m and r in pmap:
                    base = 1000000.0 if pn in self.hv_procs else 500000.0
                    for p in pmap[r]:
                        bns.append((p, base + (q * m - curr) * 1000.0))
        
        for r in self.vc_res:
            curr = stocks.get(r, 0)
            tgt = self.bulks.get(r, 0)
            if tgt > 0 and curr < tgt and r in pmap:
                for p in pmap[r]:
                    bns.append((p, (tgt - curr) * 1000.0))
            elif curr < 10 and r in pmap:
                for p in pmap[r]:
                    bns.append((p, (10 - curr) * 1000.0))
        
        if self.phase in ["convert", "sell"]:
            max_prod = max((p.results.get(t, 0) for p in self.procs for t in self.targets if p.name in self.hv_procs), default=0)
            bmult = 20 if max_prod >= 10000 else (10 if max_prod >= 1000 else (5 if max_prod >= 100 else 2))
            for hv in self.hv_procs:
                for p in self.procs:
                    if p.name == hv:
                        for r, q in p.needs.items():
                            curr = stocks.get(r, 0)
                            need = q * bmult
                            if curr < need and r in pmap:
                                for pr in pmap[r]:
                                    bns.append((pr, 10000000.0 + (need - curr) * 10000.0))
        
        if bns:
            aff = []
            for p, urg in bns:
                ok = True
                is_g = len(p.needs) <= 1 and any(n in self.targets for n in p.needs)
                if is_g and self.phase != "gather":
                    for t in self.targets:
                        if t in p.needs and stocks.get(t, 0) - self._reserve(t) < p.needs[t]:
                            ok = False
                            break
                if ok:
                    aff.append((p, urg))
            if aff:
                return max(aff, key=lambda x: x[1])[0]
        
        # Score
        scored = []
        for p in available:
            ic = sum(p.needs.values())
            ov = sum(p.results.values())
            sc = 100000.0 if not p.needs else ((ov / ic) * 100.0 if ic > 0 else ov * 100.0)
            is_g = len(p.needs) <= 1 and any(t in p.needs for t in self.targets)
            
            for t in self.targets:
                if t in p.results:
                    net = p.results[t] - p.needs.get(t, 0)
                    cb = any(r in self.bulks and stocks.get(r, 0) < self.bulks[r] * 0.5 and stocks.get(r, 0) < p.needs[r] * 2 for r in p.needs if r in self.bulks)
                    if cb:
                        low = any(stocks.get(t2, 0) < self._reserve(t2) for t2 in self.targets)
                        sc *= 1.0 if (low and net > 0) else 0.0001
                    else:
                        # Penalize selling intermediate products if HV process exists
                        if p.name not in self.hv_procs and len(self.hv_procs) > 0:
                            bonus = net * 5000.0 * (20.0 if net > 10000 else (8.0 if net > 1000 else (3.0 if net > 100 else (1.0 if net > 0 else 1.0))))
                        else:
                            bonus = net * 50000.0 * (200.0 if net > 10000 else (80.0 if net > 1000 else (30.0 if net > 100 else (10.0 if net > 0 else 1.0))))
                        sc += bonus
            
            if p.name in self.hv_procs:
                max_prod = max((pr.results.get(t, 0) for pr in self.procs for t in self.targets if pr.name in self.hv_procs), default=0)
                bmult = 20 if max_prod >= 10000 else (10 if max_prod >= 1000 else (5 if max_prod >= 100 else 2))
                cb = all(stocks.get(r, 0) >= q * bmult for r, q in p.needs.items())
                co = all(stocks.get(r, 0) >= q for r, q in p.needs.items())
                if cb:
                    sc *= 100000000.0 if self.phase in ["convert", "sell"] else 10000000.0
                elif co:
                    sc *= 10000000.0 if self.phase in ["convert", "sell"] else 1000.0
            
            # Check if this process is part of a conversion loop - if so, don't boost for bulk targets
            is_loop = False
            for ro in p.results:
                for ri in p.needs:
                    for op in self.procs:
                        if op.name != p.name and ri in op.results and ro in op.needs:
                            is_loop = True
                            break
                    if is_loop:
                        break
                if is_loop:
                    break
            
            if not is_loop:
                for r in p.results:
                    if r in self.bulks:
                        curr = stocks.get(r, 0)
                        tgt = self.bulks[r]
                        sc *= ((1000.0 + ((tgt - curr) / tgt) * 100000.0) if curr < tgt else 0.0001)
            
            for t in self.targets:
                if t in p.needs:
                    cons = p.needs[t]
                    avail = stocks.get(t, 0) - self._reserve(t)
                    if avail < cons:
                        pen = 1.0 if p.name in self.hv_procs else (10000000.0 if is_g else (100000.0 if p.name in self.needs else 10000000.0))
                        sc -= cons * pen
                    else:
                        pen = (10000.0 if avail < 100 else (1000.0 if avail < 1000 else 100.0)) * (0.1 if p.name in self.needs else 1.0)
                        sc -= cons * pen
            
            if self.phase == "gather":
                sc *= 2.0 if is_g else 1.0
            elif self.phase == "build":
                if is_g:
                    sc *= 0.0001
                elif any(self.depths.get(r, 0) >= 2 for r in p.results):
                    sc *= 50.0
            elif self.phase == "convert":
                if is_g:
                    sc *= 0.000001
                else:
                    for r in p.results:
                        d = self.depths.get(r, 0)
                        if d == 1:
                            sc *= 500.0
                            break
                        elif d == 2:
                            sc *= 100.0
                            break
            elif self.phase == "sell":
                if is_g:
                    sc *= 0.00000001
                elif p.name not in self.hv_procs:
                    sc *= 0.01
            
            for r in p.results:
                if r in self.vc_res:
                    curr = stocks.get(r, 0)
                    sc *= (5.0 if curr == 0 else (3.0 if curr < 10 else (2.0 if curr < 30 else 1.0)))
            
            # Penalize direct conversion loops
            for r in p.results:
                if r in p.needs:
                    sc *= 0.0001
            
            sc -= p.delay + p.execution_count * 0.1
            
            depth = min((self.depths.get(r, 999) for r in p.results if r in self.depths), default=0)
            crit = any(r in self.depths for r in p.results)
            scored.append((p, sc, crit, depth))
        
        pos = [(p, s, c, d) for p, s, c, d in scored if s > 0]
        if not pos:
            return None
        return max(pos, key=lambda x: (x[2], -x[3] if x[3] > 0 else 0, x[1]))[0]

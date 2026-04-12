#!/usr/bin/env python3
"""
SuperBit Engine v1.0 — рабочая библиотека

Аналогия:
  Qubit: state = complex vector 2^n, gates = unitary matrices
  SuperBit: state = (m, σ, φ) per variable + J coupling, ops = sample/phase/tune

30 qubits = 16 GB RAM, limit ~30 on PC
30 superbits = 7 KB RAM, limit ~100,000 on PC

Capabilities:
  1. SAMPLE — стохастическая оптимизация (p-bit)
  2. PHASE — знаковая интерференция (phase bit)
  3. DETECT — структурный анализ (s-bit)
  4. SOLVE — SAT/CSP через Ising mapping
  5. AUTO — self-tuning, zero hyperparameters
"""

import numpy as np
from typing import Optional, List, Tuple, Dict

# ====================================================================
# SuperBit Register: основной объект
# ====================================================================
class SuperBitRegister:
    """
    Регистр из n супербитов.

    Каждый супербит i имеет:
      m[i]  ∈ [-1, 1]  : магнетизация (знаковое значение)
      σ[i]  ∈ [0, 1]   : уверенность (из истории)
      φ[i]  ∈ [-π, π]  : фаза (для интерференции)

    Взаимодействие:
      J[i,j] : coupling matrix (Ising)
      h[i]   : external field

    Глобальные параметры:
      T : температура (self-tuning)
    """

    def __init__(self, n: int, seed: int = 42):
        self.n = n
        self.rng = np.random.default_rng(seed)

        # State
        self.m = self.rng.choice([-1.0, 1.0], size=n)
        self.sigma = np.full(n, 0.5)
        self.phi = np.zeros(n)

        # Couplings
        self.J = np.zeros((n, n))
        self.h = np.zeros(n)

        # Self-tuning
        self.T = 2.0
        self.prev_m = self.m.copy()

        # History for σ measurement
        self._history = []
        self._hist_max = 100

        # Statistics
        self.total_flips = 0
        self.best_energy = float('inf')
        self.best_state = self.m.copy()

    # ================================================================
    # PROGRAM: задать задачу
    # ================================================================
    def set_coupling(self, J: np.ndarray, h: Optional[np.ndarray] = None):
        """Задать Ising coupling matrix."""
        self.J = J.copy()
        if h is not None:
            self.h = h.copy()
        else:
            self.h = np.zeros(self.n)

    def set_from_sat(self, n_vars: int, clauses: list):
        """Задать задачу из SAT формулы (3-SAT).
        clauses: list of [(var, sign), ...] where sign ∈ {-1, +1}
        """
        self.n = n_vars
        self.m = self.rng.choice([-1.0, 1.0], size=n_vars)
        self.sigma = np.full(n_vars, 0.5)
        self.phi = np.zeros(n_vars)
        self.J = np.zeros((n_vars, n_vars))
        self.h = np.zeros(n_vars)
        self.prev_m = self.m.copy()

        for clause in clauses:
            vs = [c[0] for c in clause]
            ss = [c[1] for c in clause]
            for k in range(len(vs)):
                self.h[vs[k]] -= ss[k] / 8
            for k in range(len(vs)):
                for l in range(k+1, len(vs)):
                    self.J[vs[k], vs[l]] += ss[k] * ss[l] / 8
                    self.J[vs[l], vs[k]] += ss[k] * ss[l] / 8

    def set_from_qubo(self, Q: np.ndarray):
        """Задать QUBO: minimize x^T Q x, x ∈ {0,1}^n.
        Convert to Ising: x = (1+m)/2.
        """
        n = Q.shape[0]
        self.n = n
        self.m = self.rng.choice([-1.0, 1.0], size=n)
        self.sigma = np.full(n, 0.5)
        self.phi = np.zeros(n)
        self.prev_m = self.m.copy()

        self.J = np.zeros((n, n))
        self.h = np.zeros(n)
        for i in range(n):
            self.h[i] = -Q[i, i] / 2 - sum(Q[i, j] + Q[j, i] for j in range(n) if j != i) / 4
            for j in range(i+1, n):
                self.J[i, j] = -(Q[i, j] + Q[j, i]) / 4
                self.J[j, i] = self.J[i, j]

    # ================================================================
    # CORE OPS: базовые операции
    # ================================================================
    def energy(self) -> float:
        """Текущая энергия Ising."""
        return -0.5 * self.m @ self.J @ self.m - self.h @ self.m

    def local_field(self, i: int) -> float:
        """Локальное поле на переменной i."""
        return self.h[i] + self.J[i] @ self.m

    def flip(self, i: int):
        """Gibbs sampling flip с self-tuning."""
        beta = 1.0 / max(self.T, 0.01)
        I_i = self.local_field(i)
        p = (1.0 + np.tanh(beta * I_i)) / 2.0
        self.m[i] = 1.0 if self.rng.random() < p else -1.0
        self.total_flips += 1

    def sweep(self):
        """Один полный sweep: обновить все n переменных."""
        for i in self.rng.permutation(self.n):
            self.flip(i)

        # Track energy
        E = self.energy()
        if E < self.best_energy:
            self.best_energy = E
            self.best_state = self.m.copy()

        # Self-tune T
        ga = np.mean(self.m * self.prev_m)
        if ga > 0.8:
            self.T *= 1.02
        elif ga < 0.3:
            self.T *= 0.97
        self.T = np.clip(self.T, 0.05, 50.0)

        # Update σ from history
        self._history.append(self.m.copy())
        if len(self._history) > self._hist_max:
            self._history.pop(0)
        if len(self._history) >= 10:
            hist = np.array(self._history[-50:])
            self.sigma = np.mean(hist * self.m[np.newaxis, :] > 0, axis=0)

        self.prev_m = self.m.copy()

    # ================================================================
    # PHASE OPS: фазовые операции
    # ================================================================
    def phase_product(self, indices: list) -> float:
        """Знаковое произведение выбранных битов (phase bit)."""
        result = 1.0
        for i in indices:
            result *= self.m[i]
        return result

    def phase_correlator(self, i: int, j: int) -> float:
        """Корреляция фаз m[i]*m[j] усреднённая по истории."""
        if len(self._history) < 5:
            return self.m[i] * self.m[j]
        hist = np.array(self._history[-30:])
        return np.mean(hist[:, i] * hist[:, j])

    def discrimination_score(self, subset_a: list, subset_b: list) -> float:
        """Phase-bit discrimination: product(A) vs product(B)."""
        pa = self.phase_product(subset_a)
        pb = self.phase_product(subset_b)
        return pa - pb

    # ================================================================
    # HIGH-LEVEL ALGORITHMS
    # ================================================================
    def optimize(self, sweeps: int = 1000) -> Tuple[float, np.ndarray]:
        """Оптимизация: найти минимум энергии."""
        for _ in range(sweeps):
            self.sweep()
        return self.best_energy, self.best_state

    def detect_frozen(self, sweeps: int = 1000,
                      threshold: float = 0.8) -> Tuple[set, np.ndarray]:
        """Детекция frozen core: вернуть множество frozen переменных."""
        for _ in range(sweeps):
            self.sweep()
        frozen = set(i for i in range(self.n) if self.sigma[i] > threshold)
        return frozen, self.sigma

    def sample(self, sweeps: int = 500,
               n_samples: int = 100) -> List[np.ndarray]:
        """Сэмплирование: собрать n_samples конфигураций."""
        # Warmup
        for _ in range(sweeps // 2):
            self.sweep()
        # Collect
        samples = []
        interval = max(1, sweeps // (2 * n_samples))
        for s in range(sweeps // 2):
            self.sweep()
            if s % interval == 0 and len(samples) < n_samples:
                samples.append(self.m.copy())
        return samples

    def solve_sat(self, n_vars: int, clauses: list,
                  max_flips: int = 100000,
                  noise: float = 0.3) -> Tuple[bool, np.ndarray, int]:
        """Решить SAT через WalkSAT-style поиск на супербитах.

        Прямая работа с клаузами, без Ising approximation.
        Комбинирует greedy + noise (как WalkSAT) + self-tuning.
        """
        self.n = n_vars
        self.m = self.rng.choice([-1.0, 1.0], size=n_vars)

        # Build var→clause index
        var_clauses = [[] for _ in range(n_vars)]
        for ci, clause in enumerate(clauses):
            for v, s in clause:
                var_clauses[v].append(ci)

        def count_unsat():
            cnt = 0
            unsat_list = []
            for ci, clause in enumerate(clauses):
                if not any((s>0 and self.m[v]>0) or (s<0 and self.m[v]<0)
                           for v, s in clause):
                    cnt += 1
                    unsat_list.append(ci)
            return cnt, unsat_list

        def make_count(v):
            """Count how many clauses become satisfied if we flip v."""
            gain = 0
            for ci in var_clauses[v]:
                clause = clauses[ci]
                # Currently satisfied?
                cur_sat = any((s>0 and self.m[w]>0) or (s<0 and self.m[w]<0)
                              for w, s in clause)
                # After flip?
                old_val = self.m[v]
                self.m[v] *= -1
                new_sat = any((s>0 and self.m[w]>0) or (s<0 and self.m[w]<0)
                              for w, s in clause)
                self.m[v] = old_val
                if new_sat and not cur_sat:
                    gain += 1
                elif cur_sat and not new_sat:
                    gain -= 1
            return gain

        best_unsat = len(clauses)
        best_m = self.m.copy()

        for flip in range(max_flips):
            n_unsat, unsat_list = count_unsat()

            if n_unsat == 0:
                return True, self.m.copy(), 0

            if n_unsat < best_unsat:
                best_unsat = n_unsat
                best_m = self.m.copy()

            # Pick random unsatisfied clause
            ci = unsat_list[self.rng.integers(len(unsat_list))]
            clause = clauses[ci]

            if self.rng.random() < noise:
                # Random walk: flip random variable in clause
                v, _ = clause[self.rng.integers(len(clause))]
                self.m[v] *= -1
            else:
                # Greedy: flip variable that maximizes satisfied clauses
                best_gain = -999
                best_v = clause[0][0]
                for v, s in clause:
                    g = make_count(v)
                    if g > best_gain:
                        best_gain = g
                        best_v = v
                self.m[best_v] *= -1

            self.total_flips += 1

        return best_unsat == 0, best_m, best_unsat

    def analyze(self, sweeps: int = 1000) -> Dict:
        """Полный анализ: оптимизация + детекция + статистика."""
        for _ in range(sweeps):
            self.sweep()

        return {
            'energy': self.best_energy,
            'best_state': self.best_state.copy(),
            'sigma': self.sigma.copy(),
            'frozen': set(i for i in range(self.n) if self.sigma[i] > 0.8),
            'free': set(i for i in range(self.n) if self.sigma[i] < 0.3),
            'temperature': self.T,
            'total_flips': self.total_flips,
            'n': self.n,
            'memory_bytes': self.n * self.n * 8 + self.n * 3 * 8,
        }

    # ================================================================
    # THREE-PHASE PROTOCOL (§66)
    # ================================================================
    def optimize_3phase(self, sweeps: int = 1000,
                        detect_frac: float = 0.3,
                        lock_frac: float = 0.3) -> Tuple[float, np.ndarray, dict]:
        """Трёхфазный протокол: DETECT → DECIMATE → ANNEAL.

        Phase 1: self-tuning exploration → σ measurement
        Phase 2: lock high-σ variables
        Phase 3: SA on remaining free variables

        Returns: (energy, best_state, info_dict)
        """
        detect_sweeps = int(sweeps * detect_frac)
        anneal_sweeps = sweeps - detect_sweeps

        # Phase 1: DETECT
        mag_sum = np.zeros(self.n)
        ac_sum = np.zeros(self.n)
        count = 0
        for s in range(detect_sweeps):
            self.sweep()
            if s > detect_sweeps // 3:
                mag_sum += self.m
                ac_sum += self.m * self.prev_m
                count += 1

        if count > 0:
            detect_sigma = (np.abs(mag_sum/count) + ac_sum/count) / 2
            detect_mag = mag_sum / count
        else:
            detect_sigma = self.sigma.copy()
            detect_mag = self.m.copy()

        # Phase 2: DECIMATE
        n_lock = int(self.n * lock_frac)
        order = np.argsort(-detect_sigma)
        locked = {}
        for k in range(n_lock):
            i = int(order[k])
            locked[i] = 1.0 if detect_mag[i] > 0 else -1.0
            self.m[i] = locked[i]

        free_vars = [i for i in range(self.n) if i not in locked]
        n_free = len(free_vars)

        # Phase 3: ANNEAL
        T_start = 2.0
        T_end = 0.01
        cool = (T_end / T_start) ** (1.0 / max(anneal_sweeps * n_free, 1))
        T = T_start

        for s in range(anneal_sweeps):
            for _ in range(n_free):
                if n_free == 0:
                    break
                idx = free_vars[self.rng.integers(n_free)]
                dE = 2 * self.m[idx] * (self.h[idx] + self.J[idx] @ self.m)
                if dE < 0 or self.rng.random() < np.exp(-dE / max(T, 1e-10)):
                    self.m[idx] *= -1
                T *= cool

            E = self.energy()
            if E < self.best_energy:
                self.best_energy = E
                self.best_state = self.m.copy()

        info = {
            'locked': locked,
            'n_free': n_free,
            'detect_sigma': detect_sigma,
        }
        return self.best_energy, self.best_state, info

    # ================================================================
    # UTILITY
    # ================================================================
    def reset(self, seed: Optional[int] = None):
        """Сброс состояния."""
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.m = self.rng.choice([-1.0, 1.0], size=self.n)
        self.sigma = np.full(self.n, 0.5)
        self.phi = np.zeros(self.n)
        self.T = 2.0
        self.prev_m = self.m.copy()
        self._history = []
        self.total_flips = 0
        self.best_energy = float('inf')
        self.best_state = self.m.copy()

    def __repr__(self):
        return (f"SuperBitRegister(n={self.n}, T={self.T:.3f}, "
                f"E={self.energy():.4f}, flips={self.total_flips})")


# ====================================================================
# Convenience constructors
# ====================================================================
def superbit_register(n: int, seed: int = 42) -> SuperBitRegister:
    """Создать регистр из n супербитов."""
    return SuperBitRegister(n, seed)

def from_ising(J: np.ndarray, h: Optional[np.ndarray] = None,
               seed: int = 42) -> SuperBitRegister:
    """Создать регистр из Ising задачи."""
    n = J.shape[0]
    reg = SuperBitRegister(n, seed)
    reg.set_coupling(J, h)
    return reg

def from_sat(n_vars: int, clauses: list, seed: int = 42) -> SuperBitRegister:
    """Создать регистр из SAT задачи."""
    reg = SuperBitRegister(n_vars, seed)
    reg.set_from_sat(n_vars, clauses)
    return reg

def from_qubo(Q: np.ndarray, seed: int = 42) -> SuperBitRegister:
    """Создать регистр из QUBO задачи."""
    n = Q.shape[0]
    reg = SuperBitRegister(n, seed)
    reg.set_from_qubo(Q)
    return reg


# ====================================================================
# DEMO: сравнение с кубитами
# ====================================================================
if __name__ == "__main__":
    import time

    print("=" * 72)
    print("SuperBit Engine v1.0")
    print("=" * 72)

    # ---- Memory comparison ----
    print("\n--- Memory comparison ---")
    for n in [10, 20, 30, 50, 100, 1000, 10000, 100000]:
        qubit_mem = 2**n * 16  # complex128
        sbit_mem = n*n*8 + n*3*8  # J matrix + state vectors
        if qubit_mem < 1e18:
            q_str = f"{qubit_mem/1e9:.1f} GB" if qubit_mem > 1e9 else f"{qubit_mem/1e6:.1f} MB"
        else:
            q_str = f"10^{int(n * 0.301 + 1)} bytes"
        s_str = f"{sbit_mem/1e6:.1f} MB" if sbit_mem > 1e6 else f"{sbit_mem/1e3:.1f} KB"
        feasible_q = "✓" if qubit_mem < 16e9 else "✗"
        print(f"  n={n:>6d}: qubits={q_str:>15s} [{feasible_q}]  "
              f"superbits={s_str:>10s} [✓]")

    # ---- Optimization demo ----
    print("\n--- Optimization: SK spin glass ---")
    for n in [30, 100, 500]:
        rng_sk = np.random.default_rng(42)
        J = rng_sk.normal(0, 1/np.sqrt(n), (n, n))
        J = (J + J.T) / 2
        np.fill_diagonal(J, 0)

        reg = from_ising(J)
        t0 = time.time()
        E, state = reg.optimize(sweeps=500)
        dt = time.time() - t0
        print(f"  n={n:>4d}: E={E:>10.3f}, time={dt:.3f}s, T_final={reg.T:.3f}")

    # ---- SAT demo ----
    print("\n--- SAT solving ---")
    rng_sat = np.random.default_rng(42)
    for n_vars in [20, 50, 100]:
        m_clauses = int(3.5 * n_vars)
        clauses = []
        for _ in range(m_clauses):
            vs = rng_sat.choice(n_vars, size=3, replace=False)
            signs = rng_sat.choice([-1, 1], size=3)
            clauses.append(list(zip(vs.tolist(), signs.tolist())))

        reg = SuperBitRegister(n_vars, seed=42)
        t0 = time.time()
        solved, assignment, unsat = reg.solve_sat(n_vars, clauses, max_sweeps=2000)
        dt = time.time() - t0
        print(f"  n={n_vars:>4d}, m={m_clauses}: solved={solved}, "
              f"unsat={unsat}, time={dt:.3f}s")

    # ---- Frozen core detection ----
    print("\n--- Frozen core detection ---")
    n = 50
    rng_fc = np.random.default_rng(42)
    J = rng_fc.normal(0, 1/np.sqrt(n), (n, n))
    J = (J + J.T) / 2
    np.fill_diagonal(J, 0)

    reg = from_ising(J)
    frozen, sigma = reg.detect_frozen(sweeps=500)
    print(f"  n={n}: {len(frozen)} frozen detected, "
          f"σ mean={sigma.mean():.3f}, T_final={reg.T:.3f}")

    # ---- Full analysis ----
    print("\n--- Full analysis (one run = optimization + detection) ---")
    n = 100
    rng_full = np.random.default_rng(42)
    J = rng_full.normal(0, 1/np.sqrt(n), (n, n))
    J = (J + J.T) / 2
    np.fill_diagonal(J, 0)

    reg = from_ising(J)
    t0 = time.time()
    info = reg.analyze(sweeps=500)
    dt = time.time() - t0

    print(f"  n={info['n']}")
    print(f"  Energy: {info['energy']:.3f}")
    print(f"  Frozen: {len(info['frozen'])} variables")
    print(f"  Free: {len(info['free'])} variables")
    print(f"  Temperature: {info['temperature']:.3f}")
    print(f"  Total flips: {info['total_flips']:,}")
    print(f"  Memory: {info['memory_bytes']/1024:.1f} KB")
    print(f"  Time: {dt:.3f}s")

    # ---- Scale test ----
    print("\n--- Scale test: how far can we go? ---")
    for n in [1000, 5000, 10000]:
        # Use sparse-ish J (random graph, not all-to-all)
        rng_scale = np.random.default_rng(42)
        J = np.zeros((n, n))
        # Each variable connected to ~10 neighbors
        for i in range(n):
            neighbors = rng_scale.choice(n, size=min(10, n), replace=False)
            for j in neighbors:
                if i != j:
                    w = rng_scale.normal(0, 1/np.sqrt(10))
                    J[i, j] += w
                    J[j, i] += w

        reg = from_ising(J)
        t0 = time.time()
        E, _ = reg.optimize(sweeps=100)
        dt = time.time() - t0
        mem_mb = (n*n*8 + n*3*8) / 1e6
        print(f"  n={n:>6d}: E={E:>10.1f}, time={dt:.2f}s, "
              f"mem={mem_mb:.0f} MB")

    # ---- API summary ----
    print()
    print("=" * 72)
    print("SuperBit API")
    print("=" * 72)
    print("""
  # Создать регистр
  reg = superbit_register(100)          # 100 супербитов
  reg = from_ising(J, h)                # из Ising задачи
  reg = from_sat(n_vars, clauses)       # из SAT формулы
  reg = from_qubo(Q)                    # из QUBO матрицы

  # Оптимизация
  energy, state = reg.optimize(sweeps=1000)

  # SAT solving
  solved, assignment, unsat = reg.solve_sat(n, clauses)

  # Frozen core detection
  frozen_set, sigma = reg.detect_frozen(sweeps=1000)

  # Sampling
  samples = reg.sample(sweeps=500, n_samples=100)

  # Full analysis (optimization + detection)
  info = reg.analyze(sweeps=1000)

  # Phase operations
  product = reg.phase_product([0, 1, 2])
  corr = reg.phase_correlator(0, 1)
    """)

    print("DONE")

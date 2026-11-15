#!/usr/bin/env python3
"""Four-panel real-data GIF reconstructed from the C 1.0.0 trace adapters.

Does NOT independently implement Glauber, Metropolis or n-fold physics.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

CASES = (("glauber", "standard"), ("glauber", "nfold"),
         ("metropolis", "standard"), ("metropolis", "nfold"))


@dataclass
class Trajectory:
    clocks: np.ndarray
    sites: np.ndarray
    magnetizations: np.ndarray
    energies: np.ndarray
    waits: np.ndarray
    classes: np.ndarray


def load_trace(path: Path, L: int, J: float, H: float) -> Trajectory:
    with path.open(newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    if not records or int(records[0]["clock"]) != 0:
        raise ValueError(f"Missing initial state in {path}")
    clocks = np.array([int(r["clock"]) for r in records], dtype=np.int64)
    sites = np.array([int(r["site"]) for r in records], dtype=np.int64)
    mags = np.array([int(r["M"]) for r in records], dtype=np.int64)
    energies = np.array([float(r["E"]) for r in records], dtype=float)
    waits = np.array([int(r["wait"]) for r in records], dtype=np.int64)
    classes = np.array([int(r["class"]) for r in records], dtype=np.int64)
    N = L * L
    if mags[0] != N or np.any(np.diff(clocks) <= 0):
        raise ValueError(f"Invalid initial magnetization or clock in {path}")
    if np.any((sites[1:] < 0) | (sites[1:] >= N)):
        raise ValueError(f"Invalid flip location in {path}")
    if not np.array_equal(waits[1:], np.diff(clocks)):
        raise ValueError(f"Wait values disagree with clock in {path}")
    # Verify every recorded event really is a single spin flip of the lattice.
    spins = np.ones(N, dtype=np.int8)
    energy = -2.0 * J * N - H * N
    if abs(energy - energies[0]) > 1e-7 * max(1, abs(energy)):
        raise ValueError(f"Initial energy inconsistent with Hamiltonian in {path}")
    for k in range(1, len(clocks)):
        site = int(sites[k])
        y, x = divmod(site, L)
        neighbor_sum = (int(spins[y * L + (x-1) % L]) +
                        int(spins[y * L + (x+1) % L]) +
                        int(spins[((y-1) % L) * L + x]) +
                        int(spins[((y+1) % L) * L + x]))
        energy += 2.0 * int(spins[site]) * (J * neighbor_sum + H)
        spins[site] *= -1
        if int(np.sum(spins)) != mags[k]:
            raise ValueError(f"M inconsistent with spin flips in {path}, row {k}")
        if abs(energy - energies[k]) > 1e-7 * max(1, abs(energy)):
            raise ValueError(f"E inconsistent with Hamiltonian in {path}, row {k}")
    return Trajectory(clocks, sites, mags, energies, waits, classes)


def render(args: argparse.Namespace) -> None:
    L, N = args.L, args.L * args.L
    trace_dir = Path(args.trace_root)
    traces = {case: load_trace(trace_dir / f"{case[0]}_{case[1]}.csv", L, args.J, args.H)
              for case in CASES}
    fig = plt.figure(figsize=(10.6, 10.3), dpi=args.dpi, facecolor="#f7f8fc")
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, .61],
                          left=.066, right=.96, top=.865, bottom=.10,
                          hspace=.34, wspace=.22)
    fig.suptitle("ISING 2D  |  Dinámicas y algoritmos Monte Carlo",
                 x=.5, y=.995, fontsize=17, fontweight="bold", color="#18253f")
    time_title = fig.text(.50, .947, "", ha="center", va="center",
                          fontsize=14, fontweight="bold", color="#283951")
    fig.text(.5, .906, f"L={L}  ·  T={args.T:g}  ·  J={args.J:g}  ·  H={args.H:g}  ·  espines iniciales +1",
             ha="center", fontsize=10.5, color="#607089")
    images, notes, markers = {}, {}, {}
    cmap = ListedColormap(["#2c5587", "#f9c15e"])
    for ix, case in enumerate(CASES):
        r, c = divmod(ix, 2)
        ax = fig.add_subplot(gs[r, c])
        ax.set_facecolor("white")
        img = ax.imshow(np.ones((L, L), dtype=np.int8), cmap=cmap, vmin=-1, vmax=1,
                        interpolation="nearest", origin="upper")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("#c4ccd8")
            spine.set_linewidth(1.3)
        title = f"{'Glauber / Heat-bath' if r == 0 else 'Metropolis'}   |   {'Standard' if c == 0 else 'n-fold way'}"
        ax.set_title(title, fontsize=12, fontweight="semibold", color="#1c2e4a", pad=9)
        note = ax.text(.5, -0.082, "", ha="center", va="top", transform=ax.transAxes,
                       fontsize=9.3, color="#3e4e64")
        highlight = Rectangle((-.5, -.5), 1, 1, fill=False, ec="#f43f5e", lw=2.4, visible=False)
        ax.add_patch(highlight)
        images[case], notes[case], markers[case] = img, note, highlight
    curve_ax = fig.add_subplot(gs[2, :])
    curve_ax.set_facecolor("white")
    curve_ax.set_title("Magnetización reducida  m(t) = M/N", loc="left", fontsize=12,
                       color="#1c2e4a", weight="semibold", pad=11)
    curve_ax.set_xlim(0, args.mcss)
    curve_ax.set_ylim(-.04, 1.055)
    curve_ax.set_xlabel("Tiempo Monte Carlo equivalente (MCSS = intentos / N)", fontsize=10)
    curve_ax.set_ylabel("m(t)", fontsize=10)
    curve_ax.grid(alpha=.18, linewidth=.8)
    specs = {
        ("glauber", "standard"): ("#2365a0", "Glauber · Standard", "-"),
        ("glauber", "nfold"): ("#20a29a", "Glauber · n-fold", "--"),
        ("metropolis", "standard"): ("#d86c32", "Metropolis · Standard", "-"),
        ("metropolis", "nfold"): ("#ac559c", "Metropolis · n-fold", "--"),
    }
    lines = {}
    for case, (color, label, style) in specs.items():
        (lines[case],) = curve_ax.plot([], [], color=color, lw=1.8,
                                      label=label, linestyle=style)
    time_cursor = curve_ax.axvline(0, color="#18253f", alpha=.5, ls=":")
    curve_ax.legend(fontsize=8.8, ncol=2, loc="upper right", framealpha=.94)
    fig.text(.5, .043, "Amarillo: s=+1   ·   Azul: s=-1   ·   Recuadro rojo: último espín invertido",
             ha="center", fontsize=10.2, color="#34455d")
    fig.text(.5, .017, "Todas las trayectorias son estocásticas e independientes; se detienen al alcanzar M=0.",
             ha="center", fontsize=9.1, color="#65738a")

    spin_fields = {case: np.ones(N, dtype=np.int8) for case in CASES}
    positions = {case: 0 for case in CASES}
    saved = []
    frames = np.linspace(0, args.mcss * N, args.frames, dtype=np.int64)
    for frame_ix, clock in enumerate(frames):
        t = clock / N
        time_title.set_text(f"t = {t:.2f} MCSS   ·   imagen {frame_ix+1:02d}/{len(frames):02d}")
        time_cursor.set_xdata([t, t])
        for case in CASES:
            tr = traces[case]
            target = int(np.searchsorted(tr.clocks, clock, side="right") - 1)
            spins = spin_fields[case]
            for j in range(positions[case] + 1, target + 1):
                spins[tr.sites[j]] *= -1
            positions[case] = target
            images[case].set_data(spins.reshape(L, L))
            m = tr.magnetizations[target] / N
            k = target
            method = case[1]
            if method == "standard":
                # Once the first-passage stopping condition is met, no further attempts are made.
                attempted = int(tr.clocks[-1]) if tr.magnetizations[-1] == 0 else int(clock)
                attempted = min(int(clock), attempted)
                notes[case].set_text(f"m={m:+.3f}    aceptados={k}    rechazados={attempted-k}")
            else:
                gap = int(tr.waits[k]) if k else 0
                notes[case].set_text(f"m={m:+.3f}    eventos={k}    último salto Δt={gap}")
            marker = markers[case]
            if k > 0 and tr.magnetizations[target] > 0:
                site = int(tr.sites[k]); y, x = divmod(site, L)
                marker.set_xy((x-.5, y-.5))
                marker.set_visible(True)
            else:
                marker.set_visible(False)
            # A completed trajectory remains at M=0 after its own first passage.
            ts = np.append(tr.clocks[:target+1] / N, t)
            ys = np.append(tr.magnetizations[:target+1] / N, m)
            lines[case].set_data(ts, ys)
        fig.canvas.draw()
        rgba = np.asarray(fig.canvas.buffer_rgba())
        # Consistent adaptive palette for legible typography and compact GIF.
        saved.append(Image.fromarray(rgba[..., :3].copy(), "RGB")
                         .quantize(colors=112, method=Image.Quantize.FASTOCTREE))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = round(1000 / args.fps)
    saved[0].save(output, save_all=True, append_images=saved[1:],
                  loop=0, duration=duration, disposal=2, optimize=False)
    still = output.with_suffix(".png")
    saved[len(saved) * 3 // 4].convert("RGB").save(still)
    plt.close(fig)
    print(f"GIF: {output} ({len(saved)} frames @ {args.fps} fps)")
    print(f"PNG preview: {still}")
    for case in CASES:
        tr = traces[case]
        end = tr.clocks[-1] / N
        print(f"{case[0]:10s} {case[1]:8s}: {len(tr.clocks)-1:5d} events; "
              f"last t={end:.3f}; final m={tr.magnetizations[-1]/N:+.3f}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace-root", required=True)
    p.add_argument("--L", type=int, default=32)
    p.add_argument("--T", type=float, default=1.6)
    p.add_argument("--J", type=float, default=1.0)
    p.add_argument("--H", type=float, default=-1.0)
    p.add_argument("--mcss", type=int, default=13)
    p.add_argument("--frames", type=int, default=65)
    p.add_argument("--fps", type=int, default=9)
    p.add_argument("--dpi", type=int, default=95)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    if a.L < 4 or a.L % 2 or a.frames < 2 or a.fps < 1 or a.mcss < 1:
        p.error("L must be even and >=4; frames >=2, fps>=1, mcss>=1")
    render(a)


if __name__ == "__main__":
    main()

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MARKERS=["o","s","^","D","v","P"]
LINES=["-","--","-.",":"]

def _lab(d,h): return f"{d.capitalize()}, H/J={h:g}"
def _save(base):
    plt.tight_layout(); plt.savefig(base.with_suffix(".png"),dpi=300,bbox_inches="tight"); plt.savefig(base.with_suffix(".pdf"),bbox_inches="tight"); plt.close()

def build_figures(root: Path):
    root=Path(root); main=root/"figures/final"; supp=root/"figures/supplementary"; main.mkdir(parents=True,exist_ok=True); supp.mkdir(parents=True,exist_ok=True)
    peq=pd.read_csv(root/"results/processed/physical_equivalence_8B1.csv"); perf=pd.read_csv(root/"results/processed/performance_records_8C.csv")
    campaign=pd.read_csv(root/"results/processed/campaign_repeated_records_8B2.csv"); cs=pd.read_csv(root/"results/processed/campaign_consistency_summary_8B2.csv"); pairs=pd.read_csv(root/"results/processed/dynamics_matched_pairs_8B5.csv")
    # Equivalence vs T
    d=peq[peq.study=="temperature_sweep"].copy(); plt.figure(figsize=(8.2,5.2))
    for i,((dyn,h),g) in enumerate(d.groupby(["dynamics","H"],sort=True)):
        g=g.sort_values("T"); y=g.lifetime_ratio_nfold_standard.to_numpy(); lo=g.ratio_ci95_lo.to_numpy(); hi=g.ratio_ci95_hi.to_numpy()
        plt.errorbar(g["T"],y,yerr=np.vstack([y-lo,hi-y]),marker=MARKERS[i],linestyle=LINES[i],capsize=3,label=_lab(dyn,h)); inc=g[g.equivalence_status_8b=="INCONCLUSIVE"]; plt.scatter(inc["T"],inc.lifetime_ratio_nfold_standard,marker="x",s=70) if len(inc) else None
    plt.axhline(1,linewidth=1); plt.axhspan(.95,1.05,alpha=.10); plt.xlabel(r"$T/J$"); plt.ylabel(r"$\langle\tau\rangle_{\mathrm{nfold}}/\langle\tau\rangle_{\mathrm{standard}}$"); plt.title("Physical equivalence across temperature"); plt.legend(fontsize=8); plt.grid(alpha=.2); _save(main/"fig01_equivalence_vs_temperature")
    # Equivalence vs L
    d=peq[peq.study=="scalability_L"].copy(); plt.figure(figsize=(8.2,5.2))
    for i,((dyn,h),g) in enumerate(d.groupby(["dynamics","H"],sort=True)):
        g=g.sort_values("L"); y=g.lifetime_ratio_nfold_standard.to_numpy(); lo=g.ratio_ci95_lo.to_numpy(); hi=g.ratio_ci95_hi.to_numpy(); plt.errorbar(g.L,y,yerr=np.vstack([y-lo,hi-y]),marker=MARKERS[i],linestyle=LINES[i],capsize=3,label=_lab(dyn,h))
    plt.axhline(1,linewidth=1); plt.axhspan(.95,1.05,alpha=.10); plt.xscale("log",base=2); plt.xlabel(r"$L$"); plt.ylabel(r"$\langle\tau\rangle_{\mathrm{nfold}}/\langle\tau\rangle_{\mathrm{standard}}$"); plt.title("Physical equivalence across lattice size"); plt.legend(fontsize=8); plt.grid(alpha=.2); _save(main/"fig02_equivalence_vs_size")
    # Speed-up vs T
    d=perf[perf.study=="temperature_sweep"].copy(); plt.figure(figsize=(8.2,5.2))
    for i,((dyn,h),g) in enumerate(d.groupby(["dynamics","H"],sort=True)):
        g=g.sort_values("T"); plt.plot(g["T"],g.speedup_standard_over_nfold,marker=MARKERS[i],linestyle=LINES[i],label=_lab(dyn,h))
    plt.axhline(1,linewidth=1); plt.yscale("log"); plt.xlabel(r"$T/J$"); plt.ylabel(r"Speed-up $t_{\mathrm{standard}}/t_{\mathrm{nfold}}$"); plt.title("Computational speed-up across temperature"); plt.legend(fontsize=8); plt.grid(alpha=.2); _save(main/"fig03_speedup_vs_temperature")
    # Compression vs T
    plt.figure(figsize=(8.2,5.2))
    for i,((dyn,h),g) in enumerate(d.groupby(["dynamics","H"],sort=True)):
        g=g.sort_values("T"); plt.plot(g["T"],g.nfold_equiv_attempts_per_event,marker=MARKERS[i],linestyle=LINES[i],label=_lab(dyn,h))
    plt.yscale("log"); plt.xlabel(r"$T/J$"); plt.ylabel("Equivalent standard attempts per n-fold event"); plt.title("Rejection compression across temperature"); plt.legend(fontsize=8); plt.grid(alpha=.2); _save(main/"fig04_event_compression_vs_temperature")
    # Speed-up vs L
    dl=perf[perf.study=="scalability_L"].copy(); plt.figure(figsize=(8.2,5.2))
    for i,((dyn,h),g) in enumerate(dl.groupby(["dynamics","H"],sort=True)):
        g=g.sort_values("L"); plt.plot(g.L,g.speedup_standard_over_nfold,marker=MARKERS[i],linestyle=LINES[i],label=_lab(dyn,h))
    plt.axhline(1,linewidth=1); plt.xscale("log",base=2); plt.xlabel(r"$L$"); plt.ylabel(r"Speed-up $t_{\mathrm{standard}}/t_{\mathrm{nfold}}$"); plt.title(r"Speed-up across lattice size at $T/J=1.5$"); plt.legend(fontsize=8); plt.grid(alpha=.2); _save(main/"fig05_speedup_vs_size")
    # Mechanism
    a=d[d.standard_acceptance_fraction.notna() & d.nfold_equiv_attempts_per_event.notna()].copy(); plt.figure(figsize=(6.4,5.4))
    for i,((dyn,h),g) in enumerate(a.groupby(["dynamics","H"],sort=True)): plt.scatter(1/g.standard_acceptance_fraction,g.nfold_equiv_attempts_per_event,marker=MARKERS[i],s=44,label=_lab(dyn,h))
    mn=min((1/a.standard_acceptance_fraction).min(),a.nfold_equiv_attempts_per_event.min()); mx=max((1/a.standard_acceptance_fraction).max(),a.nfold_equiv_attempts_per_event.max()); plt.plot([mn,mx],[mn,mx],linestyle="--",linewidth=1,label=r"$y=x$"); plt.xscale("log"); plt.yscale("log"); plt.xlabel(r"$1/a_{\mathrm{standard}}$"); plt.ylabel("Equivalent attempts per n-fold event"); plt.title("Mechanism check: rejection compression"); plt.legend(fontsize=8); plt.grid(alpha=.2); _save(main/"fig06_compression_vs_inverse_acceptance")
    # Supplementary campaign consistency
    cond=cs.sort_values(["dynamics","H"]); labels=[f"{r.dynamics.capitalize()}\nH/J={r.H:g}" for r in cond.itertuples()]; xb=np.arange(len(labels),dtype=float); studies=["validation","scalability_L","temperature_sweep"]; offs=[-.18,0,.18]; plt.figure(figsize=(8,5))
    for j,st in enumerate(studies):
        xs=[]; ys=[]; yl=[]; yh=[]
        for i,r in enumerate(cond.itertuples()):
            s=campaign[(campaign.experiment_id==r.experiment_id)&(campaign.study==st)]
            if len(s)==1:
                q=s.iloc[0]; xs.append(xb[i]+offs[j]); ys.append(q.lifetime_ratio_nfold_standard); yl.append(q.lifetime_ratio_nfold_standard-q.ratio_ci95_lo); yh.append(q.ratio_ci95_hi-q.lifetime_ratio_nfold_standard)
        if xs: plt.errorbar(xs,ys,yerr=np.vstack([yl,yh]),fmt=MARKERS[j],capsize=3,label=st)
    plt.axhline(1,linewidth=1); plt.axhspan(.95,1.05,alpha=.10); plt.xticks(xb,labels); plt.ylabel(r"$\langle\tau\rangle_{\mathrm{nfold}}/\langle\tau\rangle_{\mathrm{standard}}$"); plt.title("Internal reproducibility across independent campaigns"); plt.legend(fontsize=8); plt.grid(alpha=.2,axis="y"); _save(supp/"figS01_campaign_consistency")
    # Supplementary dynamics contrast
    plt.figure(figsize=(6.2,5.4)); plt.scatter(pairs.tau_glauber_over_metropolis_standard,pairs.tau_glauber_over_metropolis_nfold,s=42); mn=min(pairs.tau_glauber_over_metropolis_standard.min(),pairs.tau_glauber_over_metropolis_nfold.min()); mx=max(pairs.tau_glauber_over_metropolis_standard.max(),pairs.tau_glauber_over_metropolis_nfold.max()); plt.plot([mn,mx],[mn,mx],linestyle="--",linewidth=1); plt.xlabel(r"$\tau_G/\tau_M$ — Standard"); plt.ylabel(r"$\tau_G/\tau_M$ — n-fold"); plt.title("Preservation of the Glauber/Metropolis dynamical contrast"); plt.grid(alpha=.2); _save(supp/"figS02_dynamic_contrast_preservation")

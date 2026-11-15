# Scientific background

## Kinetic Ising model

For a square lattice with nearest-neighbour ferromagnetic coupling,

\[
\mathcal H=-J\sum_{\langle i,j\rangle}s_i s_j-H\sum_i s_i,
\qquad J>0,\qquad s_i=\pm1.
\]

Flipping one spin changes the energy by

\[
\Delta E_i=2s_i\left(J\sum_{j\in nn(i)}s_j+H\right).
\]

The project studies **metastable escape**, not generic equilibrium sampling. The initial condition is all spins `+1`; for negative field this configuration can be metastable below the critical region. The observable of interest is the first-passage time \(\tau\) to total magnetization \(M=0\).

## Why random single-site updates matter

A sequential lattice sweep and a uniformly random single-site update can produce the same equilibrium distribution under suitable conditions, but they do not define the same microscopic stochastic dynamics. Because the n-fold way is intended here as an acceleration of a kinetic single-spin process, the Standard reference must use the **same random-site dynamics** that n-fold reorganizes.

## Glauber and Metropolis dynamics

For reduced units with \(k_B=1\):

### Glauber / heat-bath

\[
p_{\rm G}(\Delta E)=\frac{1}{1+e^{\Delta E/T}}.
\]

### Metropolis

\[
p_{\rm M}(\Delta E)=\min\left(1,e^{-\Delta E/T}\right).
\]

These are different stochastic dynamics. The project therefore checks n-fold against each Standard reference separately rather than pooling Glauber and Metropolis into a single law.

## n-fold way

On the square lattice every spin belongs to one of ten local classes determined by its orientation and the number of neighbouring up spins. All spins in a class share the same local flip probability. The n-fold method samples among classes weighted by their total escape rate and advances time by a rejection-free waiting-time construction.

The key conceptual point is that n-fold does not obtain its speed-up by changing the target kinetic law. It reorganizes the same random-update dynamics so that long sequences of rejected attempts are represented implicitly.

## Time variables

Three quantities must remain distinct:

- `time_mcss`: represented Monte Carlo time per spin;
- `events`: executed rejection-free n-fold events;
- `cpu_seconds`: real computational cost.

They answer different questions and must never be used interchangeably.

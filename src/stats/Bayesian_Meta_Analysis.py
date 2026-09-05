
import json
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from datetime import datetime
import os
import sys
from pathlib import Path

# Configuration
INPUT_FILE = "results/bio/null_stats.json"
OUTPUT_DIR = "results/stats"
# AUDIT03 (monolithic-code): _repo_root, _paper_root and _paper_figures_dir
# were defined identically here and in three other production modules. One
# owner now; parity proven over 24 of 24 comparisons before this edit
# (audit/AUDIT03_R2_collapse/probe_paths_parity.py). Guarded by
# tools/check_single_engine.sh.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from causalbool_paths import paper_figures_dir as _paper_figures_dir  # noqa: E402
# repo_root and paper_root were imported here too and never used -- residue of
# the collapse, which replaced three local definitions with three imports rather
# than with the one this module actually calls.


FIGURE_DIR = os.getenv("BAYES_FIGURE_DIR", str(_paper_figures_dir()))
SEED = 42
CHAINS = 4
DRAWS = 5000
TUNE = 1000

np.random.seed(SEED)

def load_data(filepath):
    print(f"[{datetime.now()}] Loading data from {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    z_scores = []
    networks = []
    for entry in data:
        z = entry.get('z_deg')
        if z is not None and np.isfinite(z):
            z_scores.append(z)
            networks.append(entry.get('network'))
    
    print(f"[{datetime.now()}] Loaded {len(z_scores)} valid Z-scores.")
    return np.array(z_scores), networks

# Bayesian Model Definition
# Likelihood: y ~ Normal(mu, sigma)
# Prior: mu ~ Normal(0, 10)
# Prior: sigma ~ HalfNormal(5)

def log_prior(mu, sigma):
    if sigma <= 0:
        return -np.inf
    # mu ~ Normal(0, 10)
    lp_mu = -0.5 * (mu / 10)**2 - np.log(10 * np.sqrt(2 * np.pi))
    # sigma ~ HalfNormal(5) -> 2 * Normal(0, 5) restricted to > 0
    lp_sigma = -0.5 * (sigma / 5)**2 - np.log(5 * np.sqrt(2 * np.pi)) + np.log(2)
    return lp_mu + lp_sigma

def log_likelihood(y, mu, sigma):
    if sigma <= 0:
        return -np.inf
    n = len(y)
    # y ~ Normal(mu, sigma)
    # Sum of log pdfs
    return -n * np.log(sigma * np.sqrt(2 * np.pi)) - 0.5 * np.sum(((y - mu) / sigma)**2)

def log_posterior(mu, sigma, y):
    lp = log_prior(mu, sigma)
    if not np.isfinite(lp):
        return -np.inf
    ll = log_likelihood(y, mu, sigma)
    return lp + ll

def metropolis_sampler(y, draws=5000, tune=1000, chains=4, initial_params=None):
    print(f"[{datetime.now()}] Starting Metropolis-Hastings sampler ({chains} chains, {draws} draws)...")
    
    traces = []
    
    for chain in range(chains):
        print(f"  Chain {chain+1}/{chains}...")
        # Initialize
        if initial_params:
            current_mu, current_sigma = initial_params
        else:
            current_mu = np.random.normal(0, 1)
            current_sigma = np.abs(np.random.normal(0, 1)) + 0.1
            
        current_logprob = log_posterior(current_mu, current_sigma, y)
        
        chain_samples = np.zeros((draws + tune, 2))
        accepted = 0
        accepted_sampling = 0   # counted only after tuning, so the reported
                                # rate describes the chain that was kept
        
        # AUDIT03-C. This read "Simple adaptive: standard deviation of recent
        # samples" above a fixed literal that was never reassigned. The block
        # below labelled "Adaptation during tuning" computed an acceptance rate
        # and discarded it, with its only print commented out -- which is why
        # ruff F841 was the thing that found this. The sampler was a FIXED-scale
        # random walk describing itself as adaptive.
        #
        # Measured before the fix: acceptance 0.18-0.20 across four chains,
        # against the ~0.44 optimum for a 2-parameter random-walk Metropolis
        # (Roberts, Gelman & Gilks 1997). Convergence was never in doubt --
        # R-hat 1.0014/1.0003 -- so this was an efficiency defect, not a wrong
        # posterior. The proposal was simply too wide.
        #
        # Adaptation runs during TUNING ONLY and is frozen before the retained
        # draws begin. Adapting while sampling would make the chain
        # non-Markovian and void the stationary distribution, which is the
        # standard trap here.
        prop_sd = np.array([0.5, 0.5])
        target_acc = 0.44
        adapt_every = 100
        accepted_window = 0
        
        for i in range(draws + tune):
            # Propose new mu
            prop_mu = current_mu + np.random.normal(0, prop_sd[0])
            prop_sigma = current_sigma + np.random.normal(0, prop_sd[1])
            
            # Reject if sigma <= 0 immediately
            if prop_sigma <= 0:
                prop_logprob = -np.inf
            else:
                prop_logprob = log_posterior(prop_mu, prop_sigma, y)
            
            # Acceptance ratio
            if prop_logprob > -np.inf:
                ratio = prop_logprob - current_logprob
                if np.log(np.random.rand()) < ratio:
                    current_mu = prop_mu
                    current_sigma = prop_sigma
                    current_logprob = prop_logprob
                    accepted += 1
                    accepted_window += 1
                    if i >= tune:
                        accepted_sampling += 1

            chain_samples[i] = [current_mu, current_sigma]

            # Adaptation during tuning, then frozen.
            if i < tune and i % adapt_every == 0 and i > 0:
                window_rate = accepted_window / adapt_every
                # Multiplicative Robbins-Monro style step on the log scale:
                # above target -> widen, below target -> narrow. Bounded so a
                # pathological window cannot collapse or explode the proposal.
                prop_sd = prop_sd * float(np.clip(
                    np.exp(window_rate - target_acc), 0.8, 1.25))
                prop_sd = np.clip(prop_sd, 1e-3, 1e3)
                accepted_window = 0

        acc_sampling = accepted_sampling / draws
        print(f"  Chain {chain+1} finished. Acceptance Rate: "
              f"{accepted/(draws+tune):.2f} overall, {acc_sampling:.2f} on the "
              f"retained draws (target {target_acc}); "
              f"final proposal sd [{prop_sd[0]:.3f}, {prop_sd[1]:.3f}]")
        traces.append(chain_samples[tune:])
        
    return np.array(traces)

def gelman_rubin(traces):
    """
    Compute R-hat for each parameter.
    traces shape: (chains, draws, params)
    """
    m, n, p = traces.shape
    
    # Calculate means
    chain_means = np.mean(traces, axis=1) # (m, p)
    grand_mean = np.mean(chain_means, axis=0) # (p,)
    
    # Between-chain variance B
    B = n / (m - 1) * np.sum((chain_means - grand_mean)**2, axis=0)
    
    # Within-chain variance W
    chain_vars = np.var(traces, axis=1, ddof=1) # (m, p)
    W = np.mean(chain_vars, axis=0)
    
    # Var_hat
    var_plus = (n - 1) / n * W + B / n
    
    # R-hat
    r_hat = np.sqrt(var_plus / W)
    return r_hat

def effective_sample_size(traces):
    """
    Simple ESS approximation using autocorrelation
    """
    # Combine chains
    combined = traces.reshape(-1, traces.shape[2])
    n = len(combined)
    
    ess = []
    for p in range(traces.shape[2]):
        series = combined[:, p]
        # Compute autocorrelation
        # Using fft for speed
        ft = np.fft.fft(series - np.mean(series))
        acf = np.fft.ifft(ft * np.conjugate(ft)).real
        acf = acf / acf[0]
        
        # Sum of ACF until it drops below 0.05 or becomes negative
        sum_rho = 0
        for rho in acf[1:]:
            if rho < 0.05:
                break
            sum_rho += rho
            
        tau = 1 + 2 * sum_rho
        ess.append(n / tau)
        
    return np.array(ess)

def plot_results(traces, y_data):
    # Flatten chains for plotting posterior
    flat_mu = traces[:, :, 0].flatten()
    flat_sigma = traces[:, :, 1].flatten()
    
    # Trace Plot
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    
    # Mu Trace
    for c in range(traces.shape[0]):
        axes[0, 0].plot(traces[c, :, 0], alpha=0.5, label=f'Chain {c}')
    axes[0, 0].set_title(r'Trace of $\mu$')
    axes[0, 0].set_ylabel(r'$\mu$')
    axes[0, 0].legend()
    
    # Sigma Trace
    for c in range(traces.shape[0]):
        axes[1, 0].plot(traces[c, :, 1], alpha=0.5)
    axes[1, 0].set_title(r'Trace of $\sigma$')
    axes[1, 0].set_ylabel(r'$\sigma$')
    
    # Mu Posterior
    axes[0, 1].hist(flat_mu, bins=50, density=True, color='skyblue', edgecolor='black', alpha=0.7)
    axes[0, 1].axvline(np.mean(flat_mu), color='red', linestyle='--')
    axes[0, 1].set_title(r'Posterior of $\mu$')
    
    # Sigma Posterior
    axes[1, 1].hist(flat_sigma, bins=50, density=True, color='orange', edgecolor='black', alpha=0.7)
    axes[1, 1].axvline(np.mean(flat_sigma), color='red', linestyle='--')
    axes[1, 1].set_title(r'Posterior of $\sigma$')
    
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, "bayesian_trace.png"))
    print(f"[{datetime.now()}] Saved trace plot.")
    
    # Posterior Predictive Check
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(y_data, bins=30, density=True, alpha=0.5, label='Observed Data', color='gray')
    
    # Generate predictive samples
    x_range = np.linspace(min(y_data)-5, max(y_data)+5, 100)
    # (An empty `ppc_samples` list was collected here and never appended to or
    # read. The check itself is real -- 100 posterior draws are plotted below.)
    for _ in range(100):
        idx = np.random.randint(len(flat_mu))
        m = flat_mu[idx]
        s = flat_sigma[idx]
        pdf = stats.norm.pdf(x_range, m, s)
        ax.plot(x_range, pdf, 'k-', alpha=0.1)
        
    ax.plot(x_range, stats.norm.pdf(x_range, np.mean(flat_mu), np.mean(flat_sigma)), 'r-', linewidth=2, label='Mean Posterior')
    ax.set_title("Posterior Predictive Check")
    ax.legend()
    plt.savefig(os.path.join(FIGURE_DIR, "bayesian_ppc.png"))
    print(f"[{datetime.now()}] Saved PPC plot.")

def main():
    # Load Data
    z_scores, networks = load_data(INPUT_FILE)
    
    # Run MCMC
    traces = metropolis_sampler(z_scores, draws=DRAWS, tune=TUNE, chains=CHAINS)
    
    # Diagnostics
    r_hat = gelman_rubin(traces)
    ess = effective_sample_size(traces)
    
    print("\nDiagnostics:")
    print(f"  R-hat (mu, sigma): {r_hat}")
    print(f"  ESS (mu, sigma): {ess}")
    
    # Statistics
    flat_mu = traces[:, :, 0].flatten()
    flat_sigma = traces[:, :, 1].flatten()
    
    mean_mu = np.mean(flat_mu)
    hdi_mu = np.percentile(flat_mu, [2.5, 97.5])
    prob_pos = np.mean(flat_mu > 0)
    
    print("\nPosterior Summary:")
    print(f"  Mu: {mean_mu:.3f} [{hdi_mu[0]:.3f}, {hdi_mu[1]:.3f}]")
    print(f"  P(Mu > 0): {prob_pos:.4f}")
    
    # Save Results
    results = {
        "n_samples": len(z_scores),
        "mu_mean": float(mean_mu),
        "mu_hdi_95": [float(hdi_mu[0]), float(hdi_mu[1])],
        "sigma_mean": float(np.mean(flat_sigma)),
        "prob_positive": float(prob_pos),
        "r_hat": [float(r) for r in r_hat],
        "ess": [float(e) for e in ess],
        "timestamp": datetime.now().isoformat()
    }
    
    with open(os.path.join(OUTPUT_DIR, "bayesian_summary.json"), 'w') as f:
        json.dump(results, f, indent=2)
        
    # Plotting
    plot_results(traces, z_scores)
    
    print(f"[{datetime.now()}] Analysis Complete.")

if __name__ == "__main__":
    main()

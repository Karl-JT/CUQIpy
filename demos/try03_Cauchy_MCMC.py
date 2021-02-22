# =============================================================================
# Created by:
# Felipe Uribe @ DTU
# =============================================================================
# Version 2020-10
# =============================================================================
import sys
sys.path.append("../")
import time
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

# myfuns
import cuqi

# =============================================================================
# set-up the discrete convolution model
# =============================================================================
test = cuqi.TestProblem.Deblur()
n = test.dim
tt = test.t

# =============================================================================
# data and noise
# =============================================================================
# compute truth and noisy convolved data
norm_f = np.linalg.norm(test.f_true)

# Gaussian likelihood params
b = test.data
m = len(b)                             # number of data points
likelihood = cuqi.Distribution.Gaussian(test.forward, test.sigma_obs, test.corrmat)
def likelihood_logpdf(x): return likelihood.logpdf(b, x)

# =============================================================================
# prior
# =============================================================================
loc = np.zeros(n)
delta = 1
scale = delta*test.h
prior = cuqi.Distribution.Cauchy_diff(loc, scale, 'neumann')
def prior_logpdf(x): return prior.logpdf(x)

# =============================================================================
# posterior sampling
# =============================================================================
def target(x): return likelihood_logpdf(x) + prior_logpdf(x)
def proposal(x_t, sigma): return np.random.normal(x_t, sigma)
scale = 0.05*np.ones(n)
x0 = 0.5*np.ones(n)
MCMC = cuqi.Sampler.CWMH(target, proposal, scale, x0)
# MCMC = cuqi.Sampler.RWMH(target, proposal, scale, x0)

# run sampler
Ns = int(5e3)      # number of samples
Nb = int(0.2*Ns)   # burn-in
#
ti = time.time()
x_s, target_eval, acc = MCMC.sample_adapt(Ns, Nb)
print('Elapsed time:', time.time() - ti)

# =============================================================================
med_xpos = np.median(x_s, axis=1) # sp.stats.mode
sigma_xpos = x_s.std(axis=1)
lo95, up95 = np.percentile(x_s, [2.5, 97.5], axis=1)
relerr = round(np.linalg.norm(med_xpos - test.f_true)/norm_f*100, 2)
print('\nRelerror median:', relerr, '\n')

# =============================================================================
# plots
# =============================================================================
plt.figure()
plt.plot(tt, test.f_true, 'k-')
plt.plot(tt, test.g_true, 'b-')
plt.plot(tt, b, 'r.')
plt.tight_layout()

plt.figure()
plt.plot(target_eval[Nb:])
plt.xlabel('Sample index')
plt.ylabel('Target function values')
plt.tight_layout()

plt.figure()
plt.plot(tt, test.f_true, '-', color='forestgreen', linewidth=3, label='True')
plt.plot(tt, med_xpos, '--', color='crimson', label='median')
plt.fill_between(tt, up95, lo95, color='dodgerblue', alpha=0.25)
plt.legend(loc='upper right', shadow=False, ncol = 1, fancybox=True, prop={'size':15})
plt.xticks(np.linspace(tt[0], tt[-1], 5))
plt.xlim([tt[0], tt[-1]])
plt.ylim(-0.5, 3.5)
plt.tight_layout()
# plt.savefig('fig.png', format='png', dpi=150, bbox_inches='tight')
plt.show()
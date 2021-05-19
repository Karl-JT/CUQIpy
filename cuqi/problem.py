import cuqi
import numpy as np
import time


from cuqi.distribution import Cauchy_diff, Laplace_diff, Gaussian, GMRF
from cuqi.model import LinearModel

class Generic(object):
    def __init__(self):
        raise NotImplementedError

class BayesianModel(object):
    """
    Bayesian representation of inverse problem represented by likelihood and prior

    Attributes
    ----------
        `likelihood: cuqi.model.Distribution`:
            summary: 'The likelihood distribution'
            example: model = cuqi.model.LinearModel(A)
                     likelihood = cuqi.distribution.Gaussian(model, std, corrmat)
        `prior: cuqi.model.Distribution`:
            summary: 'A cuqi distribution for the prior'
            example: cuqi.distribution.Gaussian(mean, std, corrmat)
        `model: cuqi.model.Model`:
            summary: 'A cuqi forward model (optional)'
            example: cuqi.model.LinearModel(A) #A is a matrix

    Methods
    ----------
        `MAP()`:
            summary: 'Compute MAP estimate of the inverse problem.'
            NB: 'Requires the prior to be defined.'
        `Sample(Ns)`:
            summary: 'Sample Ns samples of the inverse problem.'
            NB: 'Requires the prior to be defined.'
    """
    def __init__(self,likelihood,prior,model=None,data=None):
        self.likelihood = likelihood
        self.prior = prior
        self.model = model
        self.data = data

    def MAP(self):
        """MAP computed the MAP estimate of the posterior"""
        if self._check(Gaussian,Gaussian,LinearModel):
            b  = self.data
            A  = self.model.get_matrix()
            Ce = self.likelihood.Sigma
            x0 = self.prior.mean
            Cx = self.prior.Sigma

            #Basic map estimate using closed-form expression Tarantola 2005 (3.37-3.38)
            rhs = b-A@x0
            sysm = A@Cx@A.T+Ce
            
            return x0 + Cx@(A.T@np.linalg.solve(sysm,rhs))

        #If no implementation exists give error
        else:
            raise NotImplementedError(f'MAP estimate is not implemented in Type1 problem for model: {type(self.model)}, likelihood: {type(self.likelihood)} and prior: {type(self.prior)}. Check documentation for available combinations.')

    def sample_posterior(self,Ns):
        """Sample Ns samples of the posterior given data"""

        if self._check(Gaussian,Gaussian,LinearModel) and not self._check(Gaussian,GMRF):
            return self._sampleMapCholesky(Ns)

        elif self._check(Gaussian,Cauchy_diff) or self._check(Gaussian,Laplace_diff):
            return self._sampleCWMH(Ns)

        elif self._check(Gaussian,Gaussian):
            return self._samplepCN(Ns)

        else:
            raise NotImplementedError(f'Sampler is not implemented in Type1 problem for model: {type(self.model)}, likelihood: {type(self.likelihood)} and prior: {type(self.prior)}. Check documentation for available combinations.')

    def UQ(self,exact=None):
        print("Computing 5000 samples")
        samples = self.sample_posterior(5000)

        print("Plotting 95 percent confidence interval")
        if exact is not None:
            samples.plot_ci(95,exact=exact)
        elif hasattr(self,"exactSolution"):
            samples.plot_ci(95,exact=self.exactSolution)
        else:
            samples.plot_ci(95)

    def _check(self,distL,distP,typeModel=None):
        L = isinstance(self.likelihood,distL)
        P = isinstance(self.prior,distP)
        if typeModel is None:
            M = True
        else:
            M = isinstance(self.model,typeModel)
        return L and P and M

    def _sampleMapCholesky(self,Ns):
        # Start timing
        ti = time.time()

        b  = self.data
        A  = self.model.get_matrix()
        Ce = self.likelihood.Sigma
        x0 = self.prior.mean
        Cx = self.prior.Sigma

        # Preallocate samples
        n = self.prior.dim 
        x_s = np.zeros((n,Ns))

        x_map = self.MAP() #Compute MAP estimate
        C = np.linalg.inv(A.T@(np.linalg.inv(Ce)@A)+np.linalg.inv(Cx))
        L = np.linalg.cholesky(C)
        for s in range(Ns):
            x_s[:,s] = x_map + L@np.random.randn(n)
            # display iterations 
            if (s % 5e2) == 0:
                print("\r",'Sample', s, '/', Ns, end="")

        print("\r",'Sample', s+1, '/', Ns)
        print('Elapsed time:', time.time() - ti)
        
        return cuqi.samples.Samples(x_s)
    
    def _sampleCWMH(self,Ns):
        # Dimension
        n = self.prior.dim
        
        # Set up target and proposal
        def target(x): return self.likelihood.logpdf(self.data,x) + self.prior.logpdf(x) #ToDo: Likelihood should only depend on x (not data)
        def proposal(x_t, sigma): return np.random.normal(x_t, sigma)

        # Set up sampler
        scale = 0.05*np.ones(n)
        x0 = 0.5*np.ones(n)
        MCMC = cuqi.sampler.CWMH(target, proposal, scale, x0)
        
        # Run sampler
        Nb = int(0.2*Ns)   # burn-in
        ti = time.time()
        x_s, target_eval, acc = MCMC.sample_adapt(Ns,Nb); #ToDo: Make results class
        print('Elapsed time:', time.time() - ti)
        
        return cuqi.samples.Samples(x_s)

    def _samplepCN(self,Ns):
        # Dimension
        n = self.prior.dim
        
        # Set up target and proposal
        def target(x): return self.likelihood.logpdf(self.data,x) #ToDo: Likelihood should only depend on x (not data)
        #def proposal(ns): return self.prior.sample(ns)
        
        scale = 0.02
        x0 = np.zeros(n)
        
        #ToDO: Switch to pCN
        MCMC = cuqi.sampler.pCN(self.prior,target,scale,x0)
        
        
        #TODO: Select burn-in 
        #Nb = int(0.25*Ns)   # burn-in

        #Run sampler
        ti = time.time()
        x_s, target_eval, acc = MCMC.sample(Ns,0) #ToDo: fix sampler input
        print('Elapsed time:', time.time() - ti)
        
        return cuqi.samples.Samples(x_s)

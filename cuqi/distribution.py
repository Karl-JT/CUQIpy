import numpy as np
import scipy.stats as sps
from scipy.special import erf, loggamma, gammainc
from scipy.sparse import diags, spdiags, eye, kron, vstack
from scipy.sparse import linalg as splinalg
from scipy.linalg import eigh, dft, eigvalsh, pinvh

# import sksparse
# from sksparse.cholmod import cholesky
eps = np.finfo(float).eps

# ========================================================================
class Cauchy_diff(object):

    def __init__(self, location, scale, bndcond):
        self.loc = location
        self.scale = scale
        self.dim = len(location)
        self.bnd = bndcond

        # finite difference matrix
        one_vec = np.ones(self.dim)
        diags = np.vstack([-one_vec, one_vec])
        if (bndcond == 'zero'):
            locs = [-1, 0]
            Dmat = spdiags(diags, locs, self.dim+1, self.dim)
        elif (bndcond == 'periodic'):
            locs = [-1, 0]
            Dmat = spdiags(diags, locs, self.dim+1, self.dim).tocsr()
            Dmat[-1, 0] = 1
            Dmat[0, -1] = -1
        elif (bndcond == 'neumann'):
            locs = [0, 1]
            Dmat = spdiags(diags, locs, self.dim-1, self.dim)
        elif (bndcond == 'backward'):
            locs = [0, -1]
            Dmat = spdiags(diags, locs, self.dim, self.dim).tocsr()
            Dmat[0, 0] = 1
        elif (bndcond == 'none'):
            Dmat = eye(self.dim)
        self.D = Dmat

    def pdf(self, x):
        Dx = self.D @ (x-self.loc)
        return (1/(np.pi**len(Dx))) * np.prod(self.scale/(Dx**2 + self.scale**2))

    def logpdf(self, x):
        Dx = self.D @ (x-self.loc)
        # g_logpr = (-2*Dx/(Dx**2 + gamma**2)) @ D
        return -len(Dx)*np.log(np.pi) + sum(np.log(self.scale) - np.log(Dx**2 + self.scale**2))
    
    # def cdf(self, x):   # TODO
    #     return 1/np.pi * np.atan((x-self.loc)/self.scale)

    # def sample(self):   # TODO
    #     return self.loc + self.scale*np.tan(np.pi*(np.random.rand(self.dim)-1/2))


# ========================================================================
class Normal(object):
    """
    Normal probability distribution. Generates instance of cuqi.distribution.Normal

    
    Parameters
    ------------
    mean: mean of distribution
    std: standard deviation
    
    Methods
    -----------
    sample: generate one or more random samples
    pdf: evaluate probability density function
    logpdf: evaluate log probability density function
    cdf: evaluate cumulatiuve probability function
    
    Example
    -----------
    #Generate Normal with mean 2 and standard deviation 1
    p = cuqi.distribution.Normal(mean=2, std=1)
    """
    def __init__(self, mean, std):
        self.mean = mean
        self.std = std        
        self.dim = np.size(mean)

    def pdf(self, x):
        return 1/(self.std*np.sqrt(2*np.pi))*np.exp(-0.5*((x-self.mean)/self.std)**2)

    def logpdf(self, x):
        return -np.log(self.std*np.sqrt(2*np.pi))-0.5*((x-self.mean)/self.std)**2

    def cdf(self, x):
        return 0.5*(1 + erf((x-self.mean)/(self.std*np.sqrt(2))))

    def sample(self,N=1):
        """
        Draw sample(s) from distrubtion
        
        Example
        -------
        p = cuqi.distribution.Normal(mean=2, std=1) #Define distribution
        s = p.sample() #Sample from distribution
        

        Returns
        -------
        Generated sample(s)

        """
        
        return np.random.normal(self.mean, self.std, (N,self.dim))


# ========================================================================
class Gamma(object):

    def __init__(self, shape, rate):
        self.shape = shape
        self.rate = rate
        self.scale = 1/rate

    def pdf(self, x):
        # sps.gamma.pdf(x, a=self.shape, loc=0, scale=self.scale)
        # (self.rate**self.shape)/(gamma(self.shape)) * (x**(self.shape-1)*np.exp(-self.rate*x))
        return np.exp(self.logpdf(x))

    def logpdf(self, x):
        # sps.gamma.logpdf(x, a=self.shape, loc=0, scale=self.scale)
        return (self.shape*np.log(self.rate)-loggamma(self.shape)) + ((self.shape-1)*np.log(x) - self.rate*x)

    def cdf(self, x):
        # sps.gamma.cdf(x, a=self.shape, loc=0, scale=self.scale)
        return gammainc(self.shape, self.rate*x)

    def sample(self, N):
        return np.random.gamma(shape=self.shape, scale=self.scale, size=(N))


# ========================================================================
class Gaussian(object):

    def __init__(self, mean, std, corrmat):
        self.mean = mean
        self.std = std
        self.R = corrmat
        self.dim = len(np.diag(corrmat))
        # self = sps.multivariate_normal(mean, (std**2)*corrmat)

        # pre-computations (covariance and determinants)
        if isinstance(std, (list, tuple, np.ndarray)):
            self.Sigma = np.diag(std) @ (corrmat @ np.diag(std))   # covariance
            isdiag = np.count_nonzero(corrmat - np.diag(np.diagonal(corrmat)))
            if (isdiag == 0):    # uncorrelated
                self.det = np.prod(std**2)
                self.logdet = sum(2*np.log(std))
                self.L = np.linalg.cholesky(self.Sigma)
            else:
                self.det = np.linalg.det(self.Sigma)
                self.L = np.linalg.cholesky(self.Sigma)
                self.logdet = 2*sum(np.log(np.diag(self.L)))  # only for PSD matrices
        else:
            self.Sigma = np.diag(std*np.ones(self.dim)) @ (corrmat @ np.diag(std*np.ones(self.dim)))   # covariance
            isdiag = np.count_nonzero(corrmat - np.diag(np.diagonal(corrmat)))
            if (isdiag == 0):   # uncorrelated
                self.det = std**(2*self.dim)
                self.logdet = 2*self.dim*np.log(std)
                self.L = np.linalg.cholesky(self.Sigma)
            else:
                self.det = std**(2*self.dim) * np.linalg.det(corrmat)
                self.L = np.linalg.cholesky(self.Sigma)
                self.logdet = 2*sum(np.log(np.diag(self.L)))  # only for PSD matrices

        # inverse of Cholesky
        self.Linv = np.linalg.inv(self.L)

        # Compute decomposition such that Q = U @ U.T
        # self.Q = np.linalg.inv(self.Sigma)   # precision matrix
        # s, u = eigh(self.Q, lower=True, check_finite=True)
        # s_pinv = np.array([0 if abs(x) <= 1e-5 else 1/x for x in s], dtype=float)
        # self.U = u @ np.diag(np.sqrt(s_pinv))

    def logpdf(self, x1, *x2):
        if callable(self.mean):
            mu = self.mean(x2[0])   # mean is variable
        else:
            mu = self.mean       # mean is fix
        xLinv = (x1 - mu) @ self.Linv.T
        quadform = np.sum(np.square(xLinv), 1) if (len(xLinv.shape) > 1) else np.sum(np.square(xLinv))
        # = sps.multivariate_normal.logpdf(x1, mu, self.Sigma)
        return -0.5*(self.logdet + quadform + self.dim*np.log(2*np.pi))

    def pdf(self, x1, *x2):
        # = sps.multivariate_normal.pdf(x1, self.mean, self.Sigma)
        return np.exp(self.logpdf(x1, *x2))

    def cdf(self, x1):   # TODO
        return sps.multivariate_normal.cdf(x1, self.mean, self.Sigma)

    def sample(self, N):   # TODO

        return np.random.multivariate_normal(self.mean, self.Sigma, N).T



# ========================================================================
class GMRF(Gaussian):
        
    def __init__(self, mean, prec, N, dom, BCs):
        self.mean = mean.reshape(len(mean), 1)
        self.prec = prec
        self.N = N          # partition size
        self.BCs = BCs      # boundary conditions
        
        # BCs: 1D difference matrix 
        one_vec = np.ones(N)
        dgn = np.vstack([-one_vec, one_vec])
        if (BCs == 'zero'):
            locs = [-1, 0]
            Dmat = spdiags(dgn, locs, N+1, N).tocsc()
        elif (BCs == 'periodic'):
            locs = [-1, 0]
            Dmat = spdiags(dgn, locs, N+1, N).tocsc()
            Dmat[-1, 0] = 1
            Dmat[0, -1] = -1
        elif (BCs == 'neumann'):
            locs = [0, 1]
            Dmat = spdiags(dgn, locs, N, N).tocsc()
            Dmat[-1, -1] = 0
        elif (BCs == 'none'):
            Dmat = eye(N, dtype=int)
        else:
            raise TypeError('Unexpected BC type (choose from zero, periodic, neumann or none)')
        
        # structure matrix
        if (dom == 1):
            self.dim = N
            self.D = Dmat
            self.L = (Dmat.T @ Dmat).tocsc()
        elif (dom == 2):            
            self.dim = N**2
            I = eye(N, dtype=int)
            Ds = kron(I, Dmat)
            Dt = kron(Dmat, I)
            self.D = vstack([Ds, Dt])
            self.L = ((Ds.T @ Ds) + (Dt.T @ Dt)).tocsc()
            
        # work-around to compute sparse Cholesky
        def sparse_cholesky(A):
            # https://gist.github.com/omitakahiro/c49e5168d04438c5b20c921b928f1f5d
            LU = splinalg.splu(A, diag_pivot_thresh=0, permc_spec='natural') # sparse LU decomposition
  
            # check the matrix A is positive definite
            if (LU.perm_r == np.arange(self.dim)).all() and (LU.U.diagonal() > 0).all(): 
                return LU.L @ (diags(LU.U.diagonal()**0.5))
            else:
                raise TypeError('The matrix is not positive semi-definite')
        
        # compute Cholesky and det
        if (BCs == 'zero'):    # only for PSD matrices
            self.rank = self.dim
            self.chol = sparse_cholesky(self.L)
            self.logdet = 2*sum(np.log(self.chol.diagonal()))
            # L_cholmod = cholesky(self.L, ordering_method='natural')
            # self.chol = L_cholmod
            # self.logdet = L_cholmod.logdet()
            # 
            # np.log(np.linalg.det(self.L.todense()))
        elif (BCs == 'periodic') or (BCs == 'neumann'):
            self.rank = self.dim - 1   #np.linalg.matrix_rank(self.L.todense())
            self.chol = sparse_cholesky(self.L + np.sqrt(eps)*eye(self.dim, dtype=int))
            if (self.dim > 5000):  # approximate to avoid 'excesive' time
                self.logdet = 2*sum(np.log(self.chol.diagonal()))
            else:
                # eigval = eigvalsh(self.L.todense())
                self.L_eigval = splinalg.eigsh(self.L, self.rank, which='LM', return_eigenvectors=False)
                self.logdet = sum(np.log(self.L_eigval))

    def logpdf(self, x):
        const = 0.5*(self.rank*(np.log(self.prec)-np.log(2*np.pi)) + self.logdet)
        y = const - 0.5*( self.prec*((x-self.mean).T @ (self.L @ (x-self.mean))) )
        y = np.diag(y)
        # = sps.multivariate_normal.logpdf(x.T, self.mean.flatten(), np.linalg.inv(self.prec*self.L.todense()))
        return y

    def pdf(self, x):
        # = sps.multivariate_normal.pdf(x.T, self.mean.flatten(), np.linalg.inv(self.prec*self.L.todense()))
        return np.exp(self.logpdf(x))

    def sample(self, Ns):
        if (self.BCs == 'zero'):
            xi = np.random.randn(self.dim, Ns)   # standard Gaussian
            s = self.mean + (1/np.sqrt(self.prec))*splinalg.spsolve(self.chol.T, xi)
            # s = self.mean + (1/np.sqrt(self.prec))*L_cholmod.solve_Lt(xi, use_LDLt_decomposition=False) 
                        
        elif (self.BCs == 'periodic'):
            xi = np.random.randn(self.dim, Ns) + 1j*np.random.randn(self.dim, Ns) 
            F = dft(self.dim, scale='sqrtn')   # unitary DFT matrix
            # eigv = eigvalsh(self.L.todense()) # splinalg.eigsh(self.L, self.rank, return_eigenvectors=False)           
            eigv = np.hstack([self.L_eigval, self.L_eigval[-1]])  # repeat last eigval to complete dim
            L_sqrt = diags(np.sqrt(eigv)) 
            s = self.mean + (1/np.sqrt(self.prec))*np.real(F.conj() @ splinalg.spsolve(L_sqrt, xi))
            # L_sqrt = pinvh(np.diag(np.sqrt(eigv)))
            # s = self.mean + (1/np.sqrt(self.prec))*np.real(F.conj() @ (L_sqrt @ xi))
            
        elif (self.BCs == 'neumann'):
            xi = np.random.randn(self.D.shape[0], Ns)   # standard Gaussian
            s = self.mean + (1/np.sqrt(self.prec))* \
                splinalg.spsolve(self.chol.T, (splinalg.spsolve(self.chol, (self.D.T @ xi)))) 
        else:
            raise TypeError('Unexpected BC type (choose from zero, periodic, neumann or none)')

        return s
        


# ========================================================================
class Laplace_diff(object):

    def __init__(self, location, scale, bndcond):
        self.loc = location
        self.scale = scale
        self.dim = len(location)
        self.bnd = bndcond

        # finite difference matrix
        one_vec = np.ones(self.dim)
        diags = np.vstack([-one_vec, one_vec])
        if (bndcond == 'zero'):
            locs = [-1, 0]
            Dmat = spdiags(diags, locs, self.dim+1, self.dim)
        elif (bndcond == 'periodic'):
            locs = [-1, 0]
            Dmat = spdiags(diags, locs, self.dim+1, self.dim).tocsr()
            Dmat[-1, 0] = 1
            Dmat[0, -1] = -1
        elif (bndcond == 'neumann'):
            locs = [0, 1]
            Dmat = spdiags(diags, locs, self.dim-1, self.dim)
        elif (bndcond == 'backward'):
            locs = [0, -1]
            Dmat = spdiags(diags, locs, self.dim, self.dim).tocsr()
            Dmat[0, 0] = 1
        elif (bndcond == 'none'):
            Dmat = eye(self.dim)
        self.D = Dmat

    def pdf(self, x):
        Dx = self.D @ (x-self.loc)  # np.diff(X)
        return (1/(2*self.scale))**(len(Dx)) * np.exp(-np.linalg.norm(Dx, ord=1, axis=0)/self.scale)

    def logpdf(self, x):
        Dx = self.D @ (x-self.loc)
        return len(Dx)*(-(np.log(2)+np.log(self.scale))) - np.linalg.norm(Dx, ord=1, axis=0)/self.scale

    # def cdf(self, x):   # TODO
    #     return 1/2 + 1/2*np.sign(x-self.loc)*(1-np.exp(-np.linalg.norm(x, ord=1, axis=0)/self.scale))

    # def sample(self):   # TODO
    #     p = np.random.rand(self.dim)
    #     return self.loc - self.scale*np.sign(p-1/2)*np.log(1-2*abs(p-1/2))


class Uniform(object):
    def __init__(self):
        raise NotImplementedError
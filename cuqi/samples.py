import numpy as np
import matplotlib.pyplot as plt
from cuqi.diagnostics import Geweke
from cuqi.geometry import Continuous1D, Discrete, _DefaultGeometry

class Samples(object):

    def __init__(self, samples, geometry=None):
        self.samples = samples
        self.geometry = geometry

    @property
    def geometry(self):
        if self._geometry is None:
            self._geometry = _DefaultGeometry(grid=np.prod(self.samples.shape[:-1]))
        return self._geometry

    @geometry.setter
    def geometry(self,inGeometry):
        self._geometry = inGeometry

    def burnthin(self, Nb, Nt):
        self.samples = self.samples[Nb::Nt,:]

    def plot_mean(self,*args,**kwargs):
        # Compute mean assuming samples are index in last dimension of nparray
        mean = np.mean(self.samples,axis=-1)

        # Plot mean according to geometry
        return self.geometry.plot(mean,*args,**kwargs)

    def plot(self,sample_indices=None,*args,**kwargs):
        Ns = self.samples.shape[-1]
        if sample_indices is None:
            if Ns < 10:
                return self.geometry.plot(self.samples,*args,**kwargs)
            else:
                print("Plotting 5 randomly selected samples")
                return self.geometry.plot(self.samples[:,np.random.choice(Ns,5,replace=False)],*args,**kwargs)
        else:
            return self.geometry.plot(self.samples[:,sample_indices],*args,**kwargs)

    def plot_chain(self,variable_indices,*args,**kwargs):
        return plt.plot(self.samples[variable_indices,:].T,*args,**kwargs)

    def plot_ci(self,percent,exact=None,*args,**kwargs):

        if not isinstance(self.geometry,(Continuous1D,Discrete)):
            raise NotImplementedError("Confidence interval not implemented for {}".format(self.geometry))
        
        # Compute statistics
        mean = np.mean(self.samples,axis=-1)
        lb = (100-percent)/2
        up = 100-lb
        lo_conf, up_conf = np.percentile(self.samples, [lb, up], axis=-1)

        lci = self.geometry.plot_envelope(lo_conf, up_conf, color='dodgerblue')

        lmn = self.geometry.plot(mean,*args,**kwargs)
        if exact is not None:
            lex = self.geometry.plot(exact,*args,**kwargs)
            plt.legend([lmn[0], lex[0], lci],["Mean","Exact","Confidence Interval"])
        else:
            plt.legend([lmn[0], lci],["Mean","Confidence Interval"])

    def diagnostics(self):
        # Geweke test
        Geweke(self.samples.T)

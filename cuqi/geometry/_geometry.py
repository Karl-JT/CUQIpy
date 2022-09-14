from abc import ABC, abstractmethod
import numpy as np
import numpy.matlib as matlib
import matplotlib.pyplot as plt
import math
from scipy.fftpack import dst, idst
import scipy.sparse as sparse
import operator
from functools import reduce
import warnings

def _get_identity_geometries():
    """Return the geometries that have identity `par2fun` and `fun2par` methods (including those where `par2fun` and `fun2par` perform reshaping of the parameters or the function values array. e.g. the geometry `Image2D`.).
    These geometries do not alter the gradient computations.
    """
    return [_DefaultGeometry, Continuous1D, Continuous2D, Discrete, Image2D]

class Geometry(ABC):
    """A class that represents the geometry of the range, domain, observation, or other sets.

    It specifies a mapping from the parameter space to the function space (:meth:`par2fun`) and the inverse map if possible (:meth:`fun2par`). The parameters can be for example, the center and width of a hat function, and the function is the resulting hat function evaluated at grid points of a given grid. The geometry keeps track of the dimension and shape of the parameter space (:meth:`par_dim` and :meth:`par_shape`) and the dimension and shape of the function space (:meth:`fun_dim` and :meth:`fun_shape`).
    """
    @property
    @abstractmethod
    def par_shape(self):
        """The shape of the parameter space."""
        pass

    @property
    def par_dim(self):
        """The dimension of the geometry (parameter space)."""
        if self.par_shape is None: return None
        return reduce(operator.mul, self.par_shape) # math.prod(self.par_shape) for Python 3.8+

    @property
    def fun_shape(self):
        """The shape of the geometry (function space). """
        if not hasattr(self,'_fun_shape') or self._fun_shape is None:
            # Attempt to infer dimension
            funvals = self.par2fun(np.ones(self.par_dim))
            if hasattr(funvals, 'shape'):
                self._fun_shape = funvals.shape
            else:
                warnings.warn("Could not infer function space shape.")
                self._fun_shape = None
        return self._fun_shape
    
    @property
    def fun_dim(self):
        """The dimension of the geometry (function space). """
        if self.fun_shape is None: return None
        return reduce(operator.mul, self.fun_shape) # math.prod(self.fun_shape) for Python 3.8+

    @property
    def variables(self):
        #No variable names set, generate variable names from dim
        if not hasattr(self,"_variables"):
                self.variables = self.par_dim
        return self._variables

    @variables.setter
    def variables(self, value):
        """ Set variable names with a list of strings. Generic variable names can also be generated by passing an integer. """
        variables_value_err_msg = "variables should be int, or list of strings"
        if isinstance(value,(int,np.integer)):
            # Find name of variable if set, else set it to a default
            if hasattr(self, "_variable_name") and self._variable_name is not None:
                name = self._variable_name
            else:
                name = "v"
            # If more than one variable we index, else we dont
            value = [name+str(var) for var in range(value)] if value != 1 else [name]
        elif isinstance(value,list): 
            for var in value: 
                if not isinstance(var,str):
                    raise ValueError(variables_value_err_msg)
        else:
            raise ValueError(variables_value_err_msg) 
        self._variables = value
        self._ids = range(self.par_dim)

    def plot(self, values, is_par=True, plot_par=False, **kwargs):
        """
        Plots a function over the set defined by the geometry object.
            
        Parameters
        ----------
        values : ndarray
            1D array that contains the values of the function degrees of freedom.

        is_par : Boolean, default True
            Flag to indicate whether the values are parameters or function values.
            True:  values are passed through the :meth:`par2fun` method.
            False: values are plotted directly.
        
        plot_par : Boolean, default False
            If true this method plots the parameters as a :class:`Discrete` geometry.
        """
        #Error check
        if plot_par and not is_par:
            raise Exception("Plot par is true, but is_par is false (parameters were not given)")

        if plot_par:
            geom = Discrete(self.par_dim) #par_dim is size of the parameter space.
            return geom.plot(values, **kwargs)

        if is_par:
            values = self.par2fun(values)

        return self._plot(values, **kwargs)

    def plot_envelope(self, lo_values, hi_values, is_par=True, plot_par=False, **kwargs):
        """
        Plots an envelope from lower and upper bounds over the set defined by the geometry object.
            
        Parameters
        ----------
        lo_values : ndarray
            1D array that contains a lower bound of the function degrees of freedom.

        hi_values : ndarray
            1D array that contains an upper bound of the function degrees of freedom.

        is_par : Boolean, default True
            Flag to indicate whether the values are parameters or function values.
            True:  values are passed through the :meth:`par2fun` method.
            False: values are plotted directly.
        
        plot_par : Boolean, default False
            If true this method plots the parameters as a :class:`Discrete` geometry.
        """
        #Error check
        if plot_par and not is_par:
            raise ValueError("Plot par is true, but is_par is false (parameters were not given)")
        
        if plot_par:
            geom = Discrete(self.par_dim) #par_dim is size of the parameter space.
            return geom.plot_envelope(lo_values, hi_values, **kwargs)

        if is_par:
            lo_values = self.par2fun(lo_values)
            hi_values = self.par2fun(hi_values)

        return self._plot_envelope(lo_values,hi_values, **kwargs)

    def par2fun(self,par):
        """The parameter to function map used to map parameters to function values in e.g. plotting."""
        return par

    def fun2par(self,funvals):
        """The function to parameter map used to map function values back to parameters, if available."""
        raise NotImplementedError("fun2par not implemented. Must be implemented specifically for each geometry.")

    @abstractmethod
    def _plot(self):
        pass

    def _plot_envelope(self, *args, **kwargs):
        raise NotImplementedError("Plot envelope not implemented for {}. Use flag plot_par to plot envelope of parameters instead.".format(type(self)))
            
    def _plot_config(self,values):
        """
        A method that implements any default configuration for the plots. This method is to be called inside any 'plot_' method.
        """
        pass

    def _create_subplot_list(self,Ns,subplots=True):
        Nx = math.ceil(np.sqrt(Ns))
        Ny = Nx
        subplot_ids = []
        fig = plt.gcf()
        if subplots: fig.set_size_inches(fig.bbox_inches.corners()[3][0]*Nx, fig.bbox_inches.corners()[3][1]*Ny)

        for i in range(Ny):
            for j in range(Nx):
                subplot_id = i*Nx+j+1
                if subplot_id > Ns: 
                    continue 
                subplot_ids.append((Ny,Nx,subplot_id))
        return subplot_ids

    def __eq__(self, obj):
        if not isinstance(obj, self.__class__): return False
        return self._all_values_equal(obj)

    def __repr__(self) -> str:
        return "{}{}".format(self.__class__.__name__,self.par_shape)

    def _all_values_equal(self, obj):
        """Returns true of all values of the object and self are equal"""
        for key, value in vars(self).items():
            # If _variables exist ensure it exists in both objects (by calling generator)
            if key == "_variables": obj.variables
            if key == "_variable_name" and not hasattr(obj, "_variable_name"): obj._variable_name = None

            # Store value to compare
            obj_value = vars(obj)[key]

            # If list/tuple we compare each element
            if isinstance(value, (tuple,list)) and isinstance(obj_value, (tuple,list)):
                for i in range(max(len(value),len(obj_value))):
                    if not np.array_equiv(value[i],obj_value[i]):
                        return False
            # Else we check single element
            elif not np.array_equiv(value, obj_value):
                return False 
        return True


class _WrappedGeometry(Geometry):
    """A class that wraps a given geometry (emulates dynamic
    inheritance from the given geometry).
    
    Parameters
    -----------
    geometry : cuqi.geometry.Geometry
    """

    def __init__(self,geometry):
        self.geometry = geometry

    @property
    def par_shape(self):
        return self.geometry.par_shape

    @property
    def grid(self):
        return self.geometry.grid

    @property
    def axis_labels(self):
        return self.geometry.axis_labels

    @property
    def variables(self):
        return self.geometry.variables

    @property
    def mesh(self):
        return self.geometry.mesh

    def par2fun(self,p):
        return self.geometry.par2fun(p)

    def fun2par(self,f):
        return self.geometry.fun2par(f)

    def _plot(self, values, *args, **kwargs):
        """Calls the underlying geometry plotting method."""
        return self.geometry._plot(values, *args, **kwargs)

    def _plot_envelope(self, lo_values, hi_values, *args, **kwargs):
        """Calls the underlying geometry plotting of envelope method."""
        return self.geometry._plot_envelope(lo_values, hi_values, *args, **kwargs)

    def _process_values(self,values):
        return self.geometry._process_values(values) 

    def __repr__(self) -> str:
        return "{} wraps {}".format(self.__class__.__name__,self.geometry.__repr__())


class Continuous(Geometry, ABC):

    def __init__(self,grid=None, axis_labels=None):
        self.axis_labels = axis_labels
        self.grid = grid

    def _create_dimension(self, dim_grid):
        dim_grid_value_err_msg = "dim_grid should be int, tuple with one int element, list of numbers, 1D numpy.ndarray, or None"
        if dim_grid is None:
            return None

        if isinstance(dim_grid,tuple) and len(dim_grid)==1:
            dim_grid = dim_grid[0]

        if isinstance(dim_grid,(int,np.integer)):
            dim_grid = np.arange(dim_grid)
        elif isinstance(dim_grid,(list,np.ndarray)):
            dim_grid = np.array(dim_grid)
            if len(dim_grid.shape)!=1:
                raise ValueError(dim_grid_value_err_msg)
        else:
            raise ValueError(dim_grid_value_err_msg)
        return dim_grid.astype(float)
        
    @property
    def grid(self):
        return self._grid
    
    def fun2par(self,funvals):
        return funvals

class Continuous1D(Continuous):
    """A class that represents a continuous 1D geometry.

    Parameters
    -----------
    grid : int, tuple, list or numpy.ndarray
        1D array of node coordinates in a 1D grid (list or numpy.ndarray), or number of nodes (int or tuple with one int element) in the grid. In the latter case, a default grid with unit spacing and coordinates 0,1,2,... will be created.

    Attributes
    -----------
    grid : numpy.ndarray
        1D array of node coordinates in a 1D grid
    """

    def __init__(self, grid=None, axis_labels=None, **kwargs):
        super().__init__(grid, axis_labels, **kwargs)

    @property
    def fun_shape(self):
        if self.grid is None: return None
        return self.grid.shape

    @property
    def par_shape(self):
        """The shape of the parameter space"""
        if self.grid is None: return None
        return (len(self.grid), )

    @Continuous.grid.setter
    def grid(self, value):
        self._grid = self._create_dimension(value)

    def _plot(self, values, *args, **kwargs):
        p = plt.plot(self.grid, values, *args, **kwargs)
        self._plot_config()
        return p

    def _plot_envelope(self, lo_values, up_values, **kwargs):
        default = {'color':'dodgerblue', 'alpha':0.25}
        for key in default:
            if (key not in kwargs.keys()):
                kwargs[key]  = default[key]
        return plt.fill_between(self.grid,up_values, lo_values, **kwargs)

    def _plot_config(self):
        if self.axis_labels is not None:
            plt.xlabel(self.axis_labels[0])


class Continuous2D(Continuous):

    def __init__(self,grid=None,axis_labels=None):
        super().__init__(grid, axis_labels)
            
    @property
    def fun_shape(self): 
        if self.grid is None: return None
        return (len(self.grid[0]), len(self.grid[1])) 

    @property
    def par_shape(self):
        """The shape of the parameter space"""
        if self.grid is None: return None
        return (len(self.grid[0])*len(self.grid[1]), ) 

    @Continuous.grid.setter
    def grid(self, value):
        if value is None: self._grid = None
        else:
            if len(value)!=2:
                raise NotImplementedError("grid must be a 2D tuple of int values or arrays (list, tuple or numpy.ndarray) or combination of both")
            self._grid = (self._create_dimension(value[0]), self._create_dimension(value[1]))

    def _plot(self, values, plot_type='pcolor', **kwargs):
        """
        Overrides :meth:`cuqi.geometry.Geometry.plot`. See :meth:`cuqi.geometry.Geometry.plot` for description  and definition of the parameter `values`.
        
        Parameters
        -----------
        plot_type : str
            type of the plot. If plot_type = 'pcolor', :meth:`matplotlib.pyplot.pcolor` is called, if plot_type = 'contour', :meth:`matplotlib.pyplot.contour` is called, and if `plot_type` = 'contourf', :meth:`matplotlib.pyplot.contourf` is called, 

        kwargs : keyword arguments
            keyword arguments which the methods :meth:`matplotlib.pyplot.pcolor`, :meth:`matplotlib.pyplot.contour`, or :meth:`matplotlib.pyplot.contourf`  normally take, depending on the value of the parameter `plot_type`.
        """
        if plot_type == 'pcolor': 
            plot_method = plt.pcolor
        elif plot_type == 'contour':
            plot_method = plt.contour
        elif plot_type == 'contourf':
            plot_method = plt.contourf
        else:
            raise ValueError(f"unknown value: {plot_type} of the parameter 'plot_type'")
        
        values = self._process_values(values)
        subplot_ids = self._create_subplot_list(values.shape[-1])
        ims = []
        for rows,cols,subplot_id in subplot_ids:
            plt.subplot(rows,cols,subplot_id); 
            ims.append(plot_method(self.grid[0], self.grid[1], values[..., subplot_id-1].reshape(self.fun_shape[::-1]),
                                   **kwargs))
        self._plot_config()
        return ims

    def plot_pcolor(self, values, **kwargs):
        return self.plot(values, plot_type='pcolor', **kwargs)

    def plot_contour(self, values, **kwargs):
        return self.plot(values, plot_type='contour', **kwargs)

    def plot_contourf(self, values, **kwargs):
       return self.plot(values, plot_type='contourf', **kwargs)
    
    def _process_values(self,values):
        if len(values.shape) == 3 or\
             (len(values.shape) == 2 and values.shape[0]== self.par_dim):  
            pass
        else:
            values = values[..., np.newaxis]
        return values

    def _plot_config(self):
        for i, axis in enumerate(plt.gcf().axes):
            if self.axis_labels is not None:
                axis.set_xlabel(self.axis_labels[0])
                axis.set_ylabel(self.axis_labels[1])
            axis.set_aspect('equal')

class Image2D(Geometry):
    """ A class that represents a 2D image.

    The par2fun method converts the parameter vector into an image (matrix).
    The fun2par method converts the image (matrix) into a parameter vector.

    Plotting is handled via matplotlib.pyplot.imshow.
    Colormap is defaulted to grayscale.

    Parameters
    -----------
    im_shape : tuple
        shape of the image (rows, columns)

    order : str
        If order = 'C', the image is represented in row-major order.
        if order = 'F', the image is represented column-major order.

    visual_only : bool, Default: False
        If visual_only = True, par2fun and fun2par will not convert parameter vector into image and vice versa.
        But visualization will still be in 2D image format.

    """
    def __init__(self, im_shape, order="C", visual_only=False):
        self._im_shape = im_shape
        self._par_shape = (reduce(operator.mul, im_shape), )
        self.order = order
        self.visual_only = visual_only

        # If visual only, we have same fun_shape as par_shape
        if visual_only:
            self._fun_shape = self._par_shape
        else: # else we have image shape
            self._fun_shape = self._im_shape

    @property
    def fun_shape(self):
        return self._fun_shape

    @property
    def par_shape(self):
        return self._par_shape

    def par2fun(self, pars):
        # If geometry is only used for visualization, do nothing
        if self.visual_only: return pars
        # Else, convert parameter vector into image
        return self._vector_to_image(pars)

    def fun2par(self, funvals):
        # If geometry is only used for visualization, do nothing
        if self.visual_only: return funvals
        # Else, convert image into parameter vector
        return funvals.ravel(order=self.order) #Maybe use reshape((self.dim,), order=self.order)

    def _vector_to_image(self, vectors):
        """ Converts a vector or multiple vectors into an image. """
        # Reshape to image (also for multiple parameter vectors). TODO: #327
        image = vectors.reshape(self._im_shape+(-1,), order=self.order) 
        #Squeeze to return single image if only one parameter vector was given
        image = image.squeeze()
        return image
    
    def _plot(self, values, **kwargs):
        # If only visual, we must convert value to image ourselves
        if self.visual_only:
            values = self._vector_to_image(values)

        kwargs.setdefault('cmap', kwargs.get('cmap', "gray"))

        values = self._process_values(values)
        subplot_ids = self._create_subplot_list(values.shape[-1])
        ims = []
        for rows, cols, subplot_id in subplot_ids:
            plt.subplot(rows, cols, subplot_id)
            ims.append(plt.imshow(values[...,subplot_id-1], **kwargs))
        return ims

    def _process_values(self,values):
        if len(values.shape) == 3 or\
             (len(values.shape) == 2 and values.shape[0]== self.par_dim):  
            pass
        else:
            values = values[..., np.newaxis]
        return values

class Discrete(Geometry):

    def __init__(self,variables):       
        self.variables = variables

    @property
    def fun_shape(self):
        """The shape of the function space."""
        return (len(self.variables),)

    @property
    def par_shape(self):
        """The shape of the parameter space."""
        return (len(self.variables), )

    def _plot(self,values, **kwargs):

        if ('linestyle' not in kwargs.keys()) and ('ls' not in kwargs.keys()):
            kwargs["linestyle"]  = ''
        
        if ('marker' not in kwargs.keys()):
            kwargs["marker"]  = 'o'

        self._plot_config() 
        return plt.plot(self._ids, values, **kwargs)

    def _plot_envelope(self, lo_values, up_values, **kwargs):
        self._plot_config()
        if 'fmt' in kwargs.keys():
            raise Exception("Argument 'fmt' cannot be passed by the user")

        default = {'color':'dodgerblue', 'fmt':'none' ,'capsize':3, 'capthick':1}
        for key in default:
            if (key not in kwargs.keys()):
                kwargs[key]  = default[key]

        #Convert to 1d numpy array to handle subtraction
        lo_values = np.array(lo_values).flatten()
        up_values = np.array(up_values).flatten()
        
        return plt.errorbar(self._ids, lo_values,
                            yerr=np.vstack(
                                (np.zeros(len(lo_values)), up_values-lo_values)),
                            **kwargs)

    def _plot_config(self):
        # Add at most 10 ticks including the first and last
        n_ticks = min(10, len(self.variables))
        tick_ids = np.linspace(0, len(self.variables)-1, n_ticks, dtype=int)
        plt.xticks(tick_ids, [self.variables[i] for i in tick_ids])

    def fun2par(self,funvals):
        return funvals

class MappedGeometry(_WrappedGeometry):
    """A class that represents a mapped geometry.
    
    This applies a map (callable function) to any cuqi geometry. This will change the par2fun map.
    Additionally an inverse map (imap) can also be defined to allow inverting the function values to parameters redefining the fun2par map.

    Parameters
    -----------
    geometry : cuqi.geometry.Geometry

    map : callable function
        Any callable function representing the map which should be applied after the par2fun of the geometry.

    imap : callable function, Default None
        Any callable function representing the inverse of map.
    """

    def __init__(self,geometry,map,imap=None):
        super().__init__(geometry)
        self.map = map
        self.imap = imap

    def par2fun(self,p):
        return self.map(self.geometry.par2fun(p))

    def fun2par(self,f):
        if self.imap is None:
            raise ValueError("imap is not defined. This is needed for fun2par.")
        return self.geometry.fun2par(self.imap(f))

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__,self.geometry.__repr__())


class _DefaultGeometry(Continuous1D):
    def __init__(self, grid=None, axis_labels=None):
        super().__init__(grid, axis_labels)

    def __eq__(self, obj):
        if not isinstance(obj, (self.__class__,Continuous1D)): return False
        return self._all_values_equal(obj)

# class DiscreteField(Discrete):
#     def __init__(self, grid, cov_func, mean, std, trunc_term=100, axis_labels=['x']):
#         super().__init__(grid, axis_labels)

#         self.N = len(self.grid)
#         self.mean = mean
#         self.std = std
#         XX, YY = np.meshgrid(self.grid, self.grid, indexing='ij')
#         self.Sigma = cov_func(XX, YY)
#         self.L = np.linalg.chol(self.Sigma)

#     def par2fun(self, p):
#         return self.mean + self.L.T@p
    
class KLExpansion(Continuous1D):
    """
    Class representation of the random field in the sine basis


    .. math::
        f = \sum_{i=0}^{N-2} \\left(\\frac{1}{(i+1)^\\gamma\\tau}\\right)  p_i \\, \\text{sin}\\left(\\frac{\\pi}{N}(i+1)(K+\\frac{1}{2})\\right) 
        
        + \\frac{(-1)^K}{2}\\left(\\frac{1}{N^\\gamma\\tau}\\right)  p_{N-1}

    where:

    .. math::
        \\gamma = \\text{decay_rate},

    .. math::
        \\tau = \\text{normalizer},

    :math:`K=\\{0, 1, 2, 3, ..., N-1\\}`, :math:`N` is the number of nodes in the grid, and :math:`p_i` are the expansion coefficients. 

    The above transformation is the inverse of DST-II (see https://en.wikipedia.org/wiki/Discrete_sine_transform)

    Parameters
    -----------
    grid : array-like
        One dimensional regular grid on which the random field is defined.

    decay_rate : float, default 2.5
        The decay rate of the basis functions.

    normalizer : float, default 1.0
        A factor of the basis functions shown in the formula above.
    """
    
    # init function defining parameters for the KL expansion
    def __init__(self, grid,  decay_rate=2.5, normalizer=12.0, axis_labels=None, **kwargs):

        super().__init__(grid, axis_labels, **kwargs)

        self._decay_rate = decay_rate  # decay rate of KL
        self._normalizer = normalizer  # normalizer factor
        eigvals = np.array(range(1, self.par_dim+1))  # KL eigvals
        self._coefs = 1/np.float_power(eigvals, self.decay_rate)

    @property
    def decay_rate(self):
        return self._decay_rate

    @property
    def normalizer(self):
        return self._normalizer

    @property
    def coefs(self):
        return self._coefs

    # computes the real function out of expansion coefs
    def par2fun(self,p):
        modes = p*self.coefs/self.normalizer
        real = idst(modes)/2
        return real
    
    def fun2par(self,funvals):
        """The function to parameter map used to map function values back to parameters, if available."""
        raise NotImplementedError("fun2par not implemented. ")

class KLExpansion_Full(Continuous1D):
    '''
    Class representation of the random field in the sine basis



    .. math::
        f = \\frac{\\text{std}^2}{\\pi}\sum_{i=0}^{N-2} \\left(\\frac{\\tau^\\gamma}{(\\tau+i^2)^\\gamma}\\right)  p_i \\, \\text{sin}\\left(\\frac{\\pi}{N}(i+1)(K+\\frac{1}{2})\\right) 
        
        + \\frac{\\text{std}^2}{\\pi}\\frac{(-1)^K}{2}\\left(\\frac{\\tau^\\gamma}{\\left(\\tau+(N-1)^2\\right)^\\gamma}\\right) p_{N-1}

    where:
    
    .. math::
        \\tau = \\frac{1}{\\text{cor_len}^2},

    .. math::
        \\gamma = \\text{nu}+1,

    :math:`K=\\{0, 1, 2, 3, ..., N-1\\}`, :math:`N` is the number of nodes in the grid, and :math:`p_i` are the expansion coefficients. 

    The above transformation is the inverse of DST-II (see https://en.wikipedia.org/wiki/Discrete_sine_transform)

    Parameters
    -----------
    grid : array-like
        One dimensional regular grid on which the random field is defined.

    cor_len : float, default 1.0
        The correlation length of the random field.

    nu : float, default 2.5
        Smoothness parameter of the random field.

    std : float, default 1.0
        Standard deviation of the random field.
    '''
    
    # init function defining parameters for the KL expansion
    def __init__(self, grid, std=1.0, cor_len=0.2, nu=3.0, axis_labels=None, **kwargs):

        super().__init__(grid, axis_labels, **kwargs)
 
        tau2 = 1./cor_len/cor_len
        gamma = nu+1.
        self.var = std**2

        modes = np.arange(0,self.par_dim)

        self._coefs =  np.float_power( tau2,gamma ) * np.float_power(tau2+modes**2,-gamma)

    @property
    def coefs(self):
        return self._coefs

    # computes the real function out of expansion coefs
    def par2fun(self,p):
        freq = np.zeros(self.par_dim)
        m = len(p)
        freq[:m] = p
        temp = freq*self.coefs
        real = idst(temp)/2/np.pi
        return self.var*real
    
    def fun2par(self,funvals):
        """The function to parameter map used to map function values back to parameters, if available."""
        raise NotImplementedError("fun2par not implemented. ")


class CustomKL(Continuous1D):
    """
    A class representation of a random field in which a truncated KL expansion is computed from a given covariance function.
    
    Parameters
    -----------
    grid : array-like
        One dimensional grid on which the random field is defined.
    
    cov_func : callable
        A covariance function that takes two variables and returns the covariance between them.

    mean : float, default 0.0
        The mean of the random field.

    std : float, default 1.0
        The standard deviation of the random field.
        
    trunc_term : int, default 20% of the number of grid points
        The number of terms to truncate the KL expansion at.
    """
    def __init__(self, grid, mean=0, std=1.0, cov_func=None, trunc_term=None, axis_labels=None, **kwargs):
        super().__init__(grid, axis_labels, **kwargs)

        if trunc_term is None:
            trunc_term = int(len(grid)*0.2)
        self._trunc_term = trunc_term 
        if cov_func is None:
            # Identity covariance function
            cov_func = lambda x,y: 1.0 if np.isclose(x,y,rtol=1e-10) else 0.0
        
        #self.N = len(self.grid)
        self._mean = mean
        self._std = std
        self._compute_eigpairs( grid, cov_func, std, trunc_term, int(2*self.par_dim) )

    @property
    def mean(self):
        return self._mean

    @property
    def std(self):
        return self._std

    @property
    def trunc_term(self):
        return self._trunc_term

    @property
    def eigval(self):
        return self._eigval

    @property
    def eigvec(self):
        return self._eigvec

    @property
    def par_shape(self):
        return (self.trunc_term,)

    def par2fun(self, p):
        return self.mean + ((self.eigvec@np.diag(np.sqrt(self.eigval))) @ p)
    
    def fun2par(self,funvals):
        """The function to parameter map used to map function values back to parameters, if available."""
        raise NotImplementedError("fun2par not implemented. ")
    

    def _compute_eigpairs(self, xnod, C_nu, sigma, M, N_GL):
        # xnod: points at which the field is realized (from geometry PDE)
        # C_nu: lambda function with the covariance kernel (no variance multiplied)
        # sigma: standard deviation of the field
        # M: dimension of the field (KL truncation)
        # N_GL: gauss-legendre points for the integration
        ### return eigenpairs of an arbitrary 1D correlation kernel

        # domain data    
        n = xnod.size
        a = (xnod[-1] - xnod[0])/2     # scale
        
        # compute the Gauss-Legendre abscissas and weights
        #xi, w   = quad.Gauss_Legendre(N_GL) 
        xi, w = np.polynomial.legendre.leggauss(N_GL)

        # transform nodes and weights to [0, L]
        xi_s = a*xi + a
        w_s = a*w
        
        # compute diagonal matrix 
        D = sparse.spdiags(np.sqrt(w_s), 0, N_GL, N_GL).toarray()
        S1 = matlib.repmat(np.sqrt(w_s).reshape(1, N_GL), N_GL, 1)
        S2 = matlib.repmat(np.sqrt(w_s).reshape(N_GL, 1), 1, N_GL)
        S = S1 * S2
        
        # compute covariance matrix 
        Sigma_nu = np.zeros((N_GL, N_GL))
        for i in range(N_GL):
            for j in range(N_GL):
                if i != j:
                    Sigma_nu[i,j] = C_nu(xi_s[i], xi_s[j])
                else:
                    Sigma_nu[i,j] = sigma**2   # correct the diagonal term
                      
        # solve the eigenvalue problem
        A = Sigma_nu * S                             # D_sqrt*Sigma_nu*D_sqrt
        L, h = np.linalg.eig(A)                         # solve eigenvalue problem
        # L, h = sp.sparse.linalg.eigsh(A, M, which='LM')   # np.linalg.eig(A)         
        idx = np.argsort(-np.real(L))                  # index sorting descending
        
        # order the results
        eigval = np.real(L[idx])
        h = h[:,idx]
        
        # take the M values
        eigval = eigval[:M]
        h = np.real(h[:,:M])
        
        # replace for the actual eigenvectors
        phi = np.linalg.solve(D, h)
        
        # Nystrom's interpolation formula
        # recompute covariance matrix on partition nodes and quadrature nodes
        Sigma_nu = np.zeros((n, N_GL))
        for i in range(n):
            for j in range(N_GL):
                Sigma_nu[i,j] = C_nu(xnod[i], xi_s[j])
                          
        M1 = Sigma_nu * np.matlib.repmat(w_s.reshape(N_GL,1), 1, n).T
        M2 = phi @ np.diag(1/eigval)
        eigvec = M1 @ M2

        # normalize eigenvectors (not necessary) integrate to 1
        #norm_fact = np.zeros((M,1))
        #for i in range(M):
        #    norm_fact[i] = np.sqrt(np.trapz(eigvec[:,i]**2, xnod))
        #eigvec = eigvec/np.matlib.repmat(norm_fact, 1, n)             
        self._eigval = eigval
        self._eigvec = eigvec


class StepExpansion(Continuous1D):
    '''
    Class representation of step functions (piecewise constant functions) with `n_steps` 
    equidistant steps on the interval [x0, xn], with both endpoints included.
    The function `par2fun` maps the parameters `p` (which are the step magnitudes) to the 
    corresponding step function evaluated on the spatial grid (`grid`) of nodes x0, x1, ...xn.
    
    For example, if `n_steps` is 3 and `grid` is a uniform grid on [0, L] with nodes x0=0, x1=0.1L, ..., xn=L, 
    then the resulting function evaluated on the grid will be p[0], if x<=L/3, p[1], if L/3<x<=2L/3, 
    p[2], if 2L/3<x<=L.
    
    Parameters
    -----------
    grid: ndarray
        | Regular grid points for the step expansion to be evaluated at. The number of grid points should be equal to or larger than `n_steps`. The latter setting can be useful, for example, when using the StepExpansion geometry as a domain geometry for a cuqipy :class:`Model` that expects the input to be interpolated on a (possibly fine) grid (`grid`). The interval endpoints, [x0, xn], should be included in the grid.

    n_steps: int
        | Number of equidistant steps.

    fun2par_projection: str, default 'mean'
        | Projection of the step function (evaluated on the grid) on the parameter space. The supported projections are 
        | 'mean': the parameter p[i] value will be the average of the function values at the nodes that falls in the interval  I=(x0+i*L/n_steps, x0+(i+1)*L/n_steps].
        | 'max': the parameter p[i] value will be the maximum of the function values in I.
        | 'min': the parameter p[i] value will be the minimum of the function values in I.
        
    kwargs: keyword arguments
        | keyword arguments are passed to the initializer of :class:`~cuqi.geometry.Continuous1D`
    '''
    def __init__(self, grid, n_steps=3, fun2par_projection='mean', **kwargs):

        super().__init__(grid, **kwargs)
        self._n_steps = n_steps
        self._check_grid_setup()
        self._fun2par_projection = fun2par_projection
        L = self.grid[-1]-self.grid[0]
        x0 = self.grid[0]

        self._indices = []
        for i in range(self._n_steps):
            start = x0 + i*L/self._n_steps
            end = x0 + (i+1)*L/self._n_steps
            # Extract indices of the grid points that fall in the ith interval.
            if i ==0:
                interval_indices, =  np.where((self.grid>=start)&(self.grid<=end))
            else:
                interval_indices, = np.where((self.grid>start)&(self.grid<=end))
            self._indices.append(interval_indices)    

    @property
    def par_shape(self):
        """Shape of the parameter space."""
        return (self._n_steps,)

    @property
    def n_steps(self):
        """Number of equidistant steps."""
        return self._n_steps

    def par2fun(self, p):
        real = np.zeros(self.grid.shape)
        for i in range(self._n_steps):
            real[self._indices[i]] = p[i]
 
        return real

    def fun2par(self,f):
        val = np.zeros(self._n_steps)
        for i in range(self._n_steps):
            if self._fun2par_projection.lower() == 'mean':
                val[i] = np.mean(f[self._indices[i]])
            elif self._fun2par_projection.lower() == 'max':
                val[i] = np.max(f[self._indices[i]])
            elif self._fun2par_projection.lower() == 'min':
                val[i] = np.min(f[self._indices[i]])
            else:
                raise ValueError("Invalid projection option.")
        return val

    def _check_grid_setup(self):
        
        # The grid size is greater than or equal to the number of steps.
        if self._n_steps > np.size(self.grid):
            raise ValueError("n_steps must be smaller than the number of grid points")
        
        # Ensure the grid is equally spaced
        if not np.allclose(np.diff(self.grid), self.grid[1]-self.grid[0]):
            raise ValueError("The grid must be an equally spaced grid (regular).")

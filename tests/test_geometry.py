import numpy as np
import scipy as sp
import cuqi
import pytest
from cuqi.geometry import Continuous2D, Continuous1D

@pytest.mark.parametrize("geomClass,grid,expected_grid,expected_par_shape,expected_fun_shape,expected_dim",
                         [(cuqi.geometry.Continuous1D,(1),np.array([0]),(1,),(1,),1),
			  (cuqi.geometry.Continuous1D,(1,),np.array([0]),(1,),(1,),1),
			  (cuqi.geometry.Continuous1D, 1, np.array([0]),(1,),(1,),1),
			  (cuqi.geometry.Continuous1D, [1,2,3,4],np.array([1,2,3,4]),(4,),(4,),4),
			  (cuqi.geometry.Continuous1D, 5,np.array([0,1,2,3,4]),(5,),(5,),5),
			  (cuqi.geometry.Continuous2D,(1,1),(np.array([0]),np.array([0])),(1,),(1,1),1),
			  (cuqi.geometry.Continuous2D,([1,2,3],1), (np.array([1,2,3]), np.array([0])), (3,),(3,1), 3)
			  ])
def test_Continuous_geometry(geomClass,grid,expected_grid,expected_par_shape, expected_fun_shape,expected_dim):
    geom = geomClass(grid=grid)
    assert(np.all(np.hstack(geom.grid) == np.hstack(expected_grid))
           and (geom.par_shape == expected_par_shape)
	   and (geom.par_dim == expected_dim)
	   and (geom.fun_shape == expected_fun_shape)
	   and (geom.fun_dim == expected_dim))

@pytest.mark.parametrize("geomClass",
                         [(cuqi.geometry.Continuous1D),
			  (cuqi.geometry.Continuous2D)])
def test_None_Continuous_geometry(geomClass):
    geom = geomClass()
    assert(    (geom.grid == None)
           and (geom.par_shape == None)
           and (geom.par_dim == None)
           and (geom.fun_shape == None)
	   and (geom.fun_dim == None))

@pytest.mark.parametrize("geomClass,grid,expected_grid,expected_shape,expected_dim",
                         [(cuqi.geometry.Continuous1D, (4,), np.array([0,1,2,3]),(4,),4),
			  (cuqi.geometry.Continuous2D, (2,3), (np.array([0,1]), np.array([0,1,2])), (2,3), 6)])
def test_update_Continuous_geometry(geomClass,grid,expected_grid,expected_shape,expected_dim):
    geom = geomClass()
    geom.grid = grid
    assert(np.all(np.hstack(geom.grid) == np.hstack(expected_grid))
           and (geom.fun_shape == expected_shape)
	   and (geom.fun_dim == expected_dim))

@pytest.mark.parametrize("variables,expected_variables,expected_shape,expected_dim",
                         [(3,['v0','v1','v2'],(3,),3),
			  (['a','b'],['a','b'],(2,),2),
			  (1,['v'],(1,),1),
			  ])
def test_Discrete_geometry(variables,expected_variables,expected_shape,expected_dim):
    geom = cuqi.geometry.Discrete(variables)
    assert(geom.variables == expected_variables
           and (geom.par_shape == expected_shape)
	   and (geom.par_dim == expected_dim))

@pytest.mark.parametrize("geom1,geom2,truth_value",
                         [(cuqi.geometry._DefaultGeometry(2),cuqi.geometry.Continuous1D(2), True),
			  (cuqi.geometry.Continuous1D(2),cuqi.geometry.Continuous2D((1,2)), False),
			  (cuqi.geometry._DefaultGeometry(np.array([0,1])),cuqi.geometry.Continuous1D(2), True),
			  (cuqi.geometry.Continuous1D(2),cuqi.geometry._DefaultGeometry(3), False),
			  (cuqi.geometry.Discrete(2),cuqi.geometry.Discrete(["v0","v1"]), True),
			  (cuqi.geometry.Discrete(2),cuqi.geometry.Continuous1D(2), False)])
def test_geometry_equivalence(geom1,geom2,truth_value):
    assert( (geom1==geom2) == truth_value)

# Make sure plotting does not fail at least
@pytest.mark.parametrize("is_par,plot_par",	[(True,False),(True,True),(False,False)])
@pytest.mark.parametrize("geom,val",[
						(cuqi.geometry.Discrete(1),np.pi,),
						(cuqi.geometry.Discrete(1),[np.pi]),
						(cuqi.geometry.Discrete(3),[1,2,3]),
						(cuqi.geometry.Continuous1D(1), np.pi,),
						(cuqi.geometry.Continuous1D(1),[np.pi]),
						(cuqi.geometry.Continuous1D(3),[1,2,3]),
						])
def test_geometry_plot(geom,val,is_par,plot_par):
	geom.plot(val,is_par=is_par,plot_par=plot_par)

@pytest.mark.parametrize("is_par,plot_par",	[(True,False),(True,True),(False,False)])
@pytest.mark.parametrize("geom,lo_val,hi_val",[
						(cuqi.geometry.Discrete(1),np.pi,2*np.pi),
						(cuqi.geometry.Discrete(1),[np.pi],[2*np.pi]),
						(cuqi.geometry.Discrete(3),[1,2,3],[4,5,6]),
						(cuqi.geometry.Continuous1D(1),np.pi,2*np.pi),
						(cuqi.geometry.Continuous1D(1),[np.pi],[2*np.pi]),
						(cuqi.geometry.Continuous1D(3),[1,2,3],[4,5,6]),
						])
def test_geometry_plot(geom,lo_val,hi_val,is_par,plot_par):
	geom.plot_envelope(lo_val,hi_val,is_par=is_par,plot_par=plot_par)

def test_geometry_variables_generator_default():
	g1 = cuqi.geometry._DefaultGeometry(5)
	g2 = cuqi.geometry._DefaultGeometry(5)
	g1.variables #Extract variables (they are generated in g1, but not in g2)
	assert g1==g2 #g2 has no _variables yet, but during check its generated.

def test_geometry_variables_generator_Geometry():
	g1 = cuqi.geometry.Continuous1D(5)
	g2 = cuqi.geometry.Continuous1D(5)
	g1.variables #Extract variables (they are generated in g1, but not in g2)
	assert g1==g2 #g2 has no _variables yet, but during check its generated.


@pytest.mark.parametrize("geom, map, imap",
                         [(cuqi.geometry.Discrete(4), lambda x:x**2, lambda x:np.sqrt(x)),
			  (cuqi.geometry.Continuous1D(15),lambda x:x+12, lambda x:x-12),
			  (cuqi.geometry.Continuous2D((4,5)), lambda x:x**2+1, lambda x:np.sqrt(x-1))
			  ])
def test_mapped_geometry(geom, map, imap):
    np.random.seed(0)

    mapped_geom = cuqi.geometry.MappedGeometry(geom, map, imap)
    val = np.random.rand(mapped_geom.par_dim)
    mapped_val = mapped_geom.par2fun(val)
    imapped_mapped_val = mapped_geom.fun2par(mapped_val)
    assert(np.allclose(val, imapped_mapped_val) and geom.par_shape == mapped_geom.par_shape)
    
@pytest.mark.parametrize("g1, g2, truth_value",[
						(Continuous2D((128,128)), Continuous2D((128,128)), True),
						(Continuous2D((1,2)), Continuous2D((1,2)), True),
						(Continuous2D((3,2)), Continuous2D((3,2)), True),
						(Continuous2D(), Continuous2D(), True),
						(Continuous1D(5), Continuous1D(5), True),
						(Continuous1D(), Continuous1D(), True),
						(Continuous2D((128,128)), Continuous2D((128,127)), False),
						(Continuous2D((1,2)), Continuous2D((1,3)), False),
						(Continuous2D((3,2)), Continuous2D((3,3)), False),
						(Continuous2D(), Continuous2D((1,2)), False),
						(Continuous2D((1,2)), Continuous2D(), False),
						(Continuous1D(5), Continuous1D(6), False),
						(Continuous1D(), Continuous1D(1), False),
						(Continuous1D(1), Continuous1D(), False),
						])
def test_geometry_equality(g1, g2, truth_value):
	"""Ensure geometry arrays compare correctly"""
	assert (g1==g2) == truth_value

@pytest.mark.parametrize("n_steps",[1,2,6,7,9,10,20, 21])
def test_StepExpansion_geometry(n_steps):
    """Check StepExpansion geometry correctness"""
    grid = np.linspace(0,1,20)
    if n_steps > np.size(grid):
	#If n_steps is greater than the number of grid points, StepExpansion will fail
        with pytest.raises(ValueError):
            cuqi.geometry.StepExpansion(grid,n_steps)
    else:
	#Otherwise, assert that the StepExpansion is correct
        geom = cuqi.geometry.StepExpansion(grid,n_steps)
        par = np.random.randn(n_steps)
        geom.plot(par,linestyle = '', marker='.')

        assert np.allclose(par, geom.fun2par(geom.par2fun(par))) \
           and geom.par_dim == n_steps

@pytest.mark.parametrize("projection, func",[('MiN', np.min),
      ('mAX', np.max),('mean', np.mean)])
def test_stepExpansion_fun2par(projection, func):
    """Check StepExpansion fun2par correctness when different projection methods are used"""

    # Set up geometry and grid
    np.random.seed(0)
    grid = np.linspace(0,10, 100, endpoint=True)
    n_steps = 3
    SE_geom = cuqi.geometry.StepExpansion(grid, n_steps=n_steps, fun2par_projection=projection)
    
    # Create cuqi array of function values
    qa_f = cuqi.array.CUQIarray(np.random.rand(len(grid)), is_par=False, geometry = SE_geom)
    
    # Compute projection manually (function value to parameters)
    p = np.empty(n_steps)
    p[0]= func(qa_f[np.where(grid <=grid[-1]/n_steps)])
    p[1]= func(qa_f[np.where((grid[-1]/n_steps < grid)&( grid <=2*grid[-1]/n_steps))])
    p[2]= func(qa_f[np.where(2*grid[-1]/n_steps < grid)])

    # Compare projection with fun2par results
    assert np.allclose(p, qa_f.parameters)

@pytest.mark.parametrize("num_modes",[1, 10, 20, 25])
def test_KL_expansion(num_modes):
    """Check KL expansion geometry correctness"""
    N = 20
    grid = np.linspace(0, 1, N)
    decay_rate = 2.5
    normalizer = 12
    geom = cuqi.geometry.KLExpansion(grid,
                                     decay_rate=decay_rate,
                                     normalizer=normalizer,
                                     num_modes=num_modes)
    if num_modes > len(grid):
        num_modes = len(grid)

    p = np.random.randn(N)
    f_geom = geom.par2fun(p[:num_modes])

    p[num_modes:] = 0
    f_expected = _inverse_sin_discrete_transform_KL(
        p, N, decay_rate, normalizer)

    assert np.allclose(f_geom, f_expected)
    assert len(geom.coefs) == geom.par_dim
    assert geom.par_dim == geom.num_modes
    assert len(geom.grid) == geom.fun_dim


def test_KLExpansion_set_grid():
    """Check updating grid in KL expansion geometry"""
    dim = 100
    grid = np.linspace(0, 1, dim)
    geom = cuqi.geometry.KLExpansion(grid, num_modes=200, decay_rate=1.5)

    # If num_modes > len(grid), num_modes is set to len(grid)
    assert geom.num_modes == 100 and len(geom.coefs) == 100

    # Update grid (num_modes > len(grid))
    geom.grid = np.linspace(0, 1, 120)
    assert geom.num_modes == 120 and len(geom.coefs) == 120

    # Update grid (num_modes < len(grid))
    geom.grid = np.linspace(0, 1, 300)
    assert geom.num_modes == 200 and len(geom.coefs) == 200


def test_KLExpansion_input():
    """Check KL expansion geometry par2fun input"""
    grid = np.linspace(0, 1, 100)
    geom = cuqi.geometry.KLExpansion(grid, num_modes=30, decay_rate=1.5)

    input = np.random.randn(150)

    # Correct input
    geom.par2fun(input[:30])

    # Input larger than num_modes
    with pytest.raises(ValueError):
        geom.par2fun(input)

    # Input smaller than num_modes
    with pytest.raises(ValueError):
        geom.par2fun(input[:5])


def test_KLExpansion_None_grid():
    """Check KL expansion geometry when grid is None at the initialization or
    set to None later"""

    # Initialize KLExpansion geometry with None grid
    geom = cuqi.geometry.KLExpansion(None, num_modes=100, decay_rate=1.5)

    # Check geometry properties
    assert geom.num_modes == 0
    assert geom.par_dim == 0
    assert geom.fun_dim is None
    assert geom.coefs is None

    # Set grid
    geom.grid = np.linspace(0, 1, 110)

    # Check geometry properties
    assert geom.num_modes == 100
    assert geom.par_dim == 100
    assert geom.fun_dim == 110
    assert geom.coefs is not None

    # Initialize KLExpansion geometry with grid of length 110
    geom = cuqi.geometry.KLExpansion(np.linspace(
        0, 1, 110), num_modes=100, decay_rate=1.5)

    # Check geometry properties
    assert geom.num_modes == 100
    assert geom.par_dim == 100
    assert geom.fun_dim == 110
    assert geom.coefs is not None

    # Set grid to None
    geom.grid = None

    # Check geometry properties
    assert geom.num_modes == 0
    assert geom.par_dim == 0
    assert geom.fun_dim is None
    assert geom.coefs is None

    # Initialize KLExpansion geometry with no arguments
    geom = cuqi.geometry.KLExpansion()

    # Check geometry properties
    assert geom.num_modes == 0
    assert geom.par_dim == 0
    assert geom.fun_dim is None
    assert geom.coefs is None

def _inverse_sin_discrete_transform_KL(p, N, decay_rate, normalizer):
    """Inverse of sin discrete transform, the code
    computes the KL expansion coefficients that the KLExpansion geometry computes given p and then computes the same transformation done by `idst` from
    `scipy.fftpack`"""
    p_f2 = np.zeros(N)
    modes = []
    K = np.arange(N)
    for i in range(0,N-1):

        coeff = 1/np.float_power( i+1,decay_rate )
        modes.append( p[i]*coeff/normalizer)
        p_f2 +=  modes[-1]*np.sin(np.pi*(i+1) *(K+.5)/N)

    coeff = 1/np.float_power( N,decay_rate )
    modes.append( p[-1]*coeff/normalizer)

    p_f2 +=(-1)**(K)/2*modes[-1]
    return p_f2

def _inverse_sin_discrete_transform_KLFull(p, N, var, tau, gamma):
    """Inverse of sin discrete transform, the code
    computes the KL expansion coefficients that the KLExpansion_Full geometry computes given p and then computes the same transformation done by `idst` from
    `scipy.fftpack`"""
    p_f2 = np.zeros(N)
    modes = []
    K = np.arange(N)
    for i in range(0,N-1):

        coeff = var*np.float_power(tau, gamma)*np.float_power( i**2+tau,-gamma)
        modes.append( p[i]*coeff)
        p_f2 +=  modes[-1]*np.sin(np.pi*(i+1) *(K+.5)/N)

    coeff = var*np.float_power(tau, gamma)*np.float_power( (N-1)**2+tau,-gamma)
    modes.append( p[-1]*coeff)

    p_f2 +=(-1)**(K)/2*modes[-1]

    return p_f2/np.pi

def test_KLExpansion_Full_geometry():
    """Check KLExpansion_Full geometry correctness"""
    N = 20
    grid = np.linspace(0,1,N)
    std = 1.2
    cor_len = .1
    nu = 3.0
    geom = cuqi.geometry.KLExpansion_Full(grid,std,cor_len,nu)

    p = np.random.randn(N)
    f_geom = geom.par2fun(p)
    var = std**2
    tau = 1.0/cor_len**2
    gamma = nu+1.
    f_expected = _inverse_sin_discrete_transform_KLFull(p, N, var, tau, gamma)

    assert np.allclose(f_geom, f_expected)

def test_create_CustomKL_geometry():
    """Check CustomKL geometry initialization"""
    N = 20
    grid = np.linspace(0,1,N)
    mean = 1
    std = .1
    cov_func = None
    trunc_term = 4
    geom = cuqi.geometry.CustomKL(grid,mean,std,cov_func,trunc_term)

    assert np.isclose(geom.mean, mean) and\
           np.isclose(geom.std, std) and\
	   geom.trunc_term==trunc_term
	

def test_KLExpansion_projection():
    """Check KLExpansion geometry projection performed by the method fun2par)"""
    # Set up a KLExpansion geometry
    num_modes = 95
    N = 100
    L = 1.0
    grid = np.linspace(0,1,N)

    geom = cuqi.geometry.KLExpansion(grid, num_modes=num_modes,
     decay_rate=1.5,
     normalizer=12.0)

    # Create a signal 
    signal =1/30*(1-np.cos(2*np.pi*(L-grid)/(L)))\
                    +1/30*np.exp(-2*(10*(grid-0.5))**2)+\
                     1/30*np.exp(-2*(10*(grid-0.8))**2)

    # Project signal to the KL basis and back
    p = geom.fun2par(signal)
    assert(len(p) == num_modes)

    signal_proj = geom.par2fun(p)
    assert(len(signal_proj) == N)

    # Check that the projection is accurate
    rel_err = np.linalg.norm(signal-signal_proj)/np.linalg.norm(signal)
    assert np.isclose(rel_err, 0.0, atol=1e-5)

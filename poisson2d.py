import numpy as np
import sympy as sp
import scipy.sparse as sparse
import scipy


x, y = sp.symbols('x,y')

class Poisson2D:
    r"""Solve Poisson's equation in 2D::

        \nabla^2 u(x, y) = f(x, y), in [0, L]^2

    where L is the length of the domain in both x and y directions.
    Dirichlet boundary conditions are used for the entire boundary.
    The Dirichlet values depend on the chosen manufactured solution.

    """

    def __init__(self, L, ue):
        """Initialize Poisson solver for the method of manufactured solutions

        Parameters
        ----------
        L : number
            The length of the domain in both x and y directions
        ue : Sympy function
            The analytical solution used with the method of manufactured solutions.
            ue is used to compute the right hand side function f.
        """
        self.L = L
        self.ue = ue
        self.f = sp.diff(self.ue, x, 2)+sp.diff(self.ue, y, 2)

    def create_mesh(self, N):
        """Create 2D mesh and store in self.xij and self.yij"""
        # self.xij, self.yij ...
        self.N = N
        self.h = self.L/self.N
        x = np.linspace(0, self.L, self.N+1)
        y = np.linspace(0, self.L, self.N+1)
        self.xij, self.yij = np.meshgrid(x,y, indexing='ij')
        return x,y

    def D2(self):
        """Return second order differentiation matrix"""
        D = sparse.diags([1, -2, 1], [-1, 0, 1], (self.N+1, self. N+1), 'lil')
        D[0,:4] = 2, -5, 4, -1 
        D[-1, -4:] = -1, 4, -5, 2
        return D

    def laplace(self):
        """Return vectorized Laplace operator"""
        D2 = (1./self.h**2)*self.D2()
        vecLap = (sparse.kron(D2, sparse.eye(self.N+1))+sparse.kron(sparse.eye(self.N+1), D2))
        return vecLap

    def get_boundary_indices(self):
        """Return indices of vectorized matrix that belongs to the boundary"""
        B = np.ones((self.N+1, self.N+1), dtype=bool)
        B[1:-1, 1:-1] = 0 
        bnds = np.where(B.ravel() ==1)[0]
        return bnds


    def assemble(self):
        """Return assembled matrix A and right hand side vector b""" 
        #here we have to implement the boundary conditions, but these are not zero as in the lecture, we have to something different for the assamblence of A.
        # return A, b
        F = sp.lambdify((x,y), self.f)(self.xij, self.yij)
        A = self.laplace()
        A = A.tolil()
        bnds = self.get_boundary_indices()
        for i in bnds: 
            A[i]= 0 
            A[i,i] = 1 
        A = A.tocsr()    
        b = F.ravel()
        ue_func = sp.lambdify((x,y), self.ue)(self.xij, self.yij)
        b[bnds] = ue_func.ravel()[bnds]
        return A, b


    def l2_error(self, u):
        """Return l2-error norm"""
        uj = sp.lambdify([x,y], self.ue )(self.xij, self.yij)
        return np.sqrt(self.h**2*np.sum((uj-u)**2))

    def __call__(self, N):
        """Solve Poisson's equation.

        Parameters
        ----------
        N : int
            The number of uniform intervals in each direction

        Returns
        -------
        The solution as a Numpy array

        """
        self.create_mesh(N)
        A, b = self.assemble()
        U = self.U = sparse.linalg.spsolve(A, b.flatten()).reshape((N+1, N+1))
        return self.U

    def convergence_rates(self, m=6):
        """Compute convergence rates for a range of discretizations

        Parameters
        ----------
        m : int
            The number of discretization levels to use

        Returns
        -------
        3-tuple of arrays. The arrays represent:
            0: the orders
            1: the l2-errors
            2: the mesh sizes
        """
        E = []
        h = []
        N0 = 8
        for m in range(m):
            u = self(N0)
            E.append(self.l2_error(u))
            h.append(self.h)
            N0 *= 2
        r = [np.log(E[i-1]/E[i])/np.log(h[i-1]/h[i]) for i in range(1, m+1, 1)]
        return r, np.array(E), np.array(h)

    def eval(self, x, y):
        """Return u(x, y)

        Parameters
        ----------
        x, y : numbers
            The coordinates for evaluation

        Returns
        -------
        The value of u(x, y)

        """
        interpol_func = scipy.interpolate.RegularGridInterpolator((self.xij[:,0], self.yij[0,:]), self.U)
        return interpol_func(np.array([[x,y]]))[0]

        

def test_convergence_poisson2d():
    # This exact solution is NOT zero on the entire boundary
    ue = sp.exp(sp.cos(4*sp.pi*x)*sp.sin(2*sp.pi*y))
    sol = Poisson2D(1, ue)
    r, E, h = sol.convergence_rates()
    assert abs(r[-1]-2) < 1e-2

def test_interpolation():
    ue = sp.exp(sp.cos(4*sp.pi*x)*sp.sin(2*sp.pi*y))
    sol = Poisson2D(1, ue)
    U = sol(100)
    assert abs(sol.eval(0.52, 0.63) - ue.subs({x: 0.52, y: 0.63}).n()) < 1e-3
    assert abs(sol.eval(sol.h/2, 1-sol.h/2) - ue.subs({x: sol.h, y: 1-sol.h/2}).n()) < 1e-3

test_convergence_poisson2d()
test_interpolation()
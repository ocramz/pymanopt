import numpy as np
from numpy import testing as np_testing
from scipy.linalg import eigvalsh, expm

from pymanopt.manifolds import SymmetricPositiveDefinite
from pymanopt.tools.multi import multiprod, multisym, multitransp

from .._test import TestCase


class TestSingleSymmetricPositiveDefiniteManifold(TestCase):
    def setUp(self):
        self.n = n = 15
        self.manifold = SymmetricPositiveDefinite(n)

    def test_random_point(self):
        # Just test that rand returns a point on the manifold and two
        # different matrices generated by rand aren't too close together
        n = self.n
        manifold = self.manifold
        x = manifold.random_point()

        assert np.shape(x) == (n, n)

        # Check symmetry
        np_testing.assert_allclose(x, multisym(x))

        # Check positivity of eigenvalues
        w = np.linalg.eigvalsh(x)
        assert (w > [0]).all()

    def test_dist(self):
        manifold = self.manifold
        x = manifold.random_point()
        y = manifold.random_point()

        # Test separability
        np_testing.assert_almost_equal(manifold.dist(x, x), 0.0)

        # Test symmetry
        np_testing.assert_almost_equal(
            manifold.dist(x, y), manifold.dist(y, x)
        )

        # Test alternative implementation
        # from Eq 6.14 of "Positive definite matrices"
        d = np.sqrt((np.log(eigvalsh(x, y)) ** 2).sum())
        np_testing.assert_almost_equal(manifold.dist(x, y), d)

        # check that dist is consistent with log
        np_testing.assert_almost_equal(
            manifold.dist(x, y), manifold.norm(x, manifold.log(x, y))
        )

        # Test invariance under inversion
        np_testing.assert_almost_equal(
            manifold.dist(x, y),
            manifold.dist(np.linalg.inv(y), np.linalg.inv(x)),
        )

        # Test congruence-invariance
        a = np.random.normal(size=(self.n, self.n))  # must be invertible
        axa = multiprod(multiprod(a, x), multitransp(a))
        aya = multiprod(multiprod(a, y), multitransp(a))
        np_testing.assert_almost_equal(
            manifold.dist(x, y), manifold.dist(axa, aya)
        )

    def test_exp(self):
        manifold = self.manifold
        x = manifold.random_point()
        u = manifold.random_tangent_vector(x)
        e = expm(np.linalg.solve(x, u))

        np_testing.assert_allclose(multiprod(x, e), manifold.exp(x, u))
        u = u * 1e-6
        np_testing.assert_allclose(manifold.exp(x, u), x + u)

    def test_random_tangent_vector(self):
        # Just test that random_tangent_vector returns an element of the tangent space
        # with norm 1 and that two random_tangent_vectors are different.
        manifold = self.manifold
        x = manifold.random_point()
        u = manifold.random_tangent_vector(x)
        v = manifold.random_tangent_vector(x)
        np_testing.assert_allclose(multisym(u), u)
        np_testing.assert_almost_equal(1, manifold.norm(x, u))
        assert np.linalg.norm(u - v) > 1e-3

    def test_norm(self):
        manifold = self.manifold
        x = manifold.random_point()
        np.testing.assert_almost_equal(
            manifold.norm(np.eye(self.n), x), np.linalg.norm(x)
        )

    def test_exp_log_inverse(self):
        manifold = self.manifold
        x = manifold.random_point()
        y = manifold.random_point()
        u = manifold.log(x, y)
        np_testing.assert_allclose(manifold.exp(x, u), y)

    def test_log_exp_inverse(self):
        manifold = self.manifold
        x = manifold.random_point()
        u = manifold.random_tangent_vector(x)
        y = manifold.exp(x, u)
        np_testing.assert_allclose(manifold.log(x, y), u)


class TestMultiSymmetricPositiveDefiniteManifold(TestCase):
    def setUp(self):
        self.n = n = 10
        self.k = k = 3
        self.manifold = SymmetricPositiveDefinite(n, k=k)

    def test_dim(self):
        manifold = self.manifold
        n = self.n
        k = self.k
        np_testing.assert_equal(manifold.dim, 0.5 * k * n * (n + 1))

    def test_typical_dist(self):
        manifold = self.manifold
        np_testing.assert_equal(manifold.typical_dist, np.sqrt(manifold.dim))

    def test_dist(self):
        # n = self.n
        manifold = self.manifold
        x = manifold.random_point()
        y = manifold.random_point()

        # Test separability
        np_testing.assert_almost_equal(manifold.dist(x, x), 0.0)

        # Test symmetry
        np_testing.assert_almost_equal(
            manifold.dist(x, y), manifold.dist(y, x)
        )

    def test_inner_product(self):
        manifold = self.manifold
        k = self.k
        n = self.n
        x = manifold.random_point()
        a, b = np.random.normal(size=(2, k, n, n))
        np.testing.assert_almost_equal(
            np.tensordot(a, b.transpose((0, 2, 1)), axes=a.ndim),
            manifold.inner_product(x, multiprod(x, a), multiprod(x, b)),
        )

    def test_projection(self):
        manifold = self.manifold
        x = manifold.random_point()
        a = np.random.normal(size=(self.k, self.n, self.n))
        np.testing.assert_allclose(manifold.projection(x, a), multisym(a))

    def test_euclidean_to_riemannian_gradient(self):
        manifold = self.manifold
        x = manifold.random_point()
        u = np.random.normal(size=(self.k, self.n, self.n))
        np.testing.assert_allclose(
            manifold.euclidean_to_riemannian_gradient(x, u),
            multiprod(multiprod(x, multisym(u)), x),
        )

    def test_euclidean_to_riemannian_hessian(self):
        # Use manopt's slow method
        manifold = self.manifold
        n = self.n
        k = self.k
        x = manifold.random_point()
        egrad, ehess = np.random.normal(size=(2, k, n, n))
        u = manifold.random_tangent_vector(x)

        Hess = multiprod(multiprod(x, multisym(ehess)), x) + 2 * multisym(
            multiprod(multiprod(u, multisym(egrad)), x)
        )

        # Correction factor for the non-constant metric
        Hess = Hess - multisym(multiprod(multiprod(u, multisym(egrad)), x))
        np_testing.assert_almost_equal(
            Hess, manifold.euclidean_to_riemannian_hessian(x, egrad, ehess, u)
        )

    def test_norm(self):
        manifold = self.manifold
        x = manifold.random_point()
        Id = np.array(self.k * [np.eye(self.n)])
        np.testing.assert_almost_equal(manifold.norm(Id, x), np.linalg.norm(x))

    def test_random_point(self):
        # Just test that rand returns a point on the manifold and two
        # different matrices generated by rand aren't too close together
        k = self.k
        n = self.n
        manifold = self.manifold
        x = manifold.random_point()

        assert np.shape(x) == (k, n, n)

        # Check symmetry
        np_testing.assert_allclose(x, multisym(x))

        # Check positivity of eigenvalues
        w = np.linalg.eigvalsh(x)
        assert (w > [[0]]).all()

    def test_random_tangent_vector(self):
        # Just test that random_tangent_vector returns an element of the tangent space
        # with norm 1 and that two random_tangent_vectors are different.
        manifold = self.manifold
        x = manifold.random_point()
        u = manifold.random_tangent_vector(x)
        v = manifold.random_tangent_vector(x)
        np_testing.assert_allclose(multisym(u), u)
        np_testing.assert_almost_equal(1, manifold.norm(x, u))
        assert np.linalg.norm(u - v) > 1e-3

    def test_transport(self):
        manifold = self.manifold
        x = manifold.random_point()
        y = manifold.random_point()
        u = manifold.random_tangent_vector(x)
        np_testing.assert_allclose(manifold.transport(x, y, u), u)

    def test_exp(self):
        # Test against manopt implementation, test that for small vectors
        # exp(x, u) = x + u.
        manifold = self.manifold
        x = manifold.random_point()
        u = manifold.random_tangent_vector(x)
        e = np.zeros((self.k, self.n, self.n))
        for i in range(self.k):
            e[i] = expm(np.linalg.solve(x[i], u[i]))
        np_testing.assert_allclose(multiprod(x, e), manifold.exp(x, u))
        u = u * 1e-6
        np_testing.assert_allclose(manifold.exp(x, u), x + u)

    def test_retraction(self):
        # Check that result is on manifold and for small vectors
        # retr(x, u) = x + u.
        manifold = self.manifold
        x = manifold.random_point()
        u = manifold.random_tangent_vector(x)
        y = manifold.retraction(x, u)

        assert np.shape(y) == (self.k, self.n, self.n)
        # Check symmetry
        np_testing.assert_allclose(y, multisym(y))

        # Check positivity of eigenvalues
        w = np.linalg.eigvalsh(y)
        assert (w > [[0]]).all()

        u = u * 1e-6
        np_testing.assert_allclose(manifold.retraction(x, u), x + u)

    def test_exp_log_inverse(self):
        manifold = self.manifold
        x = manifold.random_point()
        y = manifold.random_point()
        u = manifold.log(x, y)
        np_testing.assert_allclose(manifold.exp(x, u), y)

    def test_log_exp_inverse(self):
        manifold = self.manifold
        x = manifold.random_point()
        u = manifold.random_tangent_vector(x)
        y = manifold.exp(x, u)
        np_testing.assert_allclose(manifold.log(x, y), u)

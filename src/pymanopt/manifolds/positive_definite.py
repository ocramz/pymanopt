import numpy as np

from pymanopt.manifolds.manifold import (
    RiemannianSubmanifold,
    _raise_not_implemented_error,
)
from pymanopt.tools.multi import (
    multiexpm,
    multihconj,
    multiherm,
    multilogm,
    multiqr,
    multisym,
    multitransp,
)


class _PositiveDefiniteBase(RiemannianSubmanifold):
    def __init__(self, name, dimension, *shape):
        self._shape = shape
        super().__init__(name, dimension)

    @property
    def typical_dist(self):
        return np.sqrt(self.dim)

    def dist(self, point_a, point_b):
        c = np.linalg.cholesky(point_a)
        c_inv = np.linalg.inv(c)
        logm = multilogm(
            c_inv @ point_b @ multihconj(c_inv),
            positive_definite=True,
        )
        return np.real(np.linalg.norm(logm))

    def inner_product(self, point, tangent_vector_a, tangent_vector_b):
        return np.real(
            np.tensordot(
                np.linalg.solve(point, tangent_vector_a),
                multitransp(np.linalg.solve(point, tangent_vector_b)),
                axes=point.ndim,
            )
        )

    def projection(self, point, vector):
        return multiherm(vector)

    to_tangent_space = projection

    def euclidean_to_riemannian_gradient(self, point, euclidean_gradient):
        return self.projection(point, point @ euclidean_gradient @ point)

    def euclidean_to_riemannian_hessian(
        self, point, euclidean_gradient, euclidean_hessian, tangent_vector
    ):
        return point @ multiherm(euclidean_hessian) @ point + multiherm(
            tangent_vector @ multiherm(euclidean_gradient) @ point
        )

    def norm(self, point, tangent_vector):
        return np.sqrt(
            self.inner_product(point, tangent_vector, tangent_vector)
        )

    def random_point(self):
        # Generate eigenvalues between 1 and 2.
        d = 1.0 + np.random.uniform(size=(self._k, self._n, 1))

        # Generate an orthogonal matrix.
        q, _ = multiqr(np.random.normal(size=(self._n, self._n)))
        point = q @ (d * multitransp(q))
        if self._k == 1:
            return point[0]
        return point

    def random_tangent_vector(self, point):
        k = self._k
        n = self._n
        if k == 1:
            tangent_vector = multisym(np.random.normal(size=(n, n)))
        else:
            tangent_vector = multisym(np.random.normal(size=(k, n, n)))
        return tangent_vector / self.norm(point, tangent_vector)

    def transport(self, point_a, point_b, tangent_vector_a):
        return tangent_vector_a

    def exp(self, point, tangent_vector):
        p_inv_tv = np.linalg.solve(point, tangent_vector)
        return point @ multiexpm(p_inv_tv, symmetric=False)

    def retraction(self, point, tangent_vector):
        p_inv_tv = np.linalg.solve(point, tangent_vector)
        return multiherm(
            point + tangent_vector + tangent_vector @ p_inv_tv / 2
        )

    def log(self, point_a, point_b):
        c = np.linalg.cholesky(point_a)
        c_inv = np.linalg.inv(c)
        logm = multilogm(
            c_inv @ point_b @ multihconj(c_inv),
            positive_definite=True,
        )
        return c @ logm @ multihconj(c)

    def zero_vector(self, point):
        k = self._k
        n = self._n
        if k == 1:
            return np.zeros((n, n))
        return np.zeros((k, n, n))


class SymmetricPositiveDefinite(_PositiveDefiniteBase):
    """Manifold of symmetric positive definite matrices.

    Points on the manifold and tangent vectors are represented as arrays of
    shape ``k x n x n`` if ``k > 1``, and ``n x n`` if ``k == 1``.

    Args:
        n: The size of matrices in the manifold, i.e., the number of rows and
            columns of each element.
        k: The number of elements in the product geometry.

    Note:
        The geometry is based on the discussion in chapter 6 of [Bha2007]_.
        Also see [SH2015]_ for more details.

        The second-order retraction is taken from [JVV2012]_.
    """

    def __init__(self, n: int, *, k: int = 1):
        self._n = n
        self._k = k

        if k == 1:
            name = f"Manifold of positive definite {n}x{n} matrices"
        else:
            name = (
                f"Product manifold of {k} positive definite {n}x{n} matrices"
            )
        dimension = int(k * n * (n + 1) / 2)
        super().__init__(name, dimension)


class HermitianPositiveDefinite(_PositiveDefiniteBase):
    """Manifold of Hermitian positive definite matrices.

    Points on the manifold and tangent vectors are represented as arrays of
    shape ``k x n x n`` if ``k > 1``, and ``n x n`` if ``k == 1``.

    Args:
        n: The size of matrices in the manifold, i.e., the number of rows and
            columns of each element.
        k: The number of elements in the product geometry.
    """

    def __init__(self, n: int, *, k: int = 1):
        self._n = n
        self._k = k

        if k == 1:
            name = (
                f"Manifold of Hermitian positive definite ({n} x {n}) matrices"
            )
        else:
            name = f"Product manifold of {k} ({n} x {n}) Hermitian positive definite"
        dimension = int(k * n * (n + 1))
        super().__init__(name, dimension)

    def random_point(self):
        # Generate eigenvalues between 1 and 2.
        d = 1.0 + np.random.uniform(size=(self._k, self._n, 1))

        # Generate an orthogonal matrix.
        q, _ = multiqr(
            np.random.normal(size=(self._n, self._n))
            + 1j * np.random.normal(size=(self._n, self._n))
        )
        point = q @ (d * multihconj(q))
        if self._k == 1:
            return point[0]
        return point

    def random_tangent_vector(self, point):
        k = self._k
        n = self._n
        if k == 1:
            tangent_vector = multiherm(
                np.random.randn(n, n) + 1j * np.random.randn(n, n)
            )
        else:
            tangent_vector = multiherm(
                np.random.randn(k, n, n) + 1j * np.random.randn(k, n, n)
            )
        return tangent_vector / self.norm(point, tangent_vector)

    def zero_vector(self, point):
        k = self._k
        n = self._n
        if k == 1:
            return np.zeros((n, n), dtype=complex)
        return np.zeros((k, n, n), dtype=complex)


class SpecialHermitianPositiveDefinite(HermitianPositiveDefinite):
    """Manifold of hermitian positive definite matrices with unit determinant.

    Points on the manifold and tangent vectors are represented as arrays of
    shape ``k x n x n`` if ``k > 1``, and ``n x n`` if ``k == 1``.

    Args:
        n: The size of matrices in the manifold, i.e., the number of rows and
            columns of each element.
        k: The number of elements in the product geometry.
    """

    def __init__(self, n: int, *, k: int = 1):
        super().__init__(n, k=k)
        self.dim = int(k * n * (n + 1) - k)

    def random_point(self):
        n = self._n
        k = self._k

        # Generate point on the HPD manifold.
        point = super().random_point()

        # Unit determinant.
        shape = (k, 1, 1) if k > 1 else (1, 1)
        det = (np.linalg.det(point) ** (1 / n)).reshape(shape)
        point = point / det

        return point

    def random_tangent_vector(self, point):
        tangent_vector = super().random_tangent_vector(point)

        # Project them on tangent space.
        tangent_vector = self.projection(point, tangent_vector)

        # Unit norm.
        tangent_vector = tangent_vector / self.norm(point, tangent_vector)

        return tangent_vector

    def projection(self, point, vector):
        n = self._n
        k = self._k

        # Project matrix on tangent space of HPD.
        vector = super().projection(point, vector)

        # Project on tangent space of SHPD at x.
        shape = (k, 1, 1) if k > 1 else (1, 1)
        t = np.real(
            np.trace(np.linalg.solve(point, vector), axis1=-2, axis2=-1)
        )
        t = t.reshape(shape)
        tangent_vector = vector - (1 / n) * t * point

        return tangent_vector

    def euclidean_to_riemannian_gradient(self, point, euclidean_gradient):
        return self.projection(
            point,
            super().euclidean_to_riemannian_gradient(
                point, euclidean_gradient
            ),
        )

    @_raise_not_implemented_error
    def euclidean_to_riemannian_hessian(
        self, point, euclidean_gradient, euclidean_hessian, tangent_vector
    ):
        pass

    def exp(self, point, tangent_vector):
        n = self._n
        k = self._k

        # Compute exponential mapping on HPD.
        e = super().exp(point, tangent_vector)

        # Normalize them. (This is not necessary, but it is good for numerical
        # stability.)
        shape = (k, 1, 1) if k > 1 else (1, 1)
        det = (np.linalg.det(e) ** (1 / n)).reshape(shape)
        e = e / det

        return e

    def retraction(self, point, tangent_vector):
        n = self._n
        k = self._k

        # Compute retraction on HPD.
        r = super().retraction(point, tangent_vector)

        # Unit determinant.
        shape = (k, 1, 1) if k > 1 else (1, 1)
        det = (np.linalg.det(r) ** (1 / n)).reshape(shape)
        r = r / det

        return r

    def transport(self, point_a, point_b, tangent_vector_a):
        return self.projection(
            point_b, super().projection(point_b, tangent_vector_a)
        )

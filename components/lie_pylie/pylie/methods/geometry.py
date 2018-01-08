# -*- coding: utf-8 -*-

import numpy
import math


class DihedralGeometryError(Exception):
    pass


class AngleGeometryError(Exception):
    pass


def plane_fit(coor, center=None):
    """
    p, n = planeFit(coor)

    Fit an n-dimensional plane to the points.
    Return a point on the plane and the normal.
    """

    if center is None:
        center = coor.mean(axis=0)
    x = coor.T - center[:, None]
    m = numpy.dot(x, x.T)

    return center, numpy.linalg.svd(m.astype(float))[0][:, -1]


def center_of_mass(structure, masses=1):
    """
    Calculate structure center of mass

    :param masses: Pandas DataFrame with element mass information
                   or a default mass to be used for all atoms.
                   If nothing defind a default mass of 1 is used
                   wich equals the calculation of the geometric
                   center.
    :ptype masses: Pandas DataFrame or int/float
    :return      : Center of mass coordinate as numpy array.
    """

    centerofmass = numpy.array([0.0, 0.0, 0.0], dtype=float)
    total_mass = 0.0

    for idx, atom in structure.iterrows():
        if type(masses) in (int, float):
            mass = float(masses)
        else:
            mass = masses.loc[(masses['name'] == atom['elem']) & (masses['type'] == 'atom'), 'mw']
            if mass.empty:
                mass = 12.0
            else:
                mass = mass.values[0]

        centerofmass = centerofmass + (mass * atom[['xcoor', 'ycoor', 'zcoor']].values)
        total_mass += mass

    centerofmass /= total_mass
    return centerofmass


def calc_angle(x, y, z):
    # Calculate vectors
    v1 = numpy.array(x - y, dtype=float)
    v2 = numpy.array(z - y, dtype=float)

    # Calculate angle in radians
    cosang = numpy.dot(v1, v2)
    sinang = numpy.linalg.norm(numpy.cross(v1, v2))
    rad = numpy.arctan2(sinang, cosang)

    return rad * (360 / 2 / numpy.pi)


def distance(v1, v2):
    if not len(v1) == 3 and len(v2) == 3:
        print("Vectors are not in 3D space. Returning None.")
        return None

    return numpy.sqrt((v1[0] - v2[0]) ** 2 + (v1[1] - v2[1]) ** 2 + (v1[2] - v2[2]) ** 2)


def vector(p1, p2):
    """Vector from p1 to p2.
    :param p1: coordinates of point p1
    :param p2: coordinates of point p2
    :returns : numpy array with vector coordinates
    """
    return None if len(p1) != len(p2) else numpy.array([p2[i] - p1[i] for i in xrange(len(p1))])


def projection(pnormal1, ppoint, tpoint):
    """Calculates the centroid from a 3D point cloud and returns the coordinates
    :param pnormal1: normal of plane
    :param ppoint: coordinates of point in the plane
    :param tpoint: coordinates of point to be projected
    :returns : coordinates of point orthogonally projected on the plane
    """
    # Choose the plane normal pointing to the point to be projected
    pnormal2 = [coo * (-1) for coo in pnormal1]
    d1 = distance(tpoint, pnormal1 + ppoint)
    d2 = distance(tpoint, pnormal2 + ppoint)
    pnormal = pnormal1 if d1 < d2 else pnormal2
    # Calculate the projection of tpoint to the plane
    sn = -numpy.dot(pnormal, vector(ppoint, tpoint))
    sd = numpy.dot(pnormal, pnormal)
    sb = sn / sd
    return [c1 + c2 for c1, c2 in zip(tpoint, [sb * pn for pn in pnormal])]


def norm(a):
    """Returns the norm of a matrix or vector
    Calculates the Euclidean norm of a vector.
    Applies the Frobenius norm function to a matrix
    (a.k.a. Euclidian matrix norm)
    a = numpy array
    """
    return numpy.sqrt(sum((a * a).flat))


def angle(v1, v2, deg=False):
    """
    calculates the angle between two vectors.
    v1 and v2 are numpy.array objects.
    returns a float containing the angle in radians.
    """
    length_product = norm(v1) * norm(v2)
    if length_product == 0:
        raise AngleGeometryError("Cannot calculate angle for vectors with length zero")
    angle = numpy.arccos(numpy.dot(unit_vector(v1), unit_vector(v2)))
    return math.degrees(angle) if deg else angle


def dihedral(vec1, vec2, vec3, vec4):
    """
    Returns a float value for the dihedral angle between
    the four vectors. They define the bond for which the
    torsion is calculated (~) as:
    V1 - V2 ~ V3 - V4
    The vectors vec1 .. vec4 can be array objects, lists or tuples of length
    three containing floats.
    For Scientific.geometry.Vector objects the behavior is different
    on Windows and Linux. Therefore, the latter is not a featured input type
    even though it may work.

    If the dihedral angle cant be calculated (because vectors are collinear),
    the function raises a DihedralGeometryError
    """

    all_vecs = [vec1, vec2, vec3, vec4]

    # rule out that two of the atoms are identical
    # except the first and last, which may be.
    for i in range(len(all_vecs) - 1):
        for j in range(i + 1, len(all_vecs)):
            if i > 0 or j < 3:  # exclude the (1,4) pair
                equals = all_vecs[i] == all_vecs[j]
                if equals.all():
                    raise DihedralGeometryError("Vectors #%i and #%i may be identical!" % (i, j))

    # calculate vectors representing bonds
    v12 = vec2 - vec1
    v23 = vec3 - vec2
    v34 = vec4 - vec3

    # calculate vectors perpendicular to the bonds
    normal1 = numpy.cross(v12, v23)
    normal2 = numpy.cross(v23, v34)

    # check for linearity
    if norm(normal1) == 0 or norm(normal2) == 0:
        raise DihedralGeometryError("Vectors are in one line; cannot calculate normals!")

    # normalize them to length 1.0
    normal1 = normal1 / norm(normal1)
    normal2 = normal2 / norm(normal2)

    # calculate torsion and convert to degrees
    torsion = angle(normal1, normal2) * 180.0 / numpy.pi
    return torsion
    # take into account the determinant
    # (the determinant is a scalar value distinguishing
    # between clockwise and counter-clockwise torsion.
    if sum(normal1 * v34) >= 0:
        return torsion
    else:
        torsion = 360 - torsion
        if torsion == 360: torsion = 0.0
        return torsion


def rotation_matrix(angle, direction):
    """
    Define rotation matrix over a given angle and direction vector.

    TODO: Beter make this one use quaternion
    """

    sina = math.sin(angle)
    cosa = math.cos(angle)
    direction = unit_vector(direction[:3])

    # rotation matrix around unit vector
    r = numpy.diag([cosa, cosa, cosa])
    r += numpy.outer(direction, direction) * (1.0 - cosa)
    direction *= sina
    r += numpy.array([[0.0, -direction[2], direction[1]],
                      [direction[2], 0.0, -direction[0]],
                      [-direction[1], direction[0], 0.0]])

    return r


def unit_vector(data, axis=None, out=None):
    """
    Return the unit vector
    """

    if out is None:
        data = numpy.array(data, dtype=numpy.float64, copy=True)
        if data.ndim == 1:
            data /= math.sqrt(numpy.dot(data, data))
            return data
    else:
        if out is not data:
            out[:] = numpy.array(data, copy=False)
        data = out
    length = numpy.atleast_1d(numpy.sum(data * data, axis))
    numpy.sqrt(length, length)
    if axis is not None:
        length = numpy.expand_dims(length, axis)
    data /= length
    if out is None:
        return data
import sys
import math

import numpy as np
from numpy.ma.core import angle

"""
entnommen aus pyGeoCOM,

MIT License

Copyright (c) 2025 Stefan Printz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""


RHO = 200 / math.pi

class SWVersion(object):

    def __init__(self, release: int, version: int, sub_version: int):
        self.release = release
        self.version = version
        self.sub_version = sub_version

    def __str__(self):
        return "Version {0:02d}.{1:02d}.{2:02d}".format(self.release, self.version, self.sub_version)


class Angle(object):

    def __init__(self, rad: int = 0):
        self.value_rad = rad

    @staticmethod
    def from_gon(gon_value):
        r = Angle()
        r.set_gon(gon_value)
        return r

    @staticmethod
    def from_rad(rad_value):
        r = Angle(rad_value)
        return r

    def set_gon(self, gon):
        self.value_rad = gon / RHO
        return

    def get_gon(self):
        return self.value_rad * RHO

    def abs(self):
        r = Angle()
        r.value_rad = abs(self.value_rad)
        return r

    def __add__(self, o):
        if isinstance(o, Angle):
            r = Angle()
            r.value_rad = self.value_rad + o.value_rad
            return r
        else:
            raise TypeError("unsupported operand type(s) for +: 'Angle' and '" + str(type(o).__name__) + "'")

    def __sub__(self, o):
        if isinstance(o, Angle):
            r = Angle()
            r.value_rad = self.value_rad - o.value_rad
            return r
        else:
            raise TypeError("unsupported operand type(s) for +: 'Angle' and '" + type(o).__name__ + "'")

    def __truediv__(self, o):
        if isinstance(o, (int, float)):
            r = Angle()
            r.value_rad = self.value_rad / o
        else:
            raise TypeError("unsupported operand type(s) for /: 'Angle' and '" + type(o).__name__ + "'")
        return r

    def __str__(self):
        return '{0:.7} gon'.format(self.get_gon())

    def normalise(self):
        self.value_rad %= 2 * math.pi
        return self

    def add_half_circle(self):
        r = Angle()
        r.value_rad = self.value_rad + math.pi
        r.normalise()
        return r

    def add_full_circle(self):
        r = Angle()
        r.value_rad = self.value_rad + 2 * math.pi
        r.normalise()
        return r

    def supplementary_angle(self):
        r = Angle()
        r.value_rad = 2 * math.pi - self.value_rad
        return r

    def sin(self):
        return math.sin(self.value_rad)

    def cos(self):
        return math.cos(self.value_rad)




class Measurement(object):

    def __init__(self, target, direction: Angle, zenith: Angle, sd, atmospheric_data, measure_time):
        self.target_number = target
        self.direction = direction
        self.zenith = zenith
        self.slope_distances = sd
        self.atmospheric_data = atmospheric_data
        self.measure_time = measure_time

    def __str__(self):
        return "[target: " + str(self.target_number) + ", direction: " + str(self.direction) + " , zenith: " \
               + str(self.zenith) + ", slope_distances: " + str(self.slope_distances) + ", atmospheric_data: "\
               + str(self.atmospheric_data) + ", Measure Time: " + str(self.measure_time) + "]"

    def get_horizontal_distances(self):
        return self.slope_distances * self.zenith.sin()

    def get_delta_height(self):
        return self.slope_distances * self.zenith.cos()

    def get_local_coordinate(self):
        hd = self.get_horizontal_distances()
        y = hd * self.direction.sin()
        x = hd * self.direction.cos()
        z = self.get_delta_height()
        return Coordinate(self.target_number, x, y, z)

    def get_arra(self):
        return [self.target_number, self.direction.get_gon(), self.zenith.get_gon(), self.slope_distances ]


class MeasurementTarget(object):
    def __init__(self, target, direction: Angle, zenith: Angle, distance):
        self.target_number = target
        self.direction = direction
        self.distance = distance
        self.zenith = zenith
        self.face1 = []
        self.face2 = []

    def evaluation(self, zero_direction : Measurement):
        return Measurement(self.target_number, self.reduce_direction(zero_direction), self.zenith_angle_evaluation(), self.distance_evaluation(), self.face1[0].atmospheric_data, self.face1[0].measure_time)

    def reduce_direction(self, zero_direction : Measurement):
        sum_r = Angle()
        for i in range(len(self.face1)):
            sum_r += ((self.face1[i].direction + self.face2[i].direction.add_half_circle())/2.0 - zero_direction.direction).normalise()
        return sum_r/len(self.face1)

    def zenith_angle_evaluation(self):
        sum_z = Angle()
        for i in range(len(self.face1)):
            sum_z += (((self.face1[i].zenith - self.face2[i].zenith).add_full_circle()) / 2.0)
        return sum_z / len(self.face1)

    def distance_evaluation(self):
        sum_d = 0
        for i in range(len(self.face1)):
            sum_d += (self.face1[i].slope_distances + self.face2[i].slope_distances) / 2.0
        return sum_d / len(self.face1)

    def __str__(self):
        return "Target: " +  str(self.target_number) + " hz: " + str(self.direction) + " vz: " + str(self.zenith) + " s: " + str(self.distance)


class Coordinate(object):

    def __init__(self, pkt_nr, x: float, y: float, z: float):
        self.pkt_nr = pkt_nr
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, o):
        if isinstance(o, Coordinate):
            return Coordinate(self.pkt_nr, self.x + o.x, self.y + o.y, self.z + o.z)
        else:
            raise TypeError("unsupported operand type(s) for +: 'Coordinate' and '" + type(o).__name__ + "'")

    def __sub__(self, o):
        if isinstance(o, Coordinate):
            return Coordinate(self.pkt_nr, self.x - o.x, self.y - o.y, self.z - o.z)
        else:
            raise TypeError("unsupported operand type(s) for -: 'Coordinate' and '" + type(o).__name__ + "'")

    def direction_to(self, o: "Coordinate"):
        dc = o - self
        theta_rad = math.atan2(dc.x, dc.y)
        return Angle.from_rad(theta_rad)

    def get_array(self):
        return [self.y, self.x, self.z]

    def get_homogene_array(self):
        return [self.y, self.x, self.z, 1]

    def __str__(self):
        return "[Pkt: " + str(self.pkt_nr) + " x: " + str(self.x) + ", y: " + str(self.y) + " , z: " + str(self.z) + "]"


class FullAngleMeasurement(object):

    def __init__(self):
        self.hz: Angle = Angle()
        self.v: Angle = Angle()
        self.angle_accuracy: Angle = Angle()
        self.angle_time: int = 0
        self.cross_incline: Angle = Angle()
        self.length_incline: Angle = Angle()
        self.accuracy_incline: Angle = Angle()
        self.incline_time: int = 0
        self.face_def: int = 0

    def __str__(self):
        return "[hz: " + str(self.hz) + ", v: " + str(self.v) + " , angle_accuracy: " + str(self.angle_accuracy) + \
               ", angle_time: " + str(self.angle_time) + ", cross_incline: " + str(self.cross_incline) +\
               ", length_incline: " + str(self.length_incline) + ", accuracy_incline: " + str(self.accuracy_incline) + "]"

class Transformation(object):
    def __init__(self, source_points, targets : dict):
        """
        source_points: Liste von Koordinaten im lokalen System
        targets: Dict von Koordinaten im Zielsystem
        """

        temp_source_points = []
        temp_target_points = []

        # Alle Punkte die in beiden Systemen vorhanden sind, werden für die Transformation verwendend.
        for ls in source_points:
            if ls.pkt_nr in targets:
                zs = targets[ls.pkt_nr]
                temp_source_points.append(ls.get_array())
                temp_target_points.append(zs.get_array())

        self.source_points = np.array(temp_source_points)
        self.target_points = np.array(temp_target_points)

        # Ziel ist es, eine lineare Beziehung der Form
        # [X_target, Y_target, Z_target] = A * [x, y, z, 1]^T
        # über eine affine Transformation zu ermitteln.
        # Dazu erweitern wir die Punktmatrix um eine Spalte mit Einsen (Homogenisierung).
        n = self.source_points.shape[0]  # Anzahl der Punkte
        A = np.hstack([self.source_points, np.ones((n, 1))])  # Matrix der Form (n,4) mit Spalte [x, y, z, 1]

        # Für jede Zielkoordinate (X, Y, Z) wird ein separates lineares Gleichungssystem gelöst.
        # Gesucht ist jeweils der 4-Parameter-Vektor, der die affine Abbildung in X, Y, Z beschreibt.
        # Die Funktion lstsq löst das über das kleinste Fehlerquadrat (Least Squares).
        self.X_params, _, _, _ = np.linalg.lstsq(A, self.target_points[:, 0], rcond=None)  # Parameter für X-Richtung
        self.Y_params, _, _, _ = np.linalg.lstsq(A, self.target_points[:, 1], rcond=None)  # Parameter für Y-Richtung
        self.Z_params, _, _, _ = np.linalg.lstsq(A, self.target_points[:, 2], rcond=None)  # Parameter für Z-Richtung

        source_station = Coordinate("Standpunkt", 0,0,0)
        self.station_postion = self.transform(source_station)


    def transform(self, point : Coordinate):
        """
        Transformiert einen Punkt im lokalen System ins globale System.
        """
        p = np.array([point.get_homogene_array()])
        x_t = p @ self.X_params  # Transformierte X-Koordinaten berechnen
        y_t = p @ self.Y_params  # Transformierte Y-Koordinaten berechnen
        z_t = p @ self.Z_params  # Transformierte Z-Koordinaten berechnen
        c = Coordinate(point.pkt_nr, y_t[0], x_t[0], z_t[0])
        return c

    def compute_rmse(self):
        """
        Berechnet den RMSE zwischen den transformierten und Zielpunkten.
        """
        n = self.source_points.shape[0]
        A = np.hstack([self.source_points, np.ones((n, 1))])
        transformed = np.vstack([
            A @ self.X_params,
            A @ self.Y_params,
            A @ self.Z_params
        ]).T
        residuals = transformed - self.target_points
        mse = np.mean(residuals ** 2)
        return np.sqrt(mse)
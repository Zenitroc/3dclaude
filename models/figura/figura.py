"""Figura chibi (cabezon) de un chico con barba, chaqueta y botas, sobre peana redonda.

Referencia: reference.png (una sola vista, frontal con giro ~20 grados hacia la
derecha de la imagen y camara ~7 grados por encima). reference_clean.png es la
misma imagen con el fondo (que tiene un halo claro) sustituido por blanco puro,
para que compare_views pueda recortar la silueta.

Respuestas de la ronda de preguntas (2026-11-12):
- Tamano: 120 mm de alto total con la peana, boquilla 0.4.
- Una sola pieza, un color: un STL macizo (se puede pintar a mano).
- Detalle: pelo en pinchos y rasgos de la cara (ojos, cejas, nariz, sonrisa,
  barba en relieve). SIN detalles de ropa (bolsillos, cremallera, cordones).
- Cambios para imprimir aprobados: brazos fundidos con el cuerpo; cuello/barba
  con apoyo a 45 grados bajo la cabeza. (Chaflan de peana: NO aprobado -> peana
  cilindrica recta.)

Unidades de diseno = pixeles de la referencia (z = 1356 - fila de la imagen,
x = columna - 541). Se escala a 120 mm al final. El frente mira a -Y, Z arriba.
Vista de la hoja: "front" (unica).
"""

import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE), os.environ.get("PRINT3D_SCRIPTS", "")]
from shapes import *  # noqa: E402,F401,F403

STEM = Path(__file__).stem
DESIGN_H = 1326.0  # hair tip height in reference pixels
HEIGHT = 120.0
S = HEIGHT / DESIGN_H


def mm(final: float) -> float:
    return final / S


# ---------------------------------------------------------------- helpers

def ellipse_loft(sections, yaw: float = 0.0) -> Part:
    """Loft through horizontal ellipses: (z, cx, cy, a, b)."""
    return loft([Plane.XY.offset(z) * Pos(cx, cy) * Rot(0, 0, yaw) * Ellipse(a, b) for z, cx, cy, a, b in sections])


def circle_loft(sections) -> Part:
    """(z, cx, cy, r) rows, bottom to top."""
    return loft([Plane.XY.offset(z) * Pos(cx, cy) * Circle(r) for z, cx, cy, r in sections])


def egg(center, a: float, b: float, c: float, t0: float = -0.96, t1: float = 0.96) -> Part:
    """Ellipsoid as a loft of horizontal ellipses with tiny flat caps (tessellates
    watertight; the revolved-and-scaled ellipsoid left holes at its poles)."""
    cx, cy, cz = center
    ts = [t0 + (t1 - t0) * i / 10 for i in range(11)]
    ts = [math.sin(math.pi / 2 * t) for t in ts]  # denser near the poles
    return loft([Plane.XY.offset(cz + c * t) * Pos(cx, cy) * Ellipse(a * math.sqrt(1 - t * t), b * math.sqrt(1 - t * t))
                 for t in ts])


def poly_prism(points) -> Part:
    """Front-view (x, z) polygon pushed through along Y."""
    return prism_y(Sketch() + make_face(Polyline(*points, close=True)))


def cone_between(base: Vector, tip: Vector, r: float) -> Part:
    axis = tip - base
    return Plane(origin=base, z_dir=axis) * Cone(r, 4, axis.length, align=(Align.CENTER, Align.CENTER, Align.MIN))


# ---------------------------------------------------------------- base and boots

BASE_R, BASE_H = 354.0, 59.0


def base() -> Part:
    disc = Cylinder(BASE_R, BASE_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return fillet(disc.edges().group_by(Axis.Z)[-1], 8)


def boot(cx: float, cy: float, toe_deg: float) -> Part:
    """Boot sitting on the base: sole + half-ellipsoid upper + ankle. toe_deg is the
    direction of the toe measured from -Y towards +X."""
    z0 = BASE_H
    sole = extrude(Plane.XY.offset(z0) * Pos(40, 0) * Ellipse(128, 66), amount=24)
    upper = egg((40, 0, z0 + 12), 122, 62, 82, 0.0, 0.97)
    ankle = Pos(-20, 0, z0) * Cylinder(55, 115, align=(Align.CENTER, Align.CENTER, Align.MIN))
    foot = sole + upper + ankle  # built along +X
    # +X -> toe direction: rotate so +X points to (sin t, -cos t)
    return Pos(cx, cy, 0) * Rot(0, 0, toe_deg - 90) * foot


# ---------------------------------------------------------------- legs, torso, arms

LEG_L = [(75, -140, -37, 52), (146, -141, -10, 56), (206, -128, -8, 62), (266, -109, -6, 63),
         (326, -94, -4, 76), (390, -78, 0, 88)]
LEG_R = [(75, 80, -2, 52), (146, 82, 12, 60), (206, 72, 8, 60), (266, 74, 5, 62), (326, 78, 2, 74),
         (390, 70, 0, 88)]

TORSO_YAW = 10.0
# (z, cx, cy, a, b)
TORSO = [(350, -10, 0, 152, 100), (385, -14, 0, 172, 112), (420, -18, 0, 178, 116), (480, -22, 0, 172, 116),
         (560, -30, 0, 166, 114), (640, -40, 0, 158, 108), (695, -45, 0, 140, 98), (735, -35, 0, 95, 80)]


def arms() -> Part:
    v = Vector
    left = (capsule(v(-212, -10, 690), v(-272, -20, 548), 62) + capsule(v(-272, -20, 548), v(-185, -40, 472), 50)
            + capsule(v(-272, -20, 548), v(-200, -10, 560), 60))  # web: arm fused to the body
    right = (capsule(v(98, -22, 660), v(152, -12, 490), 56) + capsule(v(152, -12, 490), v(124, -30, 432), 50)
             + capsule(v(152, -12, 490), v(95, -15, 520), 52) + capsule(v(98, -20, 640), v(112, -20, 520), 52))
    # jacket collar standing up beside the neck (left of the picture)
    collar = capsule(v(-178, 5, 705), v(-140, 15, 768), 34)
    return left + right + collar


def crotch_wedge() -> Part:
    """45-degree inverted V between the legs: the crotch is not a flat ceiling."""
    return loft([Plane.XY.offset(270) * Pos(-8, 0) * Ellipse(5, 35),
                 Plane.XY.offset(330) * Pos(-8, 0) * Ellipse(45, 92),
                 Plane.XY.offset(362) * Pos(-8, 0) * Ellipse(62, 106)])


# ---------------------------------------------------------------- head

HEAD_POS = (-15.0, -15.0, 980.0)
HEAD_YAW, HEAD_ROLL = 20.0, 8.0
# local (z, a, b, yc): half-width, half-depth, depth centre (front is -Y)
HEAD = [(-234, 36, 32, -95), (-207, 78, 72, -70), (-167, 114, 108, -45), (-127, 134, 132, -28),
        (-87, 150, 150, -15), (-47, 168, 165, -5), (-7, 180, 176, 0), (33, 190, 182, 0), (73, 196, 186, 0),
        (113, 210, 192, 5), (153, 214, 194, 5), (193, 204, 186, 8), (233, 184, 170, 10), (262, 150, 140, 12),
        (280, 100, 95, 12), (288, 55, 50, 12)]
HAIR_MASS = (0.0, 8.0, 172.0, 204.0, 190.0, 128.0)  # centre x, y, z and half-axes a, b, c (local)
HAIR_CREST = (42.0, -5.0, 245.0, 118.0, 128.0, 85.0)  # quiff rising higher on the right


def head_shape(grow: float = 0.0, rows=HEAD) -> Part:
    return loft([Plane.XY.offset(z) * Pos(0, yc) * Ellipse(a + grow, b + grow) for z, a, b, yc in rows])


def head_interp():
    from scipy.interpolate import PchipInterpolator
    zs = [r[0] for r in HEAD]
    return tuple(PchipInterpolator(zs, [r[i] for r in HEAD]) for i in (1, 2, 3))


def surface_point(z: float, theta: float, inset: float = 0.0):
    """Point on the head at local height z and angle theta (0 = +X, -90 = front),
    plus the outward horizontal normal."""
    fa, fb, fy = head_interp()
    a, b, yc = float(fa(z)) - inset, float(fb(z)) - inset, float(fy(z))
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    n = Vector(c / a, s / b, 0).normalized()
    return Vector(a * c, yc + b * s, z), n


def dome(params) -> Part:
    """Upper half of an ellipsoid as a loft (an ellipsoid cut at its equator tessellated with holes)."""
    cx, cy, cz, a, b, c = params
    rows = []
    for t in (0.0, 0.25, 0.45, 0.62, 0.76, 0.87, 0.94):
        k = math.sqrt(1 - t * t)
        rows.append(Plane.XY.offset(cz + c * t) * Pos(cx, cy) * Ellipse(a * k, b * k))
    return loft(rows)


def hair_mass() -> Part:
    return dome(HAIR_MASS) + dome(HAIR_CREST)


def spikes_on(params, rings, x_lo: float, x_hi: float) -> list[Part]:
    """Cones growing out of a dome, at most 32 deg from vertical (printable
    underside), leaning to +X; longer towards +X like the picture's quiff."""
    cx, cy, cz, a, b, c = params
    out = []
    max_tilt = math.radians(32)
    for k, (alpha, count, length, r) in enumerate(rings):
        al = math.radians(alpha)
        for i in range(count):
            be = 2 * math.pi * (i + 0.5 * (k % 2)) / count
            p = Vector(cx + a * math.sin(al) * math.cos(be), cy + b * math.sin(al) * math.sin(be), cz + c * math.cos(al))
            n = Vector((p.X - cx) / a**2, (p.Y - cy) / b**2, (p.Z - cz) / c**2).normalized()
            d = (n + Vector(0.2, -0.05, 0.6)).normalized()
            tilt = math.acos(max(-1.0, min(1.0, d.Z)))
            if tilt > max_tilt:
                h = Vector(d.X, d.Y, 0).normalized()
                d = h * math.sin(max_tilt) + Vector(0, 0, math.cos(max_tilt))
            side = min(1.0, max(0.0, (p.X - x_lo) / (x_hi - x_lo)))
            ln = length * (0.8 + 0.4 * side) * (0.85 + 0.3 * ((i * 7 + k * 3) % 5) / 4)
            base = p - n * 10
            out.append(cone_between(base, base + d * ln, r))
    return out


def spikes() -> list[Part]:
    main = spikes_on(HAIR_MASS, [(18, 5, 60, 19), (32, 10, 60, 19), (46, 15, 58, 18), (59, 20, 54, 18),
                                 (71, 24, 48, 17), (82, 26, 40, 16)], -204, 204)
    crest = spikes_on(HAIR_CREST, [(0, 1, 66, 20), (22, 6, 64, 20), (42, 11, 62, 19), (62, 15, 56, 18)], -60, 160)
    return main + crest


HAIRLINE = [(-300, 60), (-212, 82), (-170, 140), (-120, 188), (-60, 185), (0, 192), (60, 186), (120, 186),
            (170, 140), (212, 82), (300, 60), (300, 420), (-300, 420)]


def hairline(drop: float) -> list:
    return [(x, z - drop) if z < 400 else (x, z) for x, z in HAIRLINE]
BEARD = [(-300, 70), (-218, 70), (-205, -10), (-175, -62), (-135, -88), (-95, -76), (-50, -58), (0, -52),
         (50, -58), (95, -76), (135, -88), (175, -62), (205, -10), (218, 70), (300, 70), (300, -320), (-300, -320)]
EYE_X, EYE_Z = 86.0, 32.0


def eye_sketch(sx: int) -> Sketch:
    """Almond: intersection of two big circles."""
    cx = sx * EYE_X
    upper = Pos(cx, EYE_Z - 40) * Circle(66)
    lower = Pos(cx, EYE_Z + 34) * Circle(62)
    return upper & lower


def head() -> Part:
    h = head_shape()
    front = front_of(0)
    # two steps so the hair edge is a staircase of 0.5 mm, not a 1 mm ledge
    hair = (head_shape(6) & poly_prism(hairline(-8))) + (head_shape(12) & poly_prism(hairline(-16)))
    hair += hair_mass().fuse(*spikes())
    beard = (head_shape(11) & poly_prism(BEARD) & front_of(70)) + \
        (head_shape(22) & poly_prism([(x, z - 12) if z > -300 else (x, z) for x, z in BEARD]) & front_of(70))
    brows = strokes([CenterArc((sx * 85, -25), 120, 65, 50) for sx in (-1, 1)], 24)
    brows = head_shape(11) & prism_y(brows) & front
    nose = egg((4, -170, -22), 30, 26, 42)
    ears = egg((-196, 28, 25), 42, 50, 74) + egg((196, 28, 25), 42, 50, 74)
    # approved: the beard's underside rests on a 55-degree throat, not on air
    chin_rest = loft([Plane.XY.offset(-340) * Pos(0, -40) * Ellipse(40, 40),
                      Plane.XY.offset(-196) * Pos(0, -62) * Ellipse(112, 104)], ruled=True)
    hd = h + hair + beard + brows + nose + ears + chin_rest
    # engraved features
    eyes = prism_y(eye_sketch(-1) + eye_sketch(1)) & front & behind(-260)
    eye_cut = (eyes - head_shape(-10)) & front
    iris = prism_y(Pos(-EYE_X - 8, EYE_Z - 2) * Circle(19) + Pos(EYE_X - 8, EYE_Z - 2) * Circle(19))
    iris_cut = (iris - head_shape(-22)) & front & behind(-260)
    smile = strokes([CenterArc((5, -40), 70, 225, 90)], 14)
    smile_cut = (prism_y(smile) - head_shape(0)) & front  # cut through the beard down to the skin
    hd = hd.cut(eye_cut, iris_cut, smile_cut)
    return Pos(*HEAD_POS) * Rot(0, HEAD_ROLL, 0) * Rot(0, 0, HEAD_YAW) * hd


def neck_support() -> Part:
    """Approved: neck + 45-degree support under the big head (chin / back of skull)."""
    hx, hy, hz = HEAD_POS
    top = Plane.XY.offset(880) * Pos(hx + 12, hy - 5) * Ellipse(130, 130)
    bottom = Plane.XY.offset(680) * Pos(-15, 0) * Ellipse(85, 80)
    return loft([bottom, top])


def build() -> dict[str, Part]:
    body = base()
    body += boot(-148, -55, -24) + boot(95, -15, 50)
    body += circle_loft(LEG_L) + circle_loft(LEG_R)
    body += ellipse_loft(TORSO, TORSO_YAW)
    body += arms()
    body += crotch_wedge()
    body += neck_support()
    body += head()
    k = HEIGHT / body.bounding_box().max.Z  # spike tips set the final height
    return {"mono": scaled(body, k), "white": scaled(body, k)}


if __name__ == "__main__":
    fine = "--fine" in sys.argv
    tol = dict(tolerance=0.01, angular_tolerance=0.1) if fine else dict(tolerance=0.05, angular_tolerance=0.3)
    export_parts(build(), HERE, STEM, **tol)

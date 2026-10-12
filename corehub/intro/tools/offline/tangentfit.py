"""Direction of the tube at the camera, frame by frame, from the rails next to the camera.

The camera rides on the tube axis, so the four rails pass it at the same four places in every frame; how they run on
from there shows the direction (tangent) of the tube at the camera and how tightly it curves. In a bend the view
direction and the tangent differ (the film's camera looks into the bend), and the tangent is what the path needs.

    import tangentfit as TF, railfit as RF
    rd = RF.load('rust_a')
    rows = TF.scan(rd, 998, rho=34 / 623.0)       # for the bend that starts at frame 998: [(frame, moment, angle, curvature, score)]
angle: degrees turned from the old axis toward the new one; curvature: 1 / radius in solver units."""
import math
import numpy as np
import railfit as RF, ride as RD


def local_rails(C, d0, d1, alpha, kappa, rho, back=1.5, ahead=14.0, ds=0.35):
    """rails of a tube through C whose tangent is d0 turned by alpha toward d1 and which curves on toward d1 with
    curvature kappa (0 = straight); from `back`*rho behind the camera to `ahead`*rho in front. -> [(points, tangents)]"""
    T0 = math.cos(alpha) * d0 + math.sin(alpha) * d1; N0 = -math.sin(alpha) * d0 + math.cos(alpha) * d1; B = np.cross(d0, d1)
    u = np.arange(-back * rho, ahead * rho + 1e-9, ds * rho)
    if abs(kappa) < 1e-9:
        Cc = C[None, :] + u[:, None] * T0[None, :]; T = np.repeat(T0[None, :], len(u), 0); N = np.repeat(N0[None, :], len(u), 0)
    else:
        r = 1.0 / kappa; ph = u / r
        Cc = C[None, :] + r * (np.sin(ph)[:, None] * T0[None, :] + (1 - np.cos(ph))[:, None] * N0[None, :])
        T = np.cos(ph)[:, None] * T0[None, :] + np.sin(ph)[:, None] * N0[None, :]
        N = -np.sin(ph)[:, None] * T0[None, :] + np.cos(ph)[:, None] * N0[None, :]
    out = []
    for s1 in (1, -1):
        for s2 in (1, -1):
            out.append((Cc + (s1 * N + s2 * B[None, :]) * rho / math.sqrt(2.0), T))
    return out


def scan(rd, key, rho, width=None, pre=2, post=2, alphas=None, kappas=None, ahead=14.0, verbose=True):
    width = width or rho * 2.0 / 34.0
    a0, a, b, b1 = RF._bend_frames(rd, key)
    st = [x for x in rd['sections'] if x[0] == 'straight']
    cur = next(x for x in st if x[2] + 1 == key); nxt = st[st.index(cur) + 1]
    d0 = np.array(RD.AXES[cur[3]], dtype=float); d1 = np.array(RD.AXES[nxt[3]], dtype=float)
    alphas = alphas if alphas is not None else np.radians(np.arange(-12, 103, 2.0))
    kappas = kappas if kappas is not None else np.array([-0.04, -0.02, 0.0, 0.02, 0.04, 0.06, 0.08, 0.11, 0.15]) / rho
    path, s_of, cams, info = RF.cameras(rd, {}, range(a - pre, b + post + 1))
    rows = []; maps = {}
    for n, mo, C, R, s in cams:
        img = RF.moment_image(n, mo); M = np.zeros((len(kappas), len(alphas)))
        for i, k in enumerate(kappas):
            for j, al in enumerate(alphas):
                tot, w = RF.rail_response(img, local_rails(np.zeros(3), d0, d1, al, k, rho, ahead=ahead), np.zeros(3), R, width, zmin=0.3 * rho)
                M[i, j] = tot / w if w > 30 else 0.0
        i, j = np.unravel_index(np.argmax(M), M.shape)
        f = O_forward(R); view = math.degrees(math.atan2(float(f @ d1), float(f @ d0)))
        rows.append((n, mo, math.degrees(alphas[j]), kappas[i], M[i, j], view)); maps[(n, mo)] = M
        if verbose: print('%d%s  view %6.1f  tangent %6.1f  curvature*rho %5.2f  score %.1f   (best per curvature: %s)' % (n, mo, view, math.degrees(alphas[j]), kappas[i] * rho, M[i, j], ' '.join('%.0f' % math.degrees(alphas[x]) for x in M.argmax(axis=1))))
    return rows, maps


def O_forward(R):
    return R[2]

"""Splits a native frame of the 2009 video (1280x720 luma) into the two moments it contains.

Every frame of the film is a blend of two renders half a frame apart (a 60 Hz master turned into 30 fps). Line y is
    v(y) = (0.5 + s e(y)) * LATE + (0.5 - s e(y)) * EARLY,   s = +1 on even lines, -1 on odd lines
with a fixed envelope e(y): 22 lobes over the frame height (period 32.707 lines) with a plateau of 0.177 and bands of
pure 50/50 blend between them. A line minus the mean of its two neighbours is s * q(y) * (LATE - EARLY) with
q = e + mean of the neighbours' e; q was measured by regression over 105 frames with strong motion (fields/q.npy,
plateau 0.355). Where q is large enough the difference of the two moments is recovered per pixel; in the 50/50 bands
it is interpolated vertically from the lobes above and below, so the split is exact on flat areas and approximate
where a moving edge crosses a band (valid_lines() tells which lines are resolved directly)."""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
_Q = _E = None
QMIN = 0.20


def tables():
    global _Q, _E
    if _Q is None:
        _Q = np.maximum(np.load(os.path.join(HERE, 'fields', 'q.npy')), 0); _Q[0] = _Q[1]; _Q[-1] = _Q[-2]
        _E = np.load(os.path.join(HERE, 'fields', 'e.npy'))
    return _Q, _E


def valid_lines(qmin=QMIN):
    """bool[720]: lines whose two moments are separated directly (not interpolated)"""
    return tables()[0] >= qmin


def split(Yf, qmin=QMIN, smooth=0.7):
    """Yf: luma [720, 1280] float -> (early, late) luma images of the same size"""
    q, e = tables()
    H = Yf.shape[0]
    s = np.where(np.arange(H) % 2 == 0, 1.0, -1.0)
    up = np.vstack([Yf[1:2], Yf[:-1]]); dn = np.vstack([Yf[1:], Yf[-2:-1]])
    u = 0.5 * (up + dn)                                  # the opposite line type at the same height
    ok = q >= qmin
    D = np.zeros_like(Yf)                                 # LATE - EARLY
    D[ok] = (Yf[ok] - u[ok]) * (s[ok] / q[ok])[:, None]
    if smooth:                                            # average along the resolved runs only (noise is amplified up to 1/qmin)
        Ds = D.copy(); W = ok.astype(float)[:, None] * np.ones((1, Yf.shape[1]))
        num = gaussian_filter1d(D * W, smooth, axis=0, mode='nearest'); den = gaussian_filter1d(W, smooth, axis=0, mode='nearest')
        Ds[ok] = (num / np.maximum(den, 1e-6))[ok]; D = Ds
    idx = np.where(ok)[0]; bad = np.where(~ok)[0]
    lo = np.clip(np.searchsorted(idx, bad) - 1, 0, len(idx) - 1); hi = np.clip(lo + 1, 0, len(idx) - 1)
    ya, yb = idx[lo], idx[hi]
    w = np.where(yb > ya, (bad - ya) / np.maximum(yb - ya, 1), 0.0); w = np.clip(w, 0, 1)
    D[bad] = D[ya] * (1 - w)[:, None] + D[yb] * w[:, None]
    en = 0.5 * (np.r_[e[1], e[:-1]] + np.r_[e[1:], e[-2]])
    total = Yf + u - (s * (e - en))[:, None] * D          # LATE + EARLY
    return 0.5 * (total - D), 0.5 * (total + D)


def load_native(path):
    return np.asarray(Image.open(path).convert('L'), dtype=np.float64)


def to_img(Yf, size=(1280, 800)):
    return Image.fromarray(np.clip(Yf, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)

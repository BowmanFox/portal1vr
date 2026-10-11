"""compare ring measurements between the video and the offline preview with the same fitter.
usage (as a module): from ringcmp import RC; rc = RC('dm'); rc.cmp(t, [(label, (cx,cy), r_lo, r_hi, polarity), ...])"""
import numpy as np, cv2
from preview import Preview
from ringtrack import fit_ring, gray_frame, frame_of


class RC:
    def __init__(self, tag, **kw):
        self.P = Preview(tag, quiet=True, **kw)

    def render_gray(self, t, cam=None):
        im = self.P.render(t, 640, 400, cam=cam)
        return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY).astype(np.float32)

    def cmp(self, t, specs, tv=None, show=True, **kw):
        """tv: video time to compare with (default t)"""
        gv = gray_frame(frame_of(t if tv is None else tv)); gr = self.render_gray(t)
        out = []
        for label, c0, lo, hi, pol in specs:
            a = fit_ring(gv, c0, lo, hi, pol, **kw); b = fit_ring(gr, c0, lo, hi, pol, **kw)
            out.append((label, a, b))
            if show:
                f = lambda r: 'none' if r is None else 'c (%.1f, %.1f) r %.1f [n %d rms %.1f]' % (r['cx'], r['cy'], r['r'], r['n'], r['rms'])
                d = '' if (a is None or b is None) else '   d c (%+.1f, %+.1f) r %+.1f (%+.1f%%)' % (b['cx'] - a['cx'], b['cy'] - a['cy'], b['r'] - a['r'], 100 * (b['r'] / a['r'] - 1))
                print('%6.2f %-22s video %s | preview %s%s' % (t, label, f(a), f(b), d))
        return out

"""in-plane rotation between the video and the preview from edge orientations (straight edges such as the petal gaps).
rot_offset(gv, gr, mask) -> degrees the preview must be rotated (counter-clockwise on screen) to match the video"""
import numpy as np, cv2


def orient_hist(g, mask=None, bins=720):
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    mag = np.hypot(gx, gy); ang = (np.degrees(np.arctan2(gy, gx)) % 180.0)        # edge normal direction modulo 180
    if mask is not None: mag = mag * mask
    mag = np.where(mag > 20, mag, 0)
    h, _ = np.histogram(ang, bins=bins, range=(0, 180), weights=mag)
    return h / (h.sum() + 1e-9)


def rot_offset(gv, gr, mask=None, max_deg=8.0, bins=720):
    hv = orient_hist(gv, mask, bins); hr = orient_hist(gr, mask, bins)
    k = np.ones(5) / 5; hv = np.convolve(np.r_[hv[-2:], hv, hv[:2]], k, 'valid'); hr = np.convolve(np.r_[hr[-2:], hr, hr[:2]], k, 'valid')
    best = None
    for s in range(-int(max_deg * bins / 180), int(max_deg * bins / 180) + 1):
        c = float((hv * np.roll(hr, s)).sum())
        if best is None or c > best[0]: best = (c, s)
    return best[1] * 180.0 / bins

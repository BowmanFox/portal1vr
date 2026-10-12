"""Radius-versus-frame diagram of everything that is circular about a point of the picture (the tube rings ahead when the
camera looks along a straight tube): each row is one moment of the film, each column a radius; a ring approaching at
constant speed draws a curve with 1/r falling linearly.
usage: kymo.py first last [--cx 319.5 --cy 199.5] [--rmax 320] [--moments EL] [--out file] [--edges]
   (640x400 pixel units; --edges shows the radial brightness steps instead of the brightness)"""
import argparse, numpy as np, cv2
ap = argparse.ArgumentParser()
ap.add_argument('first', type=int); ap.add_argument('last', type=int); ap.add_argument('--cx', type=float, default=319.5); ap.add_argument('--cy', type=float, default=199.5)
ap.add_argument('--rmax', type=float, default=320.0); ap.add_argument('--moments', default='EL'); ap.add_argument('--out'); ap.add_argument('--edges', action='store_true')
ap.add_argument('--rowh', type=int, default=10)
a = ap.parse_args()
rs = np.arange(4, a.rmax, 0.5); angs = np.linspace(0, 2 * np.pi, 720, endpoint=False)


def profile(n, mo, cx, cy):
    g = cv2.imread('/home/claude/data/moments/%s/f%04d.jpg' % (mo, n), cv2.IMREAD_GRAYSCALE).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    xs = (cx + rs[None, :] * np.cos(angs)[:, None]) * 2 + 0.5; ys = (cy + rs[None, :] * np.sin(angs)[:, None]) * 2 + 0.5
    v = cv2.remap(g, xs.astype(np.float32), ys.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1)
    ok = v >= 0
    return np.where(ok, v, 0).sum(axis=0) / np.maximum(ok.sum(axis=0), 1)


if __name__ == '__main__':
    rows = []; labels = []
    for n in range(a.first, a.last + 1):
        for mo in a.moments:
            rows.append(profile(n, mo, a.cx, a.cy)); labels.append('%d%s' % (n, mo))
    K = np.array(rows)
    if a.edges:
        K = np.abs(np.gradient(K, axis=1)) * 12
    sx = 3; img = cv2.resize(np.clip(K * 2.2, 0, 255).astype(np.uint8), (K.shape[1] * sx // 2, K.shape[0] * a.rowh), interpolation=cv2.INTER_NEAREST)
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for i, l in enumerate(labels):
        if i % max(1, 14 // a.rowh) == 0: cv2.putText(img, l, (2, i * a.rowh + a.rowh - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 255), 1)
    for r in range(20, int(a.rmax), 20):
        x = int((r - 4) * 2 * sx / 2); cv2.line(img, (x, 0), (x, 5), (0, 255, 0), 1)
        if r % 40 == 0: cv2.putText(img, str(r), (x + 2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 0), 1)
    out = a.out or 'out/kymo_%d_%d.png' % (a.first, a.last)
    cv2.imwrite(out, img); print(out, img.shape)

"""Minimal reader for compiled Source models (MDL v44-49 + VVD v4 + VTX v7): LOD 0 triangles with material names.
Only what the offline preview needs: positions in the reference pose, normals, uvs, per-mesh material (per skin)."""
import struct, os
import numpy as np


def _cstr(b, off):
    end = b.index(b'\0', off)
    return b[off:end].decode('latin-1')


def read_model(mdl_path):
    """-> dict(cdmaterials=[..], skins=[[material name per skinref] ...], tris=[(skinref, verts[3,3], normals[3,3], uvs[3,2])])"""
    base = mdl_path[:-4]
    mdl = open(mdl_path, 'rb').read()
    assert mdl[:4] == b'IDST', mdl[:4]
    version = struct.unpack_from('<i', mdl, 4)[0]
    (numtextures, textureindex, numcdtextures, cdtextureindex, numskinref, numskinfamilies, skinindex,
     numbodyparts, bodypartindex) = struct.unpack_from('<9i', mdl, 204)
    textures = []
    for i in range(numtextures):
        o = textureindex + i * 64
        textures.append(_cstr(mdl, o + struct.unpack_from('<i', mdl, o)[0]).lower().replace('\\', '/'))
    cds = []
    for i in range(numcdtextures):
        o = struct.unpack_from('<i', mdl, cdtextureindex + i * 4)[0]
        cds.append(_cstr(mdl, o).lower().replace('\\', '/').strip('/'))
    skins = []
    for f in range(numskinfamilies):
        refs = struct.unpack_from('<%dh' % numskinref, mdl, skinindex + f * numskinref * 2)
        skins.append([textures[r] if 0 <= r < len(textures) else '' for r in refs])
    # VVD
    vvd = open(base + '.vvd', 'rb').read()
    assert vvd[:4] == b'IDSV'
    vver, vchk, numlods = struct.unpack_from('<3i', vvd, 4)
    lodverts = struct.unpack_from('<8i', vvd, 16)
    numfix, fixstart, vstart, tstart = struct.unpack_from('<4i', vvd, 48)
    raw = np.frombuffer(vvd, dtype=np.dtype([('w', '<f4', 3), ('b', 'u1', 3), ('nb', 'u1'), ('p', '<f4', 3), ('n', '<f4', 3), ('uv', '<f4', 2)]),
                        count=(tstart - vstart) // 48 if tstart > vstart else lodverts[0], offset=vstart)
    if numfix:
        parts = []
        for i in range(numfix):
            lod, src, cnt = struct.unpack_from('<3i', vvd, fixstart + i * 12)
            if lod >= 0: parts.append(raw[src:src + cnt])
        verts = np.concatenate(parts)
    else:
        verts = raw
    # VTX
    vtx = open(base + '.dx90.vtx', 'rb').read()
    (tver, cache, mbs, mbt, mbv, chk, nlods, mrl, nbp, bpo) = struct.unpack_from('<iiHHiiiiii', vtx, 0)
    tris = []
    for bp in range(numbodyparts):
        mo = bodypartindex + bp * 16
        _, nummodels, _, modelindex = struct.unpack_from('<4i', mdl, mo)
        vbp = bpo + bp * 8
        vnm, vmo = struct.unpack_from('<2i', vtx, vbp)
        # body group: only the first model of each part is drawn by default
        for mi in range(min(nummodels, 1)):
            mm = mo + modelindex + mi * 148
            nummeshes, meshindex, numvertices, vertexindex = struct.unpack_from('<4i', mdl, mm + 72)
            vmod = vbp + vmo + mi * 8
            vnl, vlo = struct.unpack_from('<2i', vtx, vmod)
            vlod = vmod + vlo          # LOD 0
            vnmesh, vmesho = struct.unpack_from('<2i', vtx, vlod)
            for me in range(nummeshes):
                ms = mm + meshindex + me * 116
                material, _, mnumv, voff = struct.unpack_from('<4i', mdl, ms)
                vmesh = vlod + vmesho + me * 9
                nsg, sgo = struct.unpack_from('<2i', vtx, vmesh)
                for sg in range(nsg):
                    sgp = vmesh + sgo + sg * (25 if version < 49 else 33)
                    nv, vo, ni, io, ns, so = struct.unpack_from('<6i', vtx, sgp)
                    vt = np.frombuffer(vtx, dtype=np.dtype([('bw', 'u1', 3), ('nb', 'u1'), ('id', '<u2'), ('bid', 'i1', 3)]), count=nv, offset=sgp + vo)
                    idx = np.frombuffer(vtx, dtype='<u2', count=ni, offset=sgp + io)
                    for s in range(ns):
                        sp = sgp + so + s * 27
                        sni, sio, snv, svo = struct.unpack_from('<4i', vtx, sp)
                        flags = vtx[sp + 18]
                        ii = idx[sio:sio + sni]
                        if flags & 1:      # triangle list
                            t3 = ii[:len(ii) // 3 * 3].reshape(-1, 3)
                        else:              # triangle strip
                            t3 = np.array([(ii[k], ii[k + 1], ii[k + 2]) if k % 2 == 0 else (ii[k + 1], ii[k], ii[k + 2]) for k in range(len(ii) - 2)])
                        if len(t3) == 0: continue
                        g = vertexindex // 48 + voff + vt['id'][t3]
                        g = np.clip(g, 0, len(verts) - 1)
                        P = verts['p'][g]; N = verts['n'][g]; UV = verts['uv'][g]
                        for k in range(len(t3)): tris.append((material, P[k], N[k], UV[k]))
    return dict(cdmaterials=cds, skins=skins, textures=textures, tris=tris, version=version)


if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        m = read_model(p)
        P = np.array([t[1] for t in m['tris']]).reshape(-1, 3)
        print(os.path.basename(p), 'v%d' % m['version'], 'tris', len(m['tris']), 'cd', m['cdmaterials'], 'skins', m['skins'][:2],
              'bbox', P.min(0).round(1), P.max(0).round(1))

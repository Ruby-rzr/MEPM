#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tableau d'ecart normalise entre deux versions de reference.

Format impose par la phase 5 : chaque commit qui change un nombre s'accompagne
d'un tableau donnant les cas touches sur 262, les champs touches, l'ecart
relatif minimal et maximal par champ, et pour les cas EC3515 en conique la
valeur avant et apres en kPa aux vitesses 10, 50, 100, 200 et 300 mm/s.

Ces tableaux servent a justifier les corrections hors contexte. Ils sont donc
autonomes et ne supposent rien de connu du lecteur.

Usage :
    python3 tests/tableau_ecart.py <version_avant> <version_apres> "<titre>"

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""
import json, sys
import numpy as np
sys.path.insert(0, '/home/user/MEPM')
from tests import reference_io
from tests.reference_io import CHAMPS_NUMERIQUES

VITESSES = [10.0, 50.0, 100.0, 200.0, 300.0]

def tableau(avant, apres, titre):
    a = reference_io.charge(avant)['resultats']
    b = reference_io.charge(apres)['resultats']
    print("=" * 78)
    print(titre)
    print(f"  {avant}  ->  {apres}")
    print("=" * 78)

    cas_touches, champs = set(), {}
    for ident in sorted(set(a) & set(b)):
        for champ in CHAMPS_NUMERIQUES:
            sa, sb = a[ident]['sorties'], b[ident]['sorties']
            if champ not in sa or champ not in sb: continue
            x = np.asarray(sa[champ], float).ravel()
            y = np.asarray(sb[champ], float).ravel()
            if x.shape != y.shape: continue
            meme = (np.isnan(x) & np.isnan(y)) | (x == y)
            if meme.all(): continue
            cas_touches.add(ident)
            comparable = ~np.isnan(x) & ~np.isnan(y) & (x != 0)
            if comparable.any():
                rel = np.abs(y[comparable] - x[comparable]) / np.abs(x[comparable])
                lo, hi = float(rel.min()), float(rel.max())
            else:
                lo = hi = float('nan')
            d = champs.setdefault(champ, [0, np.inf, -np.inf])
            d[0] += 1; d[1] = min(d[1], lo); d[2] = max(d[2], hi)

    print(f"\n  Cas touches : {len(cas_touches)} sur {len(set(a) & set(b))}")
    print(f"\n  {'champ':<8} {'cas':>5} {'ecart relatif min':>20} {'ecart relatif max':>20}")
    print(f"  {'-'*8} {'-'*5} {'-'*20} {'-'*20}")
    for champ in CHAMPS_NUMERIQUES:
        if champ not in champs:
            print(f"  {champ:<8} {0:>5} {'inchange':>20} {'inchange':>20}")
        else:
            n, lo, hi = champs[champ]
            print(f"  {champ:<8} {n:>5} {lo:>20.6e} {hi:>20.6e}")

    print(f"\n  EC3515 en conique, pression P en kPa")
    print(f"  {'materiau':<12} {'v (mm/s)':>9} {'avant':>14} {'apres':>14} {'ecart relatif':>15}")
    print(f"  {'-'*12} {'-'*9} {'-'*14} {'-'*14} {'-'*15}")
    for f in ['EC3515-0%', 'EC3515-8%']:
        k = f'B|{f}|conique'
        v = a[k]['entrees']['v']
        Pa_ = a[k]['sorties']['P_kPa']; Pb_ = b[k]['sorties']['P_kPa']
        for vv in VITESSES:
            i = v.index(vv)
            e = (Pb_[i] - Pa_[i]) / Pa_[i] if Pa_[i] else float('nan')
            print(f"  {f:<12} {vv:>9.0f} {Pa_[i]:>14.4f} {Pb_[i]:>14.4f} {e:>15.3e}")
    print()

if __name__ == "__main__":
    tableau(sys.argv[1], sys.argv[2], sys.argv[3])

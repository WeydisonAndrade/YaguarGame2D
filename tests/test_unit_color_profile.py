"""Arco: RGB do corpo igual a trigger01; fundo preto vira alpha."""
from __future__ import annotations

from PIL import Image

from src.color_profile import apply_yaguar_grade, corrected_path, prepare_bow_color_grades, using_raw_bow_color
from src.config import BOW_GRADE_POSES, YAGUAR_COLOR_PROFILE
from src.player_anim import PLAYER_DIR


def _skin_sat(path):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    sats = []
    lumas = []
    gs = []
    rs = []
    for y in range(int(h * 0.25), int(h * 0.70)):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 200:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            if mx < 30:
                continue
            if r > g >= b - 8 and r - b > 12:
                s = 0 if mx == 0 else (mx - mn) / mx
                luma = 0.3 * r + 0.59 * g + 0.11 * b
                sats.append(s)
                lumas.append(luma)
                gs.append(g)
                rs.append(r)
    return (
        sum(sats) / len(sats) if sats else 0,
        sum(lumas) / len(lumas) if lumas else 0,
        sum(gs) / len(gs) / max(1e-6, sum(rs) / len(rs)) if rs else 0,
    )


def _crushed(path, limit=18):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    n = dark = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 200:
                continue
            n += 1
            if 0.3 * r + 0.59 * g + 0.11 * b < limit:
                dark += 1
    return dark / max(1, n)


def _mean_opaque_rgb(path):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    rs = gs = bs = n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 200:
                continue
            rs += r
            gs += g
            bs += b
            n += 1
    n = max(1, n)
    return rs / n, gs / n, bs / n


def test_originais_do_arco_existem():
    for pose in BOW_GRADE_POSES:
        assert (PLAYER_DIR / f"{pose}.png").is_file()
        assert corrected_path(pose).is_file()


def test_grade_nao_muda_rgb_do_corpo():
    prepare_bow_color_grades(force=True)
    raw_s, raw_l, raw_gr = _skin_sat(PLAYER_DIR / "bow.png")
    bow_s, bow_l, bow_gr = _skin_sat(corrected_path("bow"))
    assert abs(bow_s - raw_s) <= 0.02
    assert abs(bow_l - raw_l) <= 2.0
    assert abs(bow_gr - raw_gr) <= 0.02
    rr, rg, rb = _mean_opaque_rgb(PLAYER_DIR / "bow.png")
    cr, cg, cb = _mean_opaque_rgb(corrected_path("bow"))
    assert abs(rr - cr) <= 1.5
    assert abs(rg - cg) <= 1.5
    assert abs(rb - cb) <= 1.5


def test_alpha_do_grade_permanece_rgba():
    img = apply_yaguar_grade(Image.open(PLAYER_DIR / "bow.png"))
    assert img.mode == "RGBA"
    bands = img.split()
    assert bands[-1].getextrema()[0] == 0
    assert bands[-1].getextrema()[1] == 255


def test_perfil_preserva_trigger01():
    assert YAGUAR_COLOR_PROFILE["ref_poses"] == ("trigger01",)
    assert YAGUAR_COLOR_PROFILE["sharp_ref"] == "trigger01"
    assert YAGUAR_COLOR_PROFILE["preserve_rgb"] is True
    assert YAGUAR_COLOR_PROFILE["target_height"] == 168


def test_tamanho_do_arco_iguala_ataque():
    prepare_bow_color_grades(force=True)
    attack_h = Image.open(PLAYER_DIR / "attack.png").size[1]
    defend_h = Image.open(PLAYER_DIR / "defend.png").size[1]
    assert attack_h == defend_h == 168
    for pose in BOW_GRADE_POSES:
        assert Image.open(corrected_path(pose)).size[1] == 168


def test_pretos_do_arco_permanecem_fechados():
    prepare_bow_color_grades(force=True)
    raw = _crushed(PLAYER_DIR / "bow.png")
    fix = _crushed(corrected_path("bow"))
    assert abs(fix - raw) <= 0.02


def test_nitidez_do_arco_nao_fica_mole():
    from src.color_profile import _laplacian_var
    import numpy as np

    prepare_bow_color_grades(force=True)
    arr = np.asarray(Image.open(corrected_path("bow")).convert("RGBA")).astype(np.float32)
    assert _laplacian_var(arr) >= 3500


def test_comparacao_f4_comeca_desligada():
    assert using_raw_bow_color() is False

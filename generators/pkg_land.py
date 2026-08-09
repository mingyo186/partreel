"""
패키지 랜드패턴 생성기 — 제외 풋프린트 대체용 (REQUIREMENTS §21-C 대체 수입 2차).

Antmicro 물결에서 KiCad 공식 카피로 판정돼 제외된 IC/인덕터 풋프린트를,
**각 제조사 데이터시트의 권장 랜드패턴**(도면 번호·페이지 인용)으로 자체 생성해
대체한다. 치수=사실, 우리 입력으로 우리가 생성 = 우리 저작.

치수 추출: 서브에이전트가 데이터시트 PDF의 랜드패턴 도면을 고배율 렌더로
읽고 내부 기하 정합(간격 산식)까지 교차검증한 값. 각 항목의 source 참조.

생성 후 check_provenance로 공식 라이브러리와 대조해 DIFFERENT 판정 확인.
"""

# 좌표계: KiCad y-down. SOP류는 핀1=좌상, 반시계 넘버링(좌열 위→아래, 우열 아래→위).
# QFN류는 핀1=좌상, 반시계(좌변 위→아래, 아랫변 좌→우, 우변 아래→위, 윗변 우→좌).

PACKAGES = {
    # === LQFP (ST MCU 정식 등록, 2026-08-10 — 재현 가능하게 상수 영구화) ===
    # 출처: IPC-7351B density B nominal for JEDEC MS-026 (ST 도면 st.com 차단).
    "LQFP-48_7x7_P0.5": {
        "type": "qfn", "pads_per_side": 12, "pitch": 0.5, "span": 8.325,
        "pad_w": 0.3, "pad_l": 1.475, "body": 7.0,
        "source": "IPC-7351B density B for JEDEC MS-026 BBC (LQFP48 7x7 e=0.5)",
    },
    "LQFP-64_10x10_P0.5": {
        "type": "qfn", "pads_per_side": 16, "pitch": 0.5, "span": 11.35,
        "pad_w": 0.3, "pad_l": 1.475, "body": 10.0,
        "source": "IPC-7351B density B for JEDEC MS-026 BFB (LQFP64 10x10 e=0.5)",
    },

    # === 2520(1008) 파워 인덕터 — 제조사별 분리 ===
    # 원본 Antmicro는 KiCad 범용 L_1008 하나로 뭉갰지만, TDK TFM(단자 0.6mm 짧음:
    # 패드 0.7/갭 1.5)과 Bourns SRP2510(랩어라운드 단자: 패드 1.2/갭 0.5)은 권장
    # 패턴이 상반됨 — 제조사 패턴으로 각각 생성 (원본보다 개선).
    # TDK 출처: TFM-ALMA 카탈로그 p.3 RECOMMENDED LAND PATTERN (0.7/1.5/2.0 —
    # 텍스트·고배율 렌더·벡터 실측 3중 일치; TDK 원서버 403이라 LCSC 미러의
    # TDK 저작 동일 PDF 사용, 메타데이터로 확인).
    "L_1008_2520Metric::tdk": {
        "type": "chip2", "pad_l": 0.7, "pad_w": 2.0, "cc": 2.2,
        "body_w": 2.5, "body_h": 2.0,
        "source": "TDK TFM252012ALMA catalog (20200823) p.3 recommended land "
                  "pattern: pad 0.7x2.0, gap 1.5 (matches 0.6mm terminals)",
    },
    # Bourns 출처: SRP2510TMA 데이터시트 p.1 Recommended Layout
    # (overall 2.9 / pad width 2.3 / gap 0.5 → pad_l 1.2, c-c 1.7).
    "L_1008_2520Metric::bourns": {
        "type": "chip2", "pad_l": 1.2, "pad_w": 2.3, "cc": 1.7,
        "body_w": 2.5, "body_h": 2.0,
        "source": "Bourns SRP2510TMA datasheet p.1 Recommended Layout: "
                  "overall 2.9, pad 1.2x2.3, gap 0.5",
    },

    # === QFN-24 4x4 0.5p (TI RTW0024B) ===
    # 출처: TI SCES682C(TXS02612) 도면 4219135/B p.22 — 텍스트·렌더·벡터 실측
    # 3중 일치 (스텐실 78% 커버리지 산식으로 EP 2.45 재확증). 패드 0.24x0.6,
    # 행간 3.8 c-c. 주의: 실제 TI EP=2.45 (KiCad명 EP2.6은 과대 — 언더사이즈
    # EP 랜드가 브리징 안전 방향이라 타 벤더 2.45~2.6 EP 부품에도 보수적).
    "QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm": {
        "type": "qfn", "pads_per_side": 6, "pitch": 0.5,
        "pad_w": 0.24, "pad_l": 0.6, "span": 3.8,
        "ep": 2.45, "body": 4.0,
        "source": "TI SCES682C land pattern drawing 4219135/B p.22 (verified "
                  "by text+render+vector metrology; EP land 2.45 per actual "
                  "RTW package, conservative for 2.45-2.6 EP variants)",
    },

    # Murata DFE252012P 출처: 상세규격 J(E)TE243A-0024C-01 p.5 추천패턴
    # (2.8/1.2/2.0 — 시리즈 플라이어와 2중 확인 + 벡터 실측 0.03mm 내 일치).
    "L_1008_2520Metric::murata-dfe": {
        "type": "chip2", "pad_l": 0.8, "pad_w": 2.0, "cc": 2.0,
        "body_w": 2.5, "body_h": 2.0,
        "source": "Murata spec J(E)TE243A-0024C-01 p.5 recommended pattern: "
                  "overall 2.8, pad 0.8x2.0, gap 1.2",
    },
    # Murata LQM2HP 출처: 참조규격 JELF243B_0019R-01 p.6 §12.1 Land dimensions
    # (a=1.6 갭, b=3.0 전폭, c=1.5 → 패드 0.7, c-c 2.3; 시리즈 공통 표).
    "L_1008_2520Metric::murata-lqm": {
        "type": "chip2", "pad_l": 0.7, "pad_w": 1.5, "cc": 2.3,
        "body_w": 2.5, "body_h": 2.0,
        "source": "Murata reference spec JELF243B_0019R-01 p.6 sec.12.1: "
                  "gap 1.6, overall 3.0, land width 1.5",
    },

    # === Vishay PowerPAK 1212-8 Single (3.3x3.3, DWG 5882) ===
    # 출처: Vishay AN826 doc 72597 p.7 (rev 21-Jan-08) — 인쇄 치수와 PDF 벡터
    # 실측이 0.005mm 내 일치. 핀 1-3=Source, 4=Gate(5번 인접 끝 패드), 5-8=Drain.
    # 드레인 랜드 = 열 사각형 1.725x2.235 @(0.559,0) + 리드 탭 4개(0.760x0.405,
    # 0.254 겹침 병합) — 탭 생략하면 리드당 0.51mm 랜드 손실 (에이전트 플래그).
    "Vishay_PowerPAK_1212-8_Single": {
        "type": "powerpak1212",
        "small": {"w": 0.990, "h": 0.405, "x": -1.436,
                  "ys": [-0.990, -0.330, 0.330, 0.990]},  # 핀 1,2,3,4 (위→아래)
        "thermal": {"w": 1.725, "h": 2.235, "x": 0.559},
        "tabs": {"w": 0.760, "h": 0.405, "x": 1.5495,
                 "ys": [-0.990, -0.330, 0.330, 0.990]},   # 핀 8,7,6,5 (위→아래)
        "body": 3.3,
        "source": "Vishay AN826 (doc 72597, rev 2008-01-21) p.7 recommended "
                  "minimum pads; dimensions re-measured from the PDF vector "
                  "geometry (agreement within 0.005mm); drain modeled as "
                  "thermal rect + 4 merged lead tabs per the drawing",
    },

    # === TSSOP-14 4.4x5.0 0.65p (TI PW0014A / MO-153) ===
    # 출처: TI SLCS006Z (LM339) 랜드패턴 도면 4220202/B (12/2023), PDF p.52.
    # 패드 0.45x1.5, 피치 0.65, 행간 5.8 c-c — 도면이 10X 벡터라 실측 재확인됨
    # (좌우 패드 중심 간 164.41pt=5.800mm). 스텐실 1:1.
    "TSSOP-14_4.4x5mm_P0.65mm": {
        "type": "sop", "pads_per_side": 7, "pitch": 0.65,
        "pad_w": 0.45, "pad_l": 1.5, "span": 5.8,
        "body_w": 4.4, "body_h": 5.0,
        "source": "TI SLCS006Z land pattern drawing 4220202/B (12/2023), "
                  "PDF p.52; dimensions re-measured from the drawing's 10X "
                  "vector geometry (row span 5.800 c-c confirmed)",
    },
    # === VQFN-16 3x3 0.5p EP1.1 (Microchip 4MX) ===
    # 출처: Microchip DS20006539F p.81, Drawing C04-2508 Rev A (RECOMMENDED LAND
    # PATTERN). 패드 X1=0.30 Y1=0.80 (MAX), 피치 E=0.50 BSC, 행간 C1=C2=2.90 NOM,
    # EP: 보수적으로 1.10(패키지 EP NOM; 도면 X2/Y2 MAX 1.20은 G1을 0.40으로 줄임).
    # 내부 정합: C/2-Y/2-EP/2=0.45=G1, E-X1=0.20=G2 확인됨.
    "VQFN-16-1EP_3x3mm_P0.5mm_EP1.1x1.1mm": {
        "type": "qfn", "pads_per_side": 4, "pitch": 0.5,
        "pad_w": 0.30, "pad_l": 0.80, "span": 2.90,
        "ep": 1.10, "body": 3.0,
        "source": "Microchip DS20006539F p.81 (drawing C04-2508 Rev A) "
                  "recommended land pattern; EP land held at package EP nominal "
                  "1.10 for perimeter clearance (G1 0.45)",
    },
}


def _fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _header(pid, descr):
    return [f'(footprint "{pid}"',
            '  (version 20240108) (generator "partreel")',
            '  (layer "F.Cu")',
            f'  (descr "{descr}")',
            '  (attr smd)']


def _texts(ty):
    return [f'  (fp_text reference "REF**" (at 0 {_fmt(-ty)}) (layer "F.SilkS")'
            ' (effects (font (size 1 1) (thickness 0.15))))',
            f'  (fp_text value "VAL**" (at 0 {_fmt(ty)}) (layer "F.Fab")'
            ' (effects (font (size 1 1) (thickness 0.15))))']


def _rect(x0, y0, x1, y1, layer, width):
    return [f'  (fp_line (start {_fmt(a)} {_fmt(b)}) (end {_fmt(c)} {_fmt(d)})'
            f' (stroke (width {width}) (type solid)) (layer "{layer}"))'
            for a, b, c, d in ((x0, y0, x1, y0), (x1, y0, x1, y1),
                               (x1, y1, x0, y1), (x0, y1, x0, y0))]


def qfn_footprint(pid, p, descr):
    """QFN/VQFN: 4변 둘레 패드 + 중앙 EP. 핀1=좌상, 반시계."""
    n = p["pads_per_side"]
    pitch, half = p["pitch"], p["span"] / 2
    w, l = p["pad_w"], p["pad_l"]
    first = -(n - 1) * pitch / 2  # 변 내 첫 패드 오프셋
    pads = []
    # 좌변 (1..n, 위→아래): x=-half, y=first..; 패드 길이는 행 방향(가로)
    for i in range(n):
        pads.append((str(i + 1), -half, first + i * pitch, l, w))
    # 아랫변 (n+1..2n, 좌→우)
    for i in range(n):
        pads.append((str(n + i + 1), first + i * pitch, half, w, l))
    # 우변 (2n+1..3n, 아래→위)
    for i in range(n):
        pads.append((str(2 * n + i + 1), half, -first - i * pitch, l, w))
    # 윗변 (3n+1..4n, 우→좌)
    for i in range(n):
        pads.append((str(3 * n + i + 1), -first - i * pitch, -half, w, l))

    b = p["body"] / 2
    crt = round(max(half + l / 2, b) + 0.25, 3)
    L = _header(pid, descr) + _texts(crt + 1.2)
    L += _rect(-b, -b, b, b, "F.Fab", 0.1)
    # 실크: 모서리 L자 (패드 피함) + 핀1 점
    sk = b + 0.11
    ext = first - w / 2 - 0.2  # 변 첫 패드 직전까지
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        L.append(f'  (fp_line (start {_fmt(sx * sk)} {_fmt(sy * sk)})'
                 f' (end {_fmt(sx * sk)} {_fmt(sy * -ext)})'
                 ' (stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
        L.append(f'  (fp_line (start {_fmt(sx * sk)} {_fmt(sy * sk)})'
                 f' (end {_fmt(sx * -ext)} {_fmt(sy * sk)})'
                 ' (stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
    # 핀1 점: 중심 오프셋 0.35는 점의 외곽 반지름(0.2+0.15)과 같아 패드에
    # 정확히 '접촉' — 마스크 확장에 물려 DRC silk_over_copper가 난다
    # (2026-08-10 g431_devkit 보드 초기화에서 발견). 0.65 = 반지름 0.35 +
    # 여유 0.30 (마스크 확장 0.1 이상 커버).
    d1 = half + l / 2 + 0.65
    L.append(f'  (fp_circle (center {_fmt(-d1)} {_fmt(first)}) '
             f'(end {_fmt(-d1 + 0.2)} {_fmt(first)})'
             ' (stroke (width 0.3) (type solid)) (fill solid) (layer "F.SilkS"))')
    L += _rect(-crt, -crt, crt, crt, "F.CrtYd", 0.05)
    for num, x, y, pw, pl in pads:
        L.append(f'  (pad "{num}" smd rect (at {_fmt(x)} {_fmt(y)})'
                 f' (size {_fmt(pw)} {_fmt(pl)}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    ep = p.get("ep")
    if ep:
        L.append(f'  (pad "{4 * n + 1}" smd rect (at 0 0) (size {_fmt(ep)} '
                 f'{_fmt(ep)}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    L.append(')')
    return "\n".join(L) + "\n"


def sop_footprint(pid, p, descr):
    """SOP/TSSOP/SOT 이열 걸윙: 핀1=좌상, 반시계 (좌열 위→아래, 우열 아래→위)."""
    n = p["pads_per_side"]
    pitch, half = p["pitch"], p["span"] / 2
    w, l = p["pad_w"], p["pad_l"]  # w=피치방향(세로), l=행방향(가로)
    first = -(n - 1) * pitch / 2
    pads = []
    for i in range(n):  # 좌열 1..n
        pads.append((str(i + 1), -half, first + i * pitch))
    for i in range(n):  # 우열 n+1..2n (아래→위)
        pads.append((str(n + i + 1), half, -first - i * pitch))
    bw, bh = p["body_w"] / 2, p["body_h"] / 2
    crt_x = round(half + l / 2 + 0.25, 3)
    crt_y = round(max(bh, -first + w / 2) + 0.25, 3)
    L = _header(pid, descr) + _texts(crt_y + 1.2)
    L += _rect(-bw, -bh, bw, bh, "F.Fab", 0.1)
    # 실크: 상하 라인 (몸체 폭, 패드 피함) + 핀1 점
    for sy in (-(bh + 0.11), bh + 0.11):
        L.append(f'  (fp_line (start {_fmt(-bw)} {_fmt(sy)}) (end {_fmt(bw)} '
                 f'{_fmt(sy)}) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
    d1x = -(half + l / 2 + 0.35)
    L.append(f'  (fp_circle (center {_fmt(d1x)} {_fmt(first)}) '
             f'(end {_fmt(d1x + 0.2)} {_fmt(first)})'
             ' (stroke (width 0.3) (type solid)) (fill solid) (layer "F.SilkS"))')
    L += _rect(-crt_x, -crt_y, crt_x, crt_y, "F.CrtYd", 0.05)
    for num, x, y in pads:
        L.append(f'  (pad "{num}" smd rect (at {_fmt(x)} {_fmt(y)})'
                 f' (size {_fmt(l)} {_fmt(w)}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    L.append(')')
    return "\n".join(L) + "\n"


def chip2_footprint(pid, p, descr):
    """2패드 칩 (인덕터 등): import_antmicro.chip_footprint와 동일 구조."""
    cx = round(p["cc"] / 2, 4)
    w, l = p["pad_w"], p["pad_l"]  # l=길이방향(x), w=폭방향(y)
    bx, by = p["body_w"] / 2, p["body_h"] / 2
    crt_x = round(cx + l / 2 + 0.25, 3)
    crt_y = round(max(by, w / 2) + 0.25, 3)
    L = _header(pid, descr) + _texts(crt_y + 1.2)
    L += _rect(-bx, -by, bx, by, "F.Fab", 0.1)
    sy = round(max(w / 2, by) + 0.16, 3)
    sx = round(cx - l / 2 - 0.2, 3)
    if sx > 0.2:
        for s in (-sy, sy):
            L.append(f'  (fp_line (start {_fmt(-sx)} {_fmt(s)}) (end {_fmt(sx)} '
                     f'{_fmt(s)}) (stroke (width 0.12) (type solid)) '
                     '(layer "F.SilkS"))')
    L += _rect(-crt_x, -crt_y, crt_x, crt_y, "F.CrtYd", 0.05)
    for num, x in (("1", -cx), ("2", cx)):
        L.append(f'  (pad "{num}" smd rect (at {_fmt(x)} 0) (size {_fmt(l)} '
                 f'{_fmt(w)}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    L.append(')')
    return "\n".join(L) + "\n"


def powerpak1212_footprint(pid, p, descr):
    """Vishay PowerPAK 1212-8 Single: 좌열 소스/게이트 4패드 + 드레인(열판+탭4)."""
    s, th, tb = p["small"], p["thermal"], p["tabs"]
    b = p["body"] / 2
    ext_x = tb["x"] + tb["w"] / 2  # 1.9295
    crt_x = round(ext_x + 0.25, 3)
    crt_y = round(b + 0.25, 3)
    L = _header(pid, descr) + _texts(crt_y + 1.2)
    L += _rect(-b, -b, b, b, "F.Fab", 0.1)
    # 실크: 상하 라인 (몸체 폭) + 핀1 점 (좌상)
    for sy in (-(b + 0.11), b + 0.11):
        L.append(f'  (fp_line (start {_fmt(-b)} {_fmt(sy)}) (end {_fmt(b)} '
                 f'{_fmt(sy)}) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
    d1x = s["x"] - s["w"] / 2 - 0.35
    L.append(f'  (fp_circle (center {_fmt(d1x)} {_fmt(s["ys"][0])}) '
             f'(end {_fmt(d1x + 0.2)} {_fmt(s["ys"][0])})'
             ' (stroke (width 0.3) (type solid)) (fill solid) (layer "F.SilkS"))')
    L += _rect(-crt_x, -crt_y, crt_x, crt_y, "F.CrtYd", 0.05)
    # 핀 1,2,3(S), 4(G): 좌열 위→아래
    for i, y in enumerate(s["ys"]):
        L.append(f'  (pad "{i + 1}" smd rect (at {_fmt(s["x"])} {_fmt(y)})'
                 f' (size {_fmt(s["w"])} {_fmt(s["h"])})'
                 ' (layers "F.Cu" "F.Paste" "F.Mask"))')
    # 드레인: 열판(5번) + 탭 8,7,6,5 (위→아래) — 동일 넷, 겹침 병합
    L.append(f'  (pad "5" smd rect (at {_fmt(th["x"])} 0) (size {_fmt(th["w"])} '
             f'{_fmt(th["h"])}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    for num, y in zip(("8", "7", "6", "5"), tb["ys"]):
        L.append(f'  (pad "{num}" smd rect (at {_fmt(tb["x"])} {_fmt(y)})'
                 f' (size {_fmt(tb["w"])} {_fmt(tb["h"])})'
                 ' (layers "F.Cu" "F.Paste" "F.Mask"))')
    L.append(')')
    return "\n".join(L) + "\n"


BUILDERS = {"qfn": qfn_footprint, "sop": sop_footprint, "chip2": chip2_footprint,
            "powerpak1212": powerpak1212_footprint}


def build(fp_name, pid, slug=""):
    """제외 풋프린트 이름 (+부품 슬러그) → 대체 풋프린트 텍스트 (없으면 None).

    제조사별 패턴이 갈리는 패키지는 "<fp명>::<제조사접두>" 키를 먼저 찾는다
    (슬러그 앞부분 매칭), 없으면 fp명 단독 키."""
    p = None
    for key in PACKAGES:
        if "::" in key:
            base, vendor = key.split("::", 1)
            if base == fp_name and slug.startswith(vendor):
                p = PACKAGES[key]
                fp_name = key
                break
    if p is None:
        p = PACKAGES.get(fp_name)
    if not p:
        return None
    descr = (f"{fp_name} replacement land pattern per manufacturer datasheet: "
             f"{p['source']}")
    return BUILDERS[p["type"]](pid, p, descr)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for name in PACKAGES:
        print(f"=== {name} ===")
        print(build(name, "test_" + PACKAGES[name]["type"]))

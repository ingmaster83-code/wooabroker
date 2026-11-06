# -*- coding: utf-8 -*-
"""중개수수료(중개보수) 계산 페이지 생성 -> fee/**/index.html (Jekyll front matter 페이지, 커밋 대상).
사용: python scripts/build_fee_pages.py   (요율이 바뀌면 이 파일의 SALE/LEASE/OFFICETEL 표만 고치고 다시 실행)

요율 출처: 공인중개사법 시행규칙 제20조·별표 1(주택 중개보수 상한요율)을 시·도 조례가 정하며, 확인한 기준은
경기도 주택 중개보수 등에 관한 조례 별표 1(2022.3.4. 시행, 경기부동산포털 gris.gg.go.kr 게시).
 - 매매·교환: 5천만 미만 0.6%(한도 25만) / 5천만~2억 미만 0.5%(한도 80만) / 2억~9억 0.4% / 9억~12억 0.5% / 12억~15억 0.6% / 15억 이상 0.7%
 - 임대차 등: 5천만 미만 0.5%(한도 20만) / 5천만~1억 미만 0.4%(한도 30만) / 1억~6억 0.3% / 6억~12억 0.4% / 12억~15억 0.5% / 15억 이상 0.6%
 - 월세 환산: 보증금 + 월차임×100, 이 값이 5천만 미만이면 보증금 + 월차임×70. 부가가치세 별도.
 - 주거용 오피스텔(전용 85㎡ 이하·입식 부엌·수세식 화장실·목욕시설): 매매 0.5%, 임대차 0.4%, 그 외 0.9%.
2026-08-28 시행 시행규칙 개정은 주거용 오피스텔을 '협의로 결정'한다고 명확히 한 것이 요율 관련 변경의 전부로 확인됨(요율 숫자 변경 근거 없음)."""
import os, pathlib, json, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "fee"
MAN, EOK = 10_000, 100_000_000
esc = html.escape

SALE = [(50_000_000, 0.006, 250_000), (200_000_000, 0.005, 800_000), (900_000_000, 0.004, None),
        (1_200_000_000, 0.005, None), (1_500_000_000, 0.006, None), (None, 0.007, None)]
LEASE = [(50_000_000, 0.005, 200_000), (100_000_000, 0.004, 300_000), (600_000_000, 0.003, None),
         (1_200_000_000, 0.004, None), (1_500_000_000, 0.005, None), (None, 0.006, None)]
OFFICETEL = {"sale": 0.005, "lease": 0.004, "other": 0.009}

def tier(table, amount):
    for i, (upper, rate, limit) in enumerate(table):
        if upper is None or amount < upper: return i, rate, limit

def fee(table, amount):
    i, rate, limit = tier(table, amount)
    f = amount * rate
    if limit: f = min(f, limit)
    return int(round(f)), rate, limit, i

def lease_basis(dep, rent):
    if not rent: return dep
    a = dep + rent * 100
    return dep + rent * 70 if a < 50_000_000 else a

def won(x): return "{:,}".format(int(round(x)))
def pct(r): return ("%.1f" % (r * 100)).rstrip("0").rstrip(".") + "%" if abs(r * 1000 - round(r * 1000)) < 1e-9 else "%.2f%%" % (r * 100)

def amt(n):
    n = int(round(n)); eok, rest = divmod(n, EOK); man = rest // MAN; parts = []
    if eok: parts.append("%d억" % eok)
    if man:
        ch, mn = divmod(man, 1000); s = ("%d천" % ch) if ch else ""
        if mn: s += "%d" % mn
        parts.append(s + "만")
    return " ".join(parts) + " 원" if parts else "0원"
def aslug(n): return amt(n).replace(" ", "").replace("만", "").replace("원", "")

def band(table, i):
    lo = table[i - 1][0] if i else 0; hi = table[i][0]
    return ("%s 이상" % amt(lo) if not hi else ("%s 미만" % amt(hi) if not lo else "%s 이상 ~ %s 미만" % (amt(lo), amt(hi))))

def rate_table(table, hi=None):
    rows = ""
    for i, (upper, rate, limit) in enumerate(table):
        cls = ' class="hl"' if hi == i else ""
        rows += "<tr%s><td>%s</td><td class=\"num\">%s</td><td class=\"num\">%s</td></tr>" % (cls, band(table, i), pct(rate), (won(limit) + "원") if limit else "한도 없음")
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>거래금액</th><th class="num">상한요율</th><th class="num">한도액</th></tr></thead><tbody>%s</tbody></table></div>' % rows

def table(heads, rows, num=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)

def chips(items): return '<div class="chips">%s</div>' % "".join('<a class="chip" href="%s">%s</a>' % (u, esc(t)) for t, u in items)

NOTE = ("중개보수는 거래금액 × 상한요율 이내에서 중개의뢰인과 개업공인중개사가 협의해 정하며 한도액을 넘을 수 없습니다. 부가가치세(10%)는 별도이고, 매도인·매수인(임대인·임차인)이 각각 부담합니다. "
        "요율은 시·도 조례가 정하는데 이 표는 공인중개사법 시행규칙 별표와 경기도 조례(2022.3.4. 시행)를 기준으로 했습니다. 지역별 조례가 다르거나 2026년 8월 시행규칙 개정에 따라 조례가 바뀌면 달라질 수 있으니 계약 전 해당 시·도 조례를 확인하세요.")

def page(path, title, desc, h1, sub, body, faq, crumbs):
    d = OUT / path.strip("/").replace("fee/", "", 1) if path != "/fee/" else OUT
    d.mkdir(parents=True, exist_ok=True)
    cr = ' <span>›</span> '.join(('<a href="%s">%s</a>' % (u, n)) if i < len(crumbs) - 1 else "<span>%s</span>" % n for i, (n, u) in enumerate(crumbs))
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    faq_html = "".join('<details style="margin-bottom:10px;"><summary style="cursor:pointer;font-weight:600;padding:6px 0;">%s</summary><p class="ctx">%s</p></details>' % (esc(q), esc(a)) for q, a in faq)
    html_out = f"""---
layout: default
title: "{title.replace('"', "'")}"
description: "{desc.replace('"', "'")}"
---

<div class="page-with-sidebar">
<div class="region-page">

  <nav class="breadcrumb" aria-label="위치">{cr}</nav>

  <div class="region-page-header">
    <h1>{h1}</h1>
    <p>{sub}</p>
  </div>

  <div class="ad-slot">
    {{% include ad.html %}}
  </div>

{body}

  <div class="camp-section">
    <h2>자주 묻는 질문</h2>
    {faq_html}
  </div>

  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>

</div>
<aside class="tool-sidebar"></aside>
</div>
"""
    (d / "index.html").write_text(html_out, encoding="utf-8")

def sec(t, inner): return '  <div class="camp-section">\n    <h2>%s</h2>\n    %s\n  </div>\n' % (t, inner)
def lead(t): return '  <p class="ctx" style="margin-bottom:20px;">%s</p>\n' % t
def stats(items): return '  <div class="stat-row">%s</div>\n' % "".join('<div class="stat"><small>%s</small><b>%s</b></div>' % (a, b) for a, b in items)
def near(lst, v, k=3):
    i = lst.index(v); return lst[max(0, i - k): i + k + 1]

WON_LINKS = [("매매 중개수수료", "/fee/sale/"), ("전세 중개수수료", "/fee/jeonse/"), ("월세 중개수수료", "/fee/wolse/"), ("오피스텔", "/fee/officetel/"), ("계약 전 체크리스트", "/guide/"), ("중개사무소 찾기", "/region/")]

# ───────────────────────── 매매 ─────────────────────────
SALE_AMTS = [3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 12000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000, 130000, 140000, 150000, 170000, 200000, 250000, 300000]

def page_sale(m):
    a = m * MAN; f, r, lim, i = fee(SALE, a); vat = round(f * 1.1)
    p = "/fee/sale/%s/" % aslug(a)
    nl = near(SALE_AMTS, m)
    nt = table(["매매가", "상한요율", "중개보수 상한", "부가세 포함"], [[('<a href="/fee/sale/%s/">%s</a>' % (aslug(x * MAN), amt(x * MAN))) if x != m else "<b>%s</b>" % amt(x * MAN), pct(fee(SALE, x * MAN)[1]), won(fee(SALE, x * MAN)[0]) + "원", won(round(fee(SALE, x * MAN)[0] * 1.1)) + "원"] for x in nl], (1, 2, 3))
    body = (lead(f"<b>{amt(a)}</b> 매매의 중개수수료(중개보수) 상한은 <b>{won(f)}원</b>이고 부가가치세 10%를 더하면 <b>{won(vat)}원</b>입니다. 이 금액을 매도인과 매수인이 각각 중개사에게 지급합니다(상한요율 {pct(r)}{'' if not lim else ', 한도액 ' + won(lim) + '원'}).")
            + stats([("상한요율", pct(r)), ("중개보수 상한", won(f) + "원"), ("부가세 포함", won(vat) + "원")])
            + sec("📊 매매 중개보수 요율표 (해당 구간 표시)", rate_table(SALE, i))
            + sec("🧮 계산", f"<p class=\"ctx\">{amt(a)} × {pct(r)} = {won(a * r)}원{'' if not lim else (' → 한도액 ' + won(lim) + '원 적용' if a * r > lim else '')}. 매도인·매수인이 각각 {won(f)}원(부가세 별도), 둘이 합쳐 {won(f * 2)}원을 중개사에게 지급하는 구조입니다.</p>")
            + sec("📈 비슷한 매매가의 중개수수료", nt)
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + '</p>\n'
            + chips(WON_LINKS + [("취득세 계산", "https://wooatax.wooahouse.com/acquisition/"), ("대출 이자 계산", "https://wooaloan.wooahouse.com/loan/")]))
    faq = [(f"매매가 {amt(a)}이면 중개수수료는 얼마인가요?", f"상한요율 {pct(r)}로 {won(f)}원(부가세 별도, 포함 시 {won(vat)}원)이 상한이며 매도인·매수인이 각각 지급합니다."),
           ("중개수수료는 꼭 상한요율대로 줘야 하나요?", "상한요율은 최대치이고 그 이내에서 협의해 정합니다. 한도액이 있는 구간은 한도를 넘을 수 없습니다."),
           ("부가가치세는 별도인가요?", "네. 중개사가 일반과세자라면 중개보수에 부가가치세 10%가 별도로 붙습니다.")]
    page(p, f"{amt(a)} 매매 중개수수료 — 상한 {won(f)}원 (부가세 별도)", f"매매가 {amt(a)}의 중개수수료(복비) 상한은 {won(f)}원, 부가세 포함 {won(vat)}원. 상한요율 {pct(r)}와 계산 방법.",
         f"{amt(a)} 매매 중개수수료 — 상한 {won(f)}원", "부동산 매매 복비 계산 · 부가세 별도 · 매도인·매수인 각각", body, faq, [("홈", "/"), ("중개수수료", "/fee/"), ("매매", "/fee/sale/"), (amt(a), p)])

def hub_sale():
    rows = [['<a href="/fee/sale/%s/">%s</a>' % (aslug(x * MAN), amt(x * MAN)), pct(fee(SALE, x * MAN)[1]), won(fee(SALE, x * MAN)[0]) + "원", won(round(fee(SALE, x * MAN)[0] * 1.1)) + "원"] for x in SALE_AMTS]
    body = (lead("매매가별 중개수수료(복비) 상한입니다. 금액을 누르면 계산 과정과 비슷한 금액의 수수료를 볼 수 있습니다. 부가가치세 10%는 별도입니다.")
            + sec("📊 요율표", rate_table(SALE)) + sec("🏠 매매가별 중개수수료", table(["매매가", "상한요율", "중개보수 상한", "부가세 포함"], rows, (1, 2, 3)))
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + '</p>\n' + chips(WON_LINKS))
    faq = [("매매 중개수수료는 어떻게 계산하나요?", "거래금액 × 상한요율이며 5천만원 미만은 한도 25만원, 5천만원~2억원 미만은 한도 80만원입니다."), ("3억 매매 중개수수료는?", f"상한요율 0.4%로 {won(fee(SALE, 300_000_000)[0])}원(부가세 별도)입니다.")]
    page("/fee/sale/", "매매 중개수수료 계산 — 매매가별 복비 상한표", "부동산 매매 중개수수료(복비) 요율표와 매매가별 상한 금액. 3억 120만원, 5억 200만원 등 부가세 별도.", "매매 중개수수료 계산 — 매매가별 상한표", "매매·교환 중개보수 요율 · 한도액 · 부가세", body, faq, [("홈", "/"), ("중개수수료", "/fee/"), ("매매", "/fee/sale/")])

# ───────────────────────── 전세 ─────────────────────────
JEONSE = [1000, 2000, 3000, 5000, 7000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 120000, 150000, 200000]

def page_jeonse(m):
    a = m * MAN; f, r, lim, i = fee(LEASE, a); vat = round(f * 1.1)
    p = "/fee/jeonse/%s/" % aslug(a)
    nl = near(JEONSE, m)
    nt = table(["전세 보증금", "상한요율", "중개보수 상한", "부가세 포함"], [[('<a href="/fee/jeonse/%s/">%s</a>' % (aslug(x * MAN), amt(x * MAN))) if x != m else "<b>%s</b>" % amt(x * MAN), pct(fee(LEASE, x * MAN)[1]), won(fee(LEASE, x * MAN)[0]) + "원", won(round(fee(LEASE, x * MAN)[0] * 1.1)) + "원"] for x in nl], (1, 2, 3))
    body = (lead(f"전세 보증금 <b>{amt(a)}</b>의 중개수수료(중개보수) 상한은 <b>{won(f)}원</b>이고 부가가치세 10%를 더하면 <b>{won(vat)}원</b>입니다. 임대인과 임차인이 각각 중개사에게 지급합니다(상한요율 {pct(r)}{'' if not lim else ', 한도액 ' + won(lim) + '원'}).")
            + stats([("상한요율", pct(r)), ("중개보수 상한", won(f) + "원"), ("부가세 포함", won(vat) + "원")])
            + sec("📊 임대차 중개보수 요율표 (해당 구간 표시)", rate_table(LEASE, i))
            + sec("🧮 계산", f"<p class=\"ctx\">{amt(a)} × {pct(r)} = {won(a * r)}원{'' if not lim else (' → 한도액 ' + won(lim) + '원 적용' if a * r > lim else '')}. 임대인·임차인이 각각 {won(f)}원(부가세 별도)을 지급하는 구조입니다. 전세는 보증금이 곧 거래금액입니다.</p>")
            + sec("📈 비슷한 보증금의 중개수수료", nt)
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + '</p>\n'
            + chips(WON_LINKS))
    faq = [(f"전세 {amt(a)} 중개수수료는 얼마인가요?", f"상한요율 {pct(r)}로 {won(f)}원(부가세 별도, 포함 시 {won(vat)}원)이 상한입니다."),
           ("전세 중개수수료는 누가 내나요?", "임대인과 임차인이 각각 중개보수를 중개사에게 지급합니다. 보통 거래 당사자가 각자 부담합니다."),
           ("전세 계약 갱신(연장)해도 중개수수료를 내나요?", "중개사가 새로 중개한 계약이 아니면 중개보수 지급 의무가 없습니다. 같은 임대인과 갱신하는 경우 보통 중개보수가 발생하지 않습니다.")]
    page(p, f"전세 {amt(a)} 중개수수료 — 상한 {won(f)}원 (부가세 별도)", f"전세 보증금 {amt(a)}의 중개수수료(복비) 상한은 {won(f)}원, 부가세 포함 {won(vat)}원. 상한요율 {pct(r)}와 계산 방법.",
         f"전세 {amt(a)} 중개수수료 — 상한 {won(f)}원", "전세 복비 계산 · 부가세 별도 · 임대인·임차인 각각", body, faq, [("홈", "/"), ("중개수수료", "/fee/"), ("전세", "/fee/jeonse/"), (amt(a), p)])

def hub_jeonse():
    rows = [['<a href="/fee/jeonse/%s/">%s</a>' % (aslug(x * MAN), amt(x * MAN)), pct(fee(LEASE, x * MAN)[1]), won(fee(LEASE, x * MAN)[0]) + "원", won(round(fee(LEASE, x * MAN)[0] * 1.1)) + "원"] for x in JEONSE]
    body = (lead("전세 보증금별 중개수수료(복비) 상한입니다. 금액을 누르면 계산 과정을 볼 수 있습니다. 부가가치세 10%는 별도입니다.")
            + sec("📊 요율표", rate_table(LEASE)) + sec("🏠 전세 보증금별 중개수수료", table(["전세 보증금", "상한요율", "중개보수 상한", "부가세 포함"], rows, (1, 2, 3)))
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + '</p>\n' + chips(WON_LINKS))
    faq = [("전세 중개수수료는 어떻게 계산하나요?", "보증금 × 상한요율이며 5천만원 미만 한도 20만원, 5천만원~1억원 미만 한도 30만원입니다."), ("전세 3억 중개수수료는?", f"상한요율 0.3%로 {won(fee(LEASE, 300_000_000)[0])}원(부가세 별도)입니다.")]
    page("/fee/jeonse/", "전세 중개수수료 계산 — 보증금별 복비 상한표", "전세 보증금별 중개수수료(복비) 요율표와 상한 금액. 전세 3억 90만원 등 부가세 별도.", "전세 중개수수료 계산 — 보증금별 상한표", "임대차 중개보수 요율 · 한도액 · 부가세", body, faq, [("홈", "/"), ("중개수수료", "/fee/"), ("전세", "/fee/jeonse/")])

# ───────────────────────── 월세 ─────────────────────────
W_DEPS = [500, 1000, 2000, 3000, 5000, 7000, 10000, 20000]
W_RENTS = [30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 200]

def wolse_calc(dep_man, rent_man):
    dep, rent = dep_man * MAN, rent_man * MAN
    basis = lease_basis(dep, rent); f, r, lim, i = fee(LEASE, basis)
    return dep, rent, basis, f, r, lim, i

def page_wolse(dm, rm):
    dep, rent, basis, f, r, lim, i = wolse_calc(dm, rm); vat = round(f * 1.1)
    p = "/fee/wolse/%s/%d/" % (aslug(dep), rm)
    x100 = dep + rent * 100; used70 = x100 < 50_000_000
    mult = 70 if used70 else 100
    rows = [[('<a href="/fee/wolse/%s/%d/">월세 %d만원</a>' % (aslug(dep), x, x)) if x != rm else "<b>월세 %d만원</b>" % x, won(wolse_calc(dm, x)[2]) + "원", pct(wolse_calc(dm, x)[4]), won(wolse_calc(dm, x)[3]) + "원"] for x in W_RENTS]
    body = (lead(f"보증금 <b>{amt(dep)}</b>에 월세 <b>{rm}만 원</b>이면 중개수수료(중개보수) 상한은 <b>{won(f)}원</b>, 부가가치세 10%를 더하면 <b>{won(vat)}원</b>입니다. 월세는 '보증금 + 월세 × {mult}'로 환산한 {won(basis)}원을 거래금액으로 봅니다.")
            + stats([("환산 거래금액", won(basis) + "원"), ("상한요율", pct(r)), ("중개보수 상한", won(f) + "원")])
            + sec("🧮 환산과 계산", f"<p class=\"ctx\">① 환산금액 = 보증금 {won(dep)}원 + 월세 {won(rent)}원 × 100 = {won(x100)}원." + (f" 이 금액이 5천만원 미만이라 월세 × 70으로 다시 계산해 <b>{won(basis)}원</b>이 됩니다." if used70 else f" 5천만원 이상이라 이 금액을 그대로 씁니다.") + f"<br>② 상한요율 {pct(r)}{'' if not lim else ', 한도액 ' + won(lim) + '원'} → 환산금액 × {pct(r)} = {won(basis * r)}원{'' if not lim else (' → 한도액 적용 ' + won(lim) + '원' if basis * r > lim else '')}.<br>③ 중개보수 상한 {won(f)}원(부가세 별도), 임대인·임차인이 각각 지급합니다.</p>")
            + sec("📊 임대차 중개보수 요율표 (해당 구간 표시)", rate_table(LEASE, i))
            + sec("📈 같은 보증금, 월세별 중개수수료", table(["월세", "환산 거래금액", "상한요율", "중개보수 상한"], rows, (1, 2, 3)))
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + '</p>\n'
            + chips([("보증금 %s 월세 전체표" % amt(dep), "/fee/wolse/%s/" % aslug(dep)), ("월세 중개수수료", "/fee/wolse/")] + WON_LINKS[:2] + WON_LINKS[4:]))
    faq = [(f"보증금 {amt(dep)} 월세 {rm}만원 중개수수료는 얼마인가요?", f"환산금액 {won(basis)}원에 상한요율 {pct(r)}를 적용해 {won(f)}원(부가세 별도, 포함 시 {won(vat)}원)이 상한입니다."),
           ("월세 중개수수료는 어떻게 환산하나요?", "보증금 + (월세 × 100)을 거래금액으로 봅니다. 이 값이 5천만원 미만이면 보증금 + (월세 × 70)으로 다시 계산합니다."),
           ("월세 중개수수료도 부가세가 붙나요?", "네. 일반과세 중개사라면 중개보수에 부가가치세 10%가 별도로 붙습니다.")]
    page(p, f"보증금 {amt(dep)} 월세 {rm}만원 중개수수료 — 상한 {won(f)}원", f"보증금 {amt(dep)}·월세 {rm}만원의 중개수수료(복비) 상한은 {won(f)}원(부가세 별도). 환산금액 {won(basis)}원과 계산 방법.",
         f"보증금 {amt(dep)} 월세 {rm}만원 중개수수료 — {won(f)}원", "월세 복비 계산 · 보증금+월세×100 환산 · 부가세 별도", body, faq, [("홈", "/"), ("중개수수료", "/fee/"), ("월세", "/fee/wolse/"), (amt(dep), "/fee/wolse/%s/" % aslug(dep)), ("월세 %d만원" % rm, p)])

def page_wolse_dep(dm):
    dep = dm * MAN
    rows = [['<a href="/fee/wolse/%s/%d/">월세 %d만원</a>' % (aslug(dep), x, x), won(wolse_calc(dm, x)[2]) + "원", pct(wolse_calc(dm, x)[4]), won(wolse_calc(dm, x)[3]) + "원", won(round(wolse_calc(dm, x)[3] * 1.1)) + "원"] for x in W_RENTS]
    p = "/fee/wolse/%s/" % aslug(dep)
    f50 = wolse_calc(dm, 50)[3]
    body = (lead(f"보증금 <b>{amt(dep)}</b>인 월세 계약의 월세별 중개수수료(복비) 상한입니다. 월세 50만원이면 {won(f50)}원(부가세 별도)입니다. 월세를 누르면 환산 과정을 볼 수 있습니다.")
            + sec("🏠 월세별 중개수수료", table(["월세", "환산 거래금액", "상한요율", "중개보수 상한", "부가세 포함"], rows, (1, 2, 3, 4)))
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + '</p>\n' + chips([("월세 중개수수료", "/fee/wolse/")] + WON_LINKS[:2] + WON_LINKS[4:]))
    faq = [(f"보증금 {amt(dep)} 월세 50만원 중개수수료는?", f"환산금액 {won(wolse_calc(dm, 50)[2])}원 기준 {won(f50)}원(부가세 별도)입니다."), ("월세 환산은 어떻게 하나요?", "보증금 + 월세 × 100(합이 5천만원 미만이면 월세 × 70)입니다.")]
    page(p, f"보증금 {amt(dep)} 월세 중개수수료 — 월세별 복비 상한표", f"보증금 {amt(dep)} 월세 계약의 월세별 중개수수료(복비) 상한. 월세 50만원 {won(f50)}원 등 부가세 별도.",
         f"보증금 {amt(dep)} 월세 중개수수료 — 월세별 표", "월세 복비 계산 · 환산금액 · 부가세 별도", body, faq, [("홈", "/"), ("중개수수료", "/fee/"), ("월세", "/fee/wolse/"), (amt(dep), p)])

def hub_wolse():
    rows = [['<a href="/fee/wolse/%s/">%s</a>' % (aslug(x * MAN), amt(x * MAN))] + ['<a href="/fee/wolse/%s/%d/">%s원</a>' % (aslug(x * MAN), r, won(wolse_calc(x, r)[3])) for r in (30, 50, 70, 100)] for x in W_DEPS]
    body = (lead("월세 계약의 중개수수료(복비)는 월세를 보증금으로 환산해 계산합니다. 환산금액 = 보증금 + 월세 × 100(5천만원 미만이면 월세 × 70). 보증금을 누르면 월세별 표가 나옵니다.")
            + sec("🏠 보증금·월세별 중개수수료 상한", table(["보증금", "월세 30만원", "월세 50만원", "월세 70만원", "월세 100만원"], rows, (1, 2, 3, 4)))
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + '</p>\n' + chips(WON_LINKS))
    faq = [("월세 중개수수료는 어떻게 계산하나요?", "보증금 + 월세 × 100으로 환산한 금액에 임대차 상한요율을 곱합니다. 환산금액이 5천만원 미만이면 월세 × 70을 씁니다."), ("보증금 1천만원 월세 50만원 중개수수료는?", f"환산금액 {won(wolse_calc(1000, 50)[2])}원 기준 {won(wolse_calc(1000, 50)[3])}원(부가세 별도)입니다.")]
    page("/fee/wolse/", "월세 중개수수료 계산 — 보증금·월세별 복비 상한표", "월세 중개수수료(복비) 계산법과 보증금·월세별 상한 금액. 보증금+월세×100 환산, 부가세 별도.", "월세 중개수수료 계산 — 보증금·월세별 상한표", "월세 복비 환산 · 임대차 요율 · 부가세", body, faq, [("홈", "/"), ("중개수수료", "/fee/"), ("월세", "/fee/wolse/")])

# ───────────────────────── 오피스텔 ─────────────────────────
OFT_AMTS = [5000, 10000, 20000, 30000, 50000, 70000, 100000]
def hub_officetel():
    rows = [[amt(x * MAN), won(x * MAN * OFFICETEL["sale"]) + "원", won(x * MAN * OFFICETEL["lease"]) + "원", won(x * MAN * OFFICETEL["other"]) + "원"] for x in OFT_AMTS]
    body = (lead("<b>주거용 오피스텔</b>(전용면적 85㎡ 이하이고 입식 부엌·수세식 화장실·목욕시설을 갖춘 경우)의 중개수수료 상한요율은 매매 0.5%, 임대차 0.4%입니다. 그 밖의 오피스텔(업무용 등)은 거래금액의 0.9% 이내에서 협의합니다. 한도액은 없고 부가가치세 10%는 별도입니다. 2026년 8월 28일부터는 주거용 오피스텔도 상한요율 이내에서 중개의뢰인과 중개사가 협의해 정한다고 규칙에 명확히 규정되었습니다.")
            + sec("🏢 오피스텔 중개보수 요율", table(["구분", "상한요율"], [["주거용(85㎡ 이하·입식 부엌·화장실·욕실) 매매·교환", "0.5%"], ["주거용(85㎡ 이하·입식 부엌·화장실·욕실) 임대차 등", "0.4%"], ["그 밖의 경우 매매·교환·임대차 등", "0.9%"]], (1,)))
            + sec("🧮 거래금액별 중개수수료 상한", table(["거래금액", "주거용 매매(0.5%)", "주거용 임대차(0.4%)", "그 밖의 경우(0.9%)"], rows, (1, 2, 3)))
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + ' 월세는 보증금 + 월세 × 100(5천만원 미만이면 × 70)으로 환산한 금액에 요율을 곱합니다.</p>\n' + chips(WON_LINKS))
    faq = [("오피스텔 매매 중개수수료는?", "주거용(85㎡ 이하 등)이면 0.5%, 아니면 0.9% 이내에서 협의합니다. 1억 매매면 주거용 상한 50만원입니다."), ("오피스텔 월세 중개수수료는?", "월세를 보증금으로 환산(보증금+월세×100)한 금액에 0.4%(주거용 임대차)를 곱합니다.")]
    page("/fee/officetel/", "오피스텔 중개수수료 계산 — 매매·임대차 요율 0.5%·0.4%·0.9%", "오피스텔 중개수수료(복비) 요율. 주거용 매매 0.5%, 임대차 0.4%, 그 밖의 경우 0.9%와 금액별 상한 계산.", "오피스텔 중개수수료 계산 — 요율표", "주거용 오피스텔 매매 0.5% · 임대차 0.4% · 그 밖의 경우 0.9%", body, faq, [("홈", "/"), ("중개수수료", "/fee/"), ("오피스텔", "/fee/officetel/")])

# ───────────────────────── 허브 + 계산기 ─────────────────────────
CALC_JS = """<script>
(function(){
var SALE=[[5e7,0.006,25e4],[2e8,0.005,8e5],[9e8,0.004,0],[12e8,0.005,0],[15e8,0.006,0],[0,0.007,0]];
var LEASE=[[5e7,0.005,2e5],[1e8,0.004,3e5],[6e8,0.003,0],[12e8,0.004,0],[15e8,0.005,0],[0,0.006,0]];
function fee(t,a){for(var i=0;i<t.length;i++){if(t[i][0]===0||a<t[i][0]){var f=a*t[i][1];if(t[i][2])f=Math.min(f,t[i][2]);return [Math.round(f),t[i][1]];}}}
function fmt(n){return Math.round(n).toLocaleString('ko-KR');}
document.getElementById('fee-go').addEventListener('click',function(){
 var type=document.getElementById('fee-type').value;
 var dep=(parseFloat(document.getElementById('fee-dep').value)||0)*10000;
 var rent=(parseFloat(document.getElementById('fee-rent').value)||0)*10000;
 var a=dep,t=type==='sale'?SALE:LEASE,note='';
 if(type==='wolse'&&rent>0){a=dep+rent*100;if(a<5e7)a=dep+rent*70;note=' (월세 환산금액 '+fmt(a)+'원)';}
 if(a<=0){document.getElementById('fee-out').textContent='금액을 입력하세요.';return;}
 var r=fee(t,a);
 document.getElementById('fee-out').innerHTML='중개보수 상한 <b>'+fmt(r[0])+'원</b> (상한요율 '+(r[1]*100).toFixed(1)+'%'+note+')<br>부가세 포함 <b>'+fmt(r[0]*1.1)+'원</b> · 매도인·매수인(임대인·임차인) 각각';
});
document.getElementById('fee-type').addEventListener('change',function(){document.getElementById('fee-rent-wrap').style.display=this.value==='wolse'?'inline-block':'none';});
})();
</script>"""

def hub_fee():
    calc = ('<div class="tool-box"><div class="tool-row">'
            '<div><label for="fee-type">거래 종류</label><select id="fee-type"><option value="sale">매매</option><option value="jeonse">전세</option><option value="wolse">월세</option></select></div>'
            '<div><label for="fee-dep">매매가·보증금(만원)</label><input id="fee-dep" type="number" value="30000" style="width:130px"></div>'
            '<div id="fee-rent-wrap" style="display:none"><label for="fee-rent">월세(만원)</label><input id="fee-rent" type="number" value="50" style="width:90px"></div>'
            '<button class="btn-p" id="fee-go">계산</button></div><div class="tool-out" id="fee-out">금액을 입력하고 계산을 누르세요.</div></div>' + CALC_JS)
    body = (lead("부동산 중개수수료(중개보수, 복비)는 <b>거래금액 × 상한요율</b> 이내에서 중개사와 협의해 정하며, 일부 구간은 한도액이 있습니다. 부가가치세 10%는 별도이고 매도인·매수인(임대인·임차인)이 각각 지급합니다. 월세는 보증금 + 월세 × 100(5천만원 미만이면 × 70)으로 환산합니다. 아래 계산기로 바로 계산하거나 금액별 표를 확인하세요.")
            + sec("🧮 중개수수료 계산기", calc)
            + sec("🏠 매매·교환 요율표", rate_table(SALE)) + sec("🔑 임대차(전세·월세) 요율표", rate_table(LEASE))
            + sec("📋 바로가기", chips([("매매가별 표", "/fee/sale/"), ("전세 보증금별 표", "/fee/jeonse/"), ("월세 보증금·월세별 표", "/fee/wolse/"), ("오피스텔 중개수수료", "/fee/officetel/"), ("3억 매매", "/fee/sale/3억/"), ("5억 매매", "/fee/sale/5억/"), ("전세 2억", "/fee/jeonse/2억/"), ("보증금 1천 월세 50", "/fee/wolse/1천/50/")]))
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + '</p>\n' + chips([("계약 전 체크리스트", "/guide/"), ("중개사무소 찾기", "/region/")]))
    faq = [("중개수수료는 누가 내나요?", "매매는 매도인과 매수인이, 임대차는 임대인과 임차인이 각각 중개보수를 지급합니다."), ("중개수수료는 협의가 가능한가요?", "상한요율은 최대치이고 그 이내에서 협의해 정합니다. 한도액이 있는 구간은 한도를 넘을 수 없습니다."),
           ("중개수수료는 언제 내나요?", "약정이 없으면 거래대금 지급이 완료된 날 지급합니다."), ("부가세가 포함된 금액인가요?", "표의 상한은 부가세 별도이며 부가세 포함 금액을 따로 표시했습니다.")]
    page("/fee/", "부동산 중개수수료 계산기 — 매매·전세·월세 복비 요율표", "부동산 중개수수료(복비) 계산기와 매매·전세·월세 요율표. 거래금액별 상한 금액, 월세 환산법, 오피스텔 요율, 부가세까지 한 번에.", "🧮 부동산 중개수수료 계산기 — 매매·전세·월세", "복비 계산 · 요율표 · 월세 환산 · 부가세", body, faq, [("홈", "/"), ("중개수수료", "/fee/")])

def main():
    import shutil
    if OUT.exists(): shutil.rmtree(OUT)
    n = 0
    for m in SALE_AMTS: page_sale(m); n += 1
    hub_sale(); n += 1
    for m in JEONSE: page_jeonse(m); n += 1
    hub_jeonse(); n += 1
    for d in W_DEPS:
        page_wolse_dep(d); n += 1
        for r in W_RENTS: page_wolse(d, r); n += 1
    hub_wolse(); hub_officetel(); hub_fee(); n += 3
    print("fee pages", n)

if __name__ == "__main__":
    main()

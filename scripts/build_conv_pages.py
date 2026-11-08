# -*- coding: utf-8 -*-
"""전월세 전환율 계산 페이지 생성 -> conv/**/index.html (Jekyll front matter 페이지, 커밋 대상).
 /conv/                              계산기(월세→전세 환산 · 전세→월세 환산 · 전환율 구하기) + 해설
 /conv/wolse-to-jeonse/{보증금}-{월세}/   보증금·월세(만원)별 전세 환산액 (전환율 4~10% 비교)
 /conv/jeonse-to-wolse/{전세}-{보증금}/   전세금·남기는 보증금(만원)별 월세 (전환율 4~10% 비교)
 공식: 전세 환산 = 보증금 + 월세 x 12 / 전환율,  월세 = (전세금 - 보증금) x 전환율 / 12,  전환율 = 월세 x 12 / (전세금 - 보증금).
 법적 근거: 주택임대차보호법 제7조의2·시행령 제9조 — 월차임 전환 시 산정률은 연 10%와 '한국은행 기준금리 + 2%' 중 낮은 비율(기준금리는 수시 변동 → 페이지에서는 값을 단정하지 않고 계산식과 예시만 제시)."""
import json, os, pathlib, shutil, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_fee_pages as B

ROOT = pathlib.Path(__file__).resolve().parent.parent
B.OUT = ROOT                               # B.page 가 ROOT/conv/... 로 쓰도록
OUTD = ROOT / "conv"
MAN = 10_000
RATES = [0.04, 0.05, 0.06, 0.07, 0.08, 0.10]
esc = B.esc
def m(n):                                   # 만원 -> '1억 2천4백만 원'
    n = int(round(n)); eok, rest = divmod(n, 10000); parts = []
    if eok: parts.append("%d억" % eok)
    if rest:
        th, hu, r = rest // 1000, rest % 1000 // 100, rest % 100
        parts.append((("%d천" % th) if th else "") + (("%d백" % hu) if hu else "") + (("%d" % r) if r else "") + "만")
    return (" ".join(parts) + " 원") if parts else "0원"
def won(x): return "{:,}".format(int(round(x)))
def man(x): return "{:,}".format(int(round(x)))

DEPS = [500, 1000, 2000, 3000, 5000, 10000]
RENTS = [20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90, 100, 120, 150]
JEONSE = [5000, 8000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 70000, 100000]
KEEP = [0, 1000, 2000, 3000, 5000, 10000, 20000]

LAW = ("주택임대차보호법 시행령에 따라 보증금을 월세로 바꿀 때 적용하는 산정률은 연 10%와 한국은행 기준금리에 2%p를 더한 값 중 낮은 비율을 넘을 수 없습니다. "
       "기준금리는 수시로 바뀌므로 계약 시점의 한국은행 기준금리를 확인해 계산하세요(예: 기준금리가 2.5%라면 상한은 4.5%). 이 페이지의 4~10% 비교표는 법정 상한을 단정한 것이 아니라 전환율별 시뮬레이션입니다.")
NOTE = LAW + " 상가건물 임대차나 임대인·임차인 간 합의로 정하는 경우, 지역·시장 관행은 다를 수 있으며 실제 계약 전 확인이 필요합니다."
LINKS = [("전월세 전환 계산기", "/conv/"), ("월세→전세 환산표", "/conv/wolse-to-jeonse/"), ("전세→월세 환산표", "/conv/jeonse-to-wolse/"), ("중개수수료 계산", "/fee/"), ("계약 전 체크리스트", "/guide/")]
CRUMB0 = [("우아중개사", "/"), ("전월세 전환", "/conv/")]

def jeonse_eq(d, r, rate): return d + r * 12 / rate           # 만원
def wolse_of(j, d, rate): return (j - d) * rate / 12           # 만원

def page_w2j(d, r):
    rows = [["%d%%" % round(x * 100), man(jeonse_eq(d, r, x)) + "만원", m(round(jeonse_eq(d, r, x)))] for x in RATES]
    mid = jeonse_eq(d, r, 0.06)
    p = "/conv/wolse-to-jeonse/%d-%d/" % (d, r)
    near = [(dd, rr) for dd in DEPS for rr in RENTS if dd == d and abs(RENTS.index(rr) - RENTS.index(r)) <= 3 and rr != r]
    near += [(dd, r) for dd in DEPS if dd != d and abs(DEPS.index(dd) - DEPS.index(d)) <= 2]
    nt = B.table(["보증금", "월세", "전세 환산 (전환율 6%)"], [['<a href="/conv/wolse-to-jeonse/%d-%d/">%s</a>' % (dd, rr, m(dd)), "%s만원" % man(rr), man(jeonse_eq(dd, rr, 0.06)) + "만원"] for dd, rr in near], num=(1, 2))
    body = (B.lead("보증금 <b>%s</b>에 월세 <b>%s만원</b>인 집을 전세로 환산하면, 전환율 6%%일 때 약 <b>%s만원</b>(%s)입니다. 전환율이 낮을수록 전세 환산액이 커지고, 높을수록 작아집니다. 아래 표에서 전환율별 금액을 비교해 보세요." % (m(d), man(r), man(mid), m(round(mid))))
            + B.stats([("보증금", m(d)), ("월세", "%s만원" % man(r)), ("연 월세", "%s만원" % man(r * 12))])
            + B.sec("📊 전환율별 전세 환산액", B.table(["전환율(연)", "전세 환산액(만원)", "환산액 표기"], rows, num=(1,)))
            + B.sec("🧮 계산식", '<p class="ctx">전세 환산액 = 보증금 + 월세 × 12 ÷ 전환율 = %s + %s × 12 ÷ 전환율. 예를 들어 전환율 5%%면 %s + %s ÷ 0.05 = %s만원입니다.</p>' % (m(d), man(r), man(d), man(r * 12), man(jeonse_eq(d, r, 0.05))))
            + B.sec("📈 비슷한 조건의 환산액", nt)
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + "</p>\n" + B.chips(LINKS))
    faq = [("보증금 %s 월세 %s만원은 전세로 얼마인가요?" % (m(d), man(r)), "전환율 6%% 기준 약 %s만원, 5%%면 %s만원, 4%%면 %s만원입니다. 적용 전환율은 계약마다 다르니 법정 상한(기준금리+2%%p와 10%% 중 낮은 값)을 확인하세요." % (man(mid), man(jeonse_eq(d, r, .05)), man(jeonse_eq(d, r, .04)))),
           ("전월세 전환율이란 무엇인가요?", "보증금과 월세를 서로 바꿀 때 쓰는 연 이율입니다. 월세 × 12 ÷ (환산 대상 보증금) 으로 계산합니다."),
           ("전환율이 높으면 누구에게 유리한가요?", "같은 월세 기준으로 전환율이 높으면 전세 환산액이 작아져 임차인이 월세를 상대적으로 비싸게 내는 셈입니다.")]
    B.page(p, "보증금 %s 월세 %s만원 전세 환산 — 전월세 전환율별 금액" % (m(d), man(r)), "보증금 %s 월세 %s만원을 전세로 환산하면 전환율 6%%에서 약 %s. 4~10%% 전환율별 전세 환산액 비교." % (m(d), man(r), m(mid)),
           "보증금 %s 월세 %s만원 → 전세 환산" % (m(d), man(r)), "전환율 4~10% 비교 · 월세→전세", body, faq, CRUMB0 + [("월세→전세", "/conv/wolse-to-jeonse/"), ("%s / %s만원" % (m(d), man(r)), p)])

def page_j2w(j, d):
    rows = [["%d%%" % round(x * 100), man(wolse_of(j, d, x)) + "만원", "%s만원" % man(wolse_of(j, d, x) * 12)] for x in RATES]
    mid = wolse_of(j, d, 0.05)
    p = "/conv/jeonse-to-wolse/%d-%d/" % (j, d)
    near = [(jj, d) for jj in JEONSE if jj != j and abs(JEONSE.index(jj) - JEONSE.index(j)) <= 2 and d < jj * .9]
    near += [(j, dd) for dd in KEEP if dd != d and dd < j * .9 and abs(KEEP.index(dd) - KEEP.index(d)) <= 2]
    nt = B.table(["전세금", "남기는 보증금", "월세 (전환율 5%)"], [['<a href="/conv/jeonse-to-wolse/%d-%d/">%s</a>' % (jj, dd, m(jj)), m(dd) if dd else "없음", man(wolse_of(jj, dd, .05)) + "만원"] for jj, dd in near], num=(2,))
    dtxt = ("보증금 %s을 남기고" % m(d)) if d else "보증금 없이 전액"
    body = (B.lead("전세금 <b>%s</b>을 %s 월세로 바꾸면, 전환율 5%%일 때 월세는 약 <b>%s만원</b>입니다. 전환율 4%%부터 10%%까지의 월세를 아래에서 비교해 보세요." % (m(j), dtxt, man(mid)))
            + B.stats([("전세금", m(j)), ("남기는 보증금", m(d) if d else "없음"), ("월세로 바꾸는 금액", m(j - d))])
            + B.sec("📊 전환율별 월세", B.table(["전환율(연)", "월세(만원)", "연 월세 합계"], rows, num=(1, 2)))
            + B.sec("🧮 계산식", '<p class="ctx">월세 = (전세금 − 남기는 보증금) × 전환율 ÷ 12 = (%s − %s) × 전환율 ÷ 12. 전환율 5%%면 %s × 0.05 ÷ 12 = %s만원입니다.</p>' % (man(j), man(d), man(j - d), man(mid)))
            + B.sec("📈 비슷한 조건", nt)
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + "</p>\n" + B.chips(LINKS))
    faq = [("전세 %s을 월세로 바꾸면 얼마인가요?" % m(j), "%s 전환율 5%% 기준 월세 약 %s만원, 4%%면 %s만원, 6%%면 %s만원입니다." % (dtxt, man(mid), man(wolse_of(j, d, .04)), man(wolse_of(j, d, .06)))),
           ("월세 전환 시 법정 상한이 있나요?", "있습니다. 연 10%와 한국은행 기준금리 + 2%p 중 낮은 비율이 상한입니다. 계약 시점의 기준금리를 확인하세요."),
           ("보증금을 더 남기면 월세가 줄어드나요?", "네. 월세로 바꾸는 금액(전세금 − 남기는 보증금)이 줄어들어 월세도 같은 비율로 줄어듭니다.")]
    B.page(p, "전세 %s 월세 전환 — 보증금 %s 남길 때 월세 얼마" % (m(j), m(d) if d else "없이"), "전세금 %s을 %s 월세로 바꾸면 전환율 5%%에서 월세 약 %s만원. 4~10%% 전환율별 월세 비교." % (m(j), dtxt, man(mid)),
           "전세 %s → 월세 전환" % m(j), "%s · 전환율 4~10%% 비교" % (("보증금 %s 남김" % m(d)) if d else "보증금 없음"), body, faq, CRUMB0 + [("전세→월세", "/conv/jeonse-to-wolse/"), ("%s / %s" % (m(j), m(d) if d else "보증금 없음"), p)])

CALC_JS = """<script>
(function(){
function f(n){return Math.round(n).toLocaleString('ko-KR');}
function $(i){return document.getElementById(i);}
$('cv-mode').addEventListener('change',function(){var v=this.value;$('cv-a').style.display=v==='r'?'none':'inline-block';$('cv-r').style.display=v==='j'?'none':'inline-block';$('cv-lbl-a').textContent=v==='w'?'전세금(만원)':v==='j'?'월세(만원)':'전세금(만원)';});
$('cv-go').addEventListener('click',function(){
 var mode=$('cv-mode').value,dep=+$('cv-dep').value||0,rent=+$('cv-rent').value||0,a=+$('cv-all').value||0,rate=(+$('cv-rate').value||0)/100,o=$('cv-out');
 if(mode==='j'){ if(rate<=0||rent<=0){o.textContent='월세와 전환율을 입력하세요.';return;} o.innerHTML='전세 환산액 <b>'+f(dep+rent*12/rate)+'만원</b> (보증금 '+f(dep)+' + 월세 '+f(rent)+' × 12 ÷ '+(rate*100).toFixed(1)+'%)';}
 else if(mode==='w'){ if(rate<=0||a<=dep){o.textContent='전세금이 보증금보다 커야 합니다.';return;} o.innerHTML='월세 <b>'+f((a-dep)*rate/12)+'만원</b> (('+f(a)+' − '+f(dep)+') × '+(rate*100).toFixed(1)+'% ÷ 12)';}
 else { if(a<=dep||rent<=0){o.textContent='전세금>보증금, 월세>0 이어야 합니다.';return;} o.innerHTML='전월세 전환율 <b>'+(rent*12/(a-dep)*100).toFixed(2)+'%</b> (월세 '+f(rent)+' × 12 ÷ ('+f(a)+' − '+f(dep)+'))';}
});
})();
</script>"""

def hub_calc():
    calc = ('<div class="tool-box"><div class="tool-row">'
            '<div><label for="cv-mode">계산 종류</label><select id="cv-mode"><option value="j">월세 → 전세 환산</option><option value="w">전세 → 월세 환산</option><option value="r">전환율 구하기</option></select></div>'
            '<div><label for="cv-dep">보증금(만원)</label><input id="cv-dep" type="number" value="1000" style="width:110px"></div>'
            '<div><label for="cv-rent" id="cv-lbl-r">월세(만원)</label><input id="cv-rent" type="number" value="50" style="width:90px"></div>'
            '<div><label for="cv-all" id="cv-lbl-a">전세금(만원)</label><input id="cv-all" type="number" value="20000" style="width:110px;display:none"></div>'
            '<div><label for="cv-rate">전환율(연 %)</label><input id="cv-rate" type="number" step="0.1" value="5" style="width:80px"></div>'
            '<button class="btn-p" id="cv-go">계산</button></div><div class="tool-out" id="cv-out">값을 입력하고 계산을 누르세요.</div></div>' + CALC_JS)
    ex = B.table(["월세 → 전세 환산 예시", "전환율 4%", "전환율 5%", "전환율 6%"], [["보증금 %s + 월세 %d만원" % (m(d), r)] + [m(round(jeonse_eq(d, r, x))) for x in (0.04, 0.05, 0.06)] for d, r in ((1000, 50), (5000, 80))])
    body = (B.lead("보증금과 월세를 서로 바꿀 때 쓰는 <b>전월세 전환율</b> 계산기입니다. 월세를 전세로 환산하거나, 전세를 월세로 바꾸거나, 현재 계약의 전환율을 거꾸로 구할 수 있습니다.")
            + B.sec("🧮 전월세 전환 계산기", calc)
            + B.sec("📐 공식", '<ul class="ctx"><li>전세 환산액 = 보증금 + 월세 × 12 ÷ 전환율</li><li>월세 = (전세금 − 남기는 보증금) × 전환율 ÷ 12</li><li>전환율 = 월세 × 12 ÷ (전세금 − 보증금)</li></ul>')
            + B.sec("📊 계산 예시", ex + '<p class="ctx" style="font-size:.85rem;color:#6B7280;">예시 금액은 반올림한 값입니다.</p>')
            + B.sec("⚖️ 법정 전환율 상한", '<p class="ctx">%s</p>' % esc(LAW))
            + B.sec("📋 환산표 바로가기", B.chips([("월세→전세 환산표", "/conv/wolse-to-jeonse/"), ("전세→월세 환산표", "/conv/jeonse-to-wolse/"), ("중개수수료 계산", "/fee/"), ("계약 전 체크리스트", "/guide/")]))
            + '  <p class="ctx" style="font-size:.85rem;color:#6B7280;">' + esc(NOTE) + "</p>\n")
    faq = [("전월세 전환율은 어떻게 계산하나요?", "월세 × 12 ÷ (전세금 − 보증금)으로 구합니다. 예를 들어 전세 2억을 보증금 1억 + 월세 40만원으로 바꾸면 40×12÷10,000=4.8%입니다."),
           ("전환율의 법정 상한은 얼마인가요?", "연 10%와 한국은행 기준금리 + 2%p 중 낮은 비율입니다. 기준금리는 변동하므로 계약 시점 값을 확인하세요."),
           ("전세 환산액은 어디에 쓰나요?", "월세 집과 전세 집을 같은 기준으로 비교하거나, 월세 보증금 증액·감액 협의의 기준으로 쓸 수 있습니다.")]
    B.page("/conv/", "전월세 전환율 계산기 — 월세 전세 환산 · 전세 월세 전환", "월세를 전세로, 전세를 월세로 바꾸는 전월세 전환율 계산기. 전환율 구하기와 전환율별 환산표, 법정 상한 계산식.",
           "전월세 전환율 계산기", "월세 ↔ 전세 환산 · 전환율 구하기", body, faq, CRUMB0)

def hub_w2j():
    blocks = ""
    for d in DEPS:
        blocks += B.sec("보증금 %s" % m(d), B.chips([("월세 %s만원" % r, "/conv/wolse-to-jeonse/%d-%d/" % (d, r)) for r in RENTS]))
    body = B.lead("보증금과 월세 조합별로 전세 환산액을 계산해 둔 표입니다. 조합을 눌러 전환율 4~10% 비교를 확인하세요.") + blocks + B.chips(LINKS)
    B.page("/conv/wolse-to-jeonse/", "월세 전세 환산표 — 보증금·월세별 전세 환산액", "보증금 500만~1억, 월세 20~150만원 조합별 전세 환산액. 전환율 4~10% 비교.", "월세 → 전세 환산표", "보증금·월세 조합별", body,
           [("월세를 전세로 환산하는 공식은?", "전세 환산액 = 보증금 + 월세 × 12 ÷ 전환율입니다."), ("전환율은 얼마를 써야 하나요?", "계약 시점의 법정 상한(기준금리+2%p와 10% 중 낮은 값) 이내에서 협의합니다.")], CRUMB0 + [("월세→전세", "/conv/wolse-to-jeonse/")])

def hub_j2w():
    blocks = ""
    for j in JEONSE:
        blocks += B.sec("전세금 %s" % m(j), B.chips([(("보증금 %s 남김" % m(d)) if d else "보증금 없음", "/conv/jeonse-to-wolse/%d-%d/" % (j, d)) for d in KEEP if d < j * .9]))
    body = B.lead("전세금과 남기는 보증금 조합별 월세를 계산해 둔 표입니다. 조합을 눌러 전환율 4~10% 비교를 확인하세요.") + blocks + B.chips(LINKS)
    B.page("/conv/jeonse-to-wolse/", "전세 월세 전환표 — 전세금·보증금별 월세", "전세 5천만~10억, 남기는 보증금별 월세 전환액. 전환율 4~10% 비교.", "전세 → 월세 전환표", "전세금·남기는 보증금 조합별", body,
           [("전세를 월세로 바꾸는 공식은?", "월세 = (전세금 − 남기는 보증금) × 전환율 ÷ 12입니다."), ("전환율 상한이 있나요?", "연 10%와 기준금리+2%p 중 낮은 비율이 상한입니다.")], CRUMB0 + [("전세→월세", "/conv/jeonse-to-wolse/")])

def main():
    if OUTD.exists(): shutil.rmtree(OUTD)
    n = 0
    for d in DEPS:
        for r in RENTS: page_w2j(d, r); n += 1
    for j in JEONSE:
        for d in KEEP:
            if d < j * .9: page_j2w(j, d); n += 1
    hub_calc(); hub_w2j(); hub_j2w(); n += 3
    print("conv pages", n)

if __name__ == "__main__":
    main()

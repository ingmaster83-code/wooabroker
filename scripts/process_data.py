#!/usr/bin/env python3
"""
process_data.py - 전국공인중개사사무소표준데이터를 Jekyll 페이지 생성용 JSON으로 가공 (시도별 분할)

입력: _rawdata/broker_raw.json (fetch_broker.py 결과)
출력: _rawdata/broker_{시도}.json (시도별), search_index.json (루트, 이름 검색용)

사용법: python scripts/process_data.py [--limit N]
"""
import json, re, sys, argparse
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
RAW = ROOT / "_rawdata" / "broker_raw.json"
RAWDATA_DIR = ROOT / "_rawdata"
SEARCH_INDEX_OUT = ROOT / "search_index.json"

DO_MAP = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주", "제주도": "제주",
}

# 동/읍/면 토큰: 한글이 반드시 포함돼야 함(아파트 "101동" 제외). "종로1가" 같은 가 단위 포함.
DONG_TOKEN = re.compile(r"^[가-힣][가-힣0-9]*(?:동|읍|면)$|^[가-힣]+\d+가$")
ROAD_RE = re.compile(r"([가-힣0-9]+(?:대로|로|길))(?:\d+번길)?\s*\d")
ROAD_BASE_RE = re.compile(r"([가-힣0-9]+(?:대로|로|길))")


def clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def split_address(addr):
    """주소 문자열 -> (sido_full, sigungu_display, rest_tokens)"""
    toks = addr.split()
    if len(toks) < 2:
        return None, None, []
    sido_full = toks[0]
    if sido_full == "세종특별자치시":
        return sido_full, "세종시", toks[1:]
    sg = toks[1]
    rest = toks[2:]
    # 일반시 안의 구 (수원시 영통구 등)
    if sg.endswith("시") and rest and rest[0].endswith("구") and len(rest[0]) > 1:
        sg = f"{sg} {rest[0]}"
        rest = rest[1:]
    return sido_full, sg, rest


def dong_from_tokens(tokens):
    for t in tokens:
        t = t.strip("(),")
        if DONG_TOKEN.match(t):
            return t
    return None


def dong_from_paren(addr):
    for m in re.finditer(r"\(([^)]*)\)", addr):
        for part in re.split(r"[,\s]+", m.group(1)):
            if DONG_TOKEN.match(part):
                return part
    return None


def road_name(road_addr):
    m = ROAD_RE.search(road_addr or "")
    return m.group(1) if m else None


def type_label(t):
    t = clean(t)
    if t == "법인":
        return "중개법인"
    if t == "개업공인중개사":
        return "개업공인중개사"
    return "공인중개사"


def to_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if args.limit:
        raw = raw[: args.limit]
        print(f"[--limit] {len(raw)}개만 처리")

    # 개설등록번호 중복은 기준일이 최신인 것만 (이름이 다르면 별개로 취급)
    best = {}
    for d in raw:
        key = (clean(d.get("ESTBL_REG_NO")), clean(d.get("MED_OFFICE_NM")))
        if key not in best or (d.get("CRTR_YMD") or "") > (best[key].get("CRTR_YMD") or ""):
            best[key] = d
    raw = list(best.values())

    items, skipped = [], Counter()
    seen = Counter()
    for d in raw:
        office = clean(d.get("MED_OFFICE_NM"))
        reg = clean(d.get("ESTBL_REG_NO"))
        road = clean(d.get("LCTN_ROAD_NM_ADDR"))
        lot = clean(d.get("LCTN_LOTNO_ADDR"))
        if not office or not reg:
            skipped["no_name_or_reg"] += 1
            continue
        base = road or lot
        sido_full, sg, rest = split_address(base)
        if not sido_full:
            skipped["bad_addr"] += 1
            continue
        if sido_full == "전남광주통합특별시":
            do = "광주" if (sg or "").endswith("구") else "전남"
        else:
            do = DO_MAP.get(sido_full)
        if not do or not sg:
            skipped["no_sido"] += 1
            continue

        dong = None
        if lot:
            _, _, lrest = split_address(lot)
            dong = dong_from_tokens(lrest)
        if not dong and road:
            dong = dong_from_paren(road)
        if not dong and road:
            # 도로명주소의 읍/면 토큰 ("남양주시 오남읍 ...")
            for t in rest[:2]:
                if re.match(r"^[가-힣]+(읍|면)$", t):
                    dong = t
                    break
        dong = dong or "기타"

        slug = re.sub(r"[^0-9A-Za-z가-힣-]", "", reg) or f"x{len(items)}"
        seen[slug] += 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"

        items.append({
            "slug": slug,
            "officeName": office,
            "regNo": reg,
            "kind": type_label(d.get("OPBIZ_LREA_CLSC_SE")),
            "doShort": do,
            "sigungu": sg,
            "sgSlug": sg.replace(" ", "-"),
            "dong": dong,
            "road": road,
            "lot": lot,
            "roadName": road_name(road) or "",
            "tel": clean(d.get("TELNO")),
            "regDate": clean(d.get("ESTBL_REG_YMD")),
            "ddc": clean(d.get("DDC_JOIN_YN")),
            "rep": clean(d.get("RPRSV_NM")),
            "emp": to_int(d.get("OGDP_LREA_CNT")),
            "asst": to_int(d.get("MED_SPMBR_CNT")),
            "home": clean(d.get("HMPG_ADDR")),
            "refDate": clean(d.get("CRTR_YMD")),
        })

    # 동/도로 단위 통계를 각 레코드에 미리 계산 (페이지 차별화용)
    by_dong = defaultdict(list)
    by_road = defaultdict(list)
    for i in items:
        by_dong[(i["doShort"], i["sigungu"], i["dong"])].append(i)
        if i["roadName"]:
            by_road[(i["doShort"], i["sigungu"], i["roadName"])].append(i)
    for key, lst in by_dong.items():
        lst.sort(key=lambda x: (x["regDate"] or "9999", x["regNo"]))
        for rank, i in enumerate(lst, 1):
            i["dongCount"] = len(lst)
            i["dongRank"] = rank  # 개설등록이 오래된 순서
    for key, lst in by_road.items():
        for i in lst:
            i["roadCount"] = len(lst)

    RAWDATA_DIR.mkdir(parents=True, exist_ok=True)
    for old in RAWDATA_DIR.glob("broker_*.json"):
        if old.name != "broker_raw.json":
            old.unlink()
    by_do = defaultdict(list)
    for i in items:
        by_do[i["doShort"]].append(i)
    for do, group in by_do.items():
        out = RAWDATA_DIR / f"broker_{do}.json"
        out.write_text(json.dumps(group, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  {do}: {len(group)}개 → {out.name} ({out.stat().st_size/1024/1024:.1f}MB)")

    no_dong = sum(1 for i in items if i["dong"] == "기타")
    print(f"\n총 {len(items)}개 (제외 {dict(skipped)})")
    print(f"시군구 {len({(i['doShort'], i['sigungu']) for i in items})}개, 동/읍/면 {len(by_dong)}개 (기타 {no_dong}개 = {no_dong/len(items)*100:.1f}%)")
    road_hubs = [k for k, v in by_road.items() if len(v) >= 3]
    print(f"도로 허브(3곳 이상) 후보: {len(road_hubs)}개")

    index = [{"n": i["officeName"], "s": i["slug"], "do": i["doShort"], "sg": i["sigungu"], "dg": i["dong"]} for i in items]
    SEARCH_INDEX_OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"검색 인덱스 {len(index)}건 ({SEARCH_INDEX_OUT.stat().st_size/1024/1024:.1f}MB)")


if __name__ == "__main__":
    main()

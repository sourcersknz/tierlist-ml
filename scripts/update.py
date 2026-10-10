# -*- coding: utf-8 -*-
"""
MLBB ティア表 データ更新スクリプト

処理:
  1. Moonton統計API から Gミシック・7日間のヒーロー統計を取得
  2. data/master.json（日本語名・レーン・main）とマージ
  3. template.html にデータを埋め込み、index.html を生成

実行: python scripts/update.py
"""
import json
import os
import sys
import datetime

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(ROOT, "data", "master.json")
TEMPLATE_PATH = os.path.join(ROOT, "template.html")
OUTPUT_PATH = os.path.join(ROOT, "index.html")
SNAPSHOT_DIR = os.path.join(ROOT, "data", "snapshots")

# 7日間集計 (1日=2756567 / 3日=2756568 / 7日=2756569 / 15日=2756565 / 30日=2756570)
URL = "https://api.gms.moontontech.com/api/gms/source/2669606/2756569"

# bigrank: all=101 / epic=5 / legend=6 / mythic=7 / honor=8 / glory=9
BIGRANK = "9"  # Gミシック

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://www.mobilelegends.com",
    "Referer": "https://www.mobilelegends.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    ),
}

PAYLOAD = {
    "pageSize": 200,
    "pageIndex": 1,
    "filters": [
        {"field": "bigrank", "operator": "eq", "value": BIGRANK},
        {"field": "match_type", "operator": "eq", "value": "0"},
    ],
    "sorts": [
        {"data": {"field": "main_hero_win_rate", "order": "desc"}, "type": "sequence"}
    ],
    "fields": [
        "main_hero",
        "main_heroid",
        "main_hero_appearance_rate",
        "main_hero_win_rate",
        "main_hero_ban_rate",
        "data.sub_hero.heroid",
        "data.sub_hero.increase_win_rate",
    ],
}

LANE_ORDER = ["roam", "exp", "jg", "mid", "gold"]
LANE_LABEL = {"roam": "Roam", "exp": "Exp", "jg": "JG", "mid": "Mid", "gold": "Gold"}
LANE_EMOJI = {"roam": "\U0001F300", "exp": "\u2694\uFE0F", "jg": "\U0001F33F",
              "mid": "\U0001F52E", "gold": "\U0001F3F9"}


def fetch_records():
    """Moonton統計APIからレコードを取得する。"""
    print(f"POST {URL} (bigrank={BIGRANK})")
    r = requests.post(URL, json=PAYLOAD, headers=HEADERS, timeout=45)
    print(f"  HTTP {r.status_code} / {len(r.content):,} bytes")
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    records = r.json().get("data", {}).get("records", [])
    if not records:
        raise RuntimeError("records が空。API仕様が変わった可能性があります。")
    print(f"  取得: {len(records)} 件")
    return records


def build_heroes(records, master):
    """統計レコードと台帳をマージしてヒーロー配列を作る。"""
    heroes = []
    unknown = []
    for rec in records:
        d = rec["data"]
        hid = d["main_heroid"]
        m = master.get(str(hid), {})
        if not m:
            unknown.append((hid, d["main_hero"]["data"]["name"]))
        lanes = list(m.get("lanes") or [])
        main = m.get("main")
        if main and main not in lanes:
            lanes.append(main)
        heroes.append({
            "id": hid,
            "name": m.get("name") or d["main_hero"]["data"]["name"],
            "en": d["main_hero"]["data"]["name"],
            "head": d["main_hero"]["data"].get("head", ""),
            "pick": round(d["main_hero_appearance_rate"], 5),
            "win": round(d["main_hero_win_rate"], 5),
            "ban": round(d["main_hero_ban_rate"], 5),
            "lanes": lanes,
            "main": main,
            "sub": [
                {"id": s["heroid"], "inc": round(s["increase_win_rate"], 5)}
                for s in d.get("sub_hero", [])
            ],
        })
    if unknown:
        print("  [注意] 台帳に無いヒーロー（英語名で表示されます）:")
        for hid, en in unknown:
            print(f"    id={hid} {en}  → data/master.json に追加してください")
    return heroes


def render(heroes, updated):
    """template.html にデータを流し込んで index.html を書き出す。"""
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        html = f.read()

    payload = {"updated": updated, "rank": "Gミシック", "span": "7日間", "heroes": heroes}
    data_js = "const RAW = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";"

    lanes = ["const LANES = ["]
    for lane in LANE_ORDER:
        lanes.append('  {id:"%s",label:"%s",emoji:"%s"},'
                     % (lane, LANE_LABEL[lane], LANE_EMOJI[lane]))
    lanes.append("];")
    lanes_js = "\n".join(lanes)

    # カウンターデータ（data/counter.json があれば埋め込む）
    counter_path = os.path.join(ROOT, "data", "counter.json")
    if os.path.exists(counter_path):
        with open(counter_path, encoding="utf-8") as f:
            counter_data = json.load(f)
        counter_js = "const COUNTER = " + json.dumps(counter_data, ensure_ascii=False, separators=(",", ":")) + ";"
    else:
        counter_js = "const COUNTER = {heroes:[]};"

    if "/*__DATA__*/" not in html or "/*__LANES__*/" not in html:
        raise RuntimeError("template.html にプレースホルダが見つかりません。")

    html = (html.replace("/*__DATA__*/", data_js)
                .replace("/*__LANES__*/", lanes_js)
                .replace("/*__COUNTER__*/", counter_js))
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  index.html を生成 ({len(html):,} bytes)")


def save_snapshot(heroes, updated):
    """日次スナップショットを残す（メタ推移の記録用）。"""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    day = updated[:10]
    path = os.path.join(SNAPSHOT_DIR, f"{day}.json")
    slim = [{"id": h["id"], "pick": h["pick"], "win": h["win"], "ban": h["ban"]} for h in heroes]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"updated": updated, "heroes": slim}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  スナップショット: data/snapshots/{day}.json")


def main():
    jst = datetime.timezone(datetime.timedelta(hours=9))
    updated = datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M")

    with open(MASTER_PATH, encoding="utf-8") as f:
        master = json.load(f)
    print(f"台帳: {len(master)} 体")

    records = fetch_records()
    heroes = build_heroes(records, master)
    render(heroes, updated)
    save_snapshot(heroes, updated)
    print(f"完了: {updated} JST")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[失敗] {type(e).__name__}: {e}")
        sys.exit(1)

"""Create a 19-second fixed-camera cutout list-comedy replica fixture.

The fixture intentionally mirrors the reference structure rather than its exact
art: one couch background, two mostly static cutout characters, rapid prop
replacement, hard cuts, a bright era label, and bottom subtitles.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from pipeline import save

WIDTH, HEIGHT, FPS = 960, 540, 24
ITEMS = [
    "竹蜻蜓", "铁皮青蛙", "东南西北", "嘎拉哈", "绿豆糕",
    "三鲜伊面", "麦丽素", "无花果", "猴王丹", "滚地龙",
    "酒心糖", "冰袋", "山楂糕", "麦芽糖", "葫芦兄弟录像带",
    "黑猫警长录像带", "天书奇谭录像带", "舒克和贝塔录像带",
    "三个和尚录像带", "大闹天宫录像带",
]
DURATIONS = [22] * 12 + [24] * 8  # exactly 456 frames = 19 seconds


def _layer():
    return Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))


def _mark_unique(image: Image.Image, index: int):
    # Invisible RGB marker under alpha=0: visually identical, unique file digest.
    image.putpixel((0, 0), ((index * 31) % 255, (index * 73) % 255, (index * 127) % 255, 0))


def _background() -> Image.Image:
    img = Image.new("RGBA", (WIDTH, HEIGHT), "#918b80")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 318, WIDTH, HEIGHT), fill="#171717")
    d.line((0, 400, WIDTH, 400), fill="#4a4a4a", width=5)
    d.line((0, 470, WIDTH, 470), fill="#353535", width=4)
    # couch
    d.rounded_rectangle((42, 122, 925, 337), 28, fill="#efbd68", outline="#111111", width=5)
    for x in (62, 285, 515, 742):
        d.rounded_rectangle((x, 142, x + 165, 300), 22, fill="#f6d99d", outline="#111111", width=4)
    # upper wall line and era card
    d.line((0, 106, WIDTH, 106), fill="#3c3934", width=5)
    d.rounded_rectangle((690, 28, 842, 88), 10, fill="#efefef", outline="#1b1b1b", width=3)
    d.text((714, 40), "80s", fill="#23b51d", stroke_width=2, stroke_fill="white")
    return img


def _panda(index: int) -> Image.Image:
    img = _layer()
    d = ImageDraw.Draw(img)
    # body
    d.rounded_rectangle((105, 220, 302, 462), 32, fill="#efa900", outline="#111111", width=5)
    d.rectangle((122, 293, 285, 341), fill="#f4c12c", outline="#111111", width=4)
    d.rectangle((114, 452, 188, 540), fill="#111111")
    d.rectangle((219, 452, 292, 540), fill="#111111")
    # panda ears + face
    d.ellipse((116, 100, 170, 154), fill="#111111")
    d.ellipse((241, 100, 295, 154), fill="#111111")
    d.ellipse((132, 106, 282, 245), fill="white", outline="#111111", width=5)
    # simple meme-like facial expression without copying exact face
    d.arc((164, 155, 205, 183), 195, 345, fill="#111111", width=3)
    d.arc((213, 155, 254, 183), 195, 345, fill="#111111", width=3)
    d.line((207, 178, 204, 195), fill="#111111", width=3)
    d.arc((177, 186, 240, 224), 8, 170, fill="#111111", width=4)
    _mark_unique(img, index)
    return img


def _kid(index: int) -> Image.Image:
    img = _layer()
    d = ImageDraw.Draw(img)
    # legs
    d.polygon([(618, 405), (663, 405), (654, 535), (606, 535)], fill="#4d6140", outline="#111111")
    d.polygon([(674, 405), (718, 405), (742, 535), (694, 535)], fill="#4d6140", outline="#111111")
    # torso / jacket
    d.polygon([(584, 260), (688, 242), (754, 418), (616, 432)], fill="#f3f3f3", outline="#111111")
    d.polygon([(650, 255), (688, 242), (704, 333), (665, 339)], fill="#d7d7d7", outline="#111111")
    # scarf
    d.polygon([(643, 257), (682, 258), (673, 289), (649, 287)], fill="#d82922", outline="#111111")
    # satchel
    d.polygon([(692, 330), (767, 342), (757, 447), (682, 436)], fill="#6f7651", outline="#111111", width=3)
    d.line((650, 266, 724, 373), fill="#2f2f2f", width=7)
    # head/hair
    d.ellipse((606, 123, 721, 248), fill="#f2cfb5", outline="#111111", width=4)
    d.pieslice((600, 106, 730, 208), 180, 360, fill="#111111")
    d.rectangle((612, 125, 720, 153), fill="#111111")
    # face
    d.ellipse((634, 171, 643, 181), fill="#111111")
    d.ellipse((684, 171, 693, 181), fill="#111111")
    d.arc((651, 188, 681, 213), 5, 170, fill="#111111", width=3)
    # arm changes every other shot: small present gesture
    lift = (index % 3) * 7
    d.line((604, 292, 523, 324 - lift), fill="#f2cfb5", width=21)
    d.ellipse((505, 308 - lift, 535, 337 - lift), fill="#f2cfb5", outline="#111111")
    d.line((736, 293, 771, 349), fill="#f2cfb5", width=18)
    _mark_unique(img, 100 + index)
    return img


def _prop(index: int) -> Image.Image:
    img = _layer()
    d = ImageDraw.Draw(img)
    x, y = 490, 315
    mode = index
    if mode == 0:  # bamboo-copter
        d.line((x, y, x, y + 65), fill="#6d4b24", width=10)
        d.line((x - 55, y, x + 55, y), fill="#e6b22f", width=12)
        d.ellipse((x - 10, y - 10, x + 10, y + 10), fill="#c7432b")
    elif mode == 1:  # tin frog
        d.ellipse((x - 48, y + 8, x + 48, y + 58), fill="#5fa74d", outline="#17351b", width=4)
        d.ellipse((x - 34, y - 8, x - 12, y + 15), fill="#e7df85", outline="#17351b")
        d.ellipse((x + 12, y - 8, x + 34, y + 15), fill="#e7df85", outline="#17351b")
    elif mode == 2:  # paper fortune teller
        d.polygon([(x, y - 45), (x + 58, y), (x, y + 45), (x - 58, y)], fill="#e7e7e7", outline="#222222")
        d.line((x - 58, y, x + 58, y), fill="#777777", width=3)
        d.line((x, y - 45, x, y + 45), fill="#777777", width=3)
    elif mode == 3:  # knucklebones
        for ox, oy in [(-35, 5), (0, -10), (35, 8), (-15, 35), (23, 38)]:
            d.ellipse((x + ox - 13, y + oy - 13, x + ox + 13, y + oy + 13), fill="#ddd0ae", outline="#555555")
    elif mode in (4, 5, 6, 7, 8, 9, 10, 11):
        colors = ["#e7c96f", "#ffd235", "#c42925", "#c0beb6", "#d94b31", "#f08132", "#e25ca0", "#7fc6e8"]
        d.rounded_rectangle((x - 58, y - 48, x + 58, y + 62), 12, fill=colors[mode - 4], outline="#222222", width=4)
        d.rectangle((x - 40, y - 22, x + 40, y + 10), fill="#fff2c6")
        for i in range(5):
            d.ellipse((x - 40 + i * 18, y + 22, x - 25 + i * 18, y + 37), fill="#8e4e2f")
    elif mode in (12, 13):
        for i in range(5):
            d.ellipse((x - 58 + i * 26, y + 12 + (i % 2) * 10, x - 35 + i * 26, y + 35 + (i % 2) * 10),
                      fill="#b84235" if mode == 12 else "#ad7d34", outline="#6b3028")
    else:  # VHS stacks
        count = min(1 + mode - 13, 6)
        palette = ["#2775b7", "#e5bf40", "#d94c3b", "#6b9d52", "#794f9d", "#dd7a35"]
        for i in range(count):
            ox = (i % 3) * 44 - 50
            oy = (i // 3) * 45 - 25
            d.rectangle((x + ox, y + oy, x + ox + 80, y + oy + 38),
                        fill=palette[i % len(palette)], outline="#171717", width=3)
            d.rectangle((x + ox + 8, y + oy + 7, x + ox + 71, y + oy + 18), fill="#eeeeee")
    _mark_unique(img, 200 + index)
    return img


def _manifest(cid: str, name: str, role: str) -> dict:
    return {
        "id": cid,
        "name": name,
        "story_role": role,
        "identity": {
            "face": "simple black-outline comedy face",
            "hair": "fixed graphic silhouette",
            "clothing": "fixed outfit",
            "proportions": "flat cutout proportions",
            "distinctive_features": "stable silhouette and color blocking",
        },
        "reference": {
            "image": f"characters/{cid}/reference.png",
            "status": "planned",
            "locks": "identity_only",
            "prompt": "Synthetic cutout reference generated by fixture.",
        },
    }


def build(project: Path) -> Path:
    if project.exists():
        raise FileExistsError(f"Use a new output directory: {project}")
    project.mkdir(parents=True)

    original_content = "、".join(ITEMS)
    brief = {
        "version": "0.1",
        "project_id": "fixed-list-comedy-replica",
        "title": "Fixed-camera list comedy replica",
        "original_content": original_content,
        "content_preservation": [
            "One fixed couch scene with two cutout characters.",
            "Rapid item replacement and hard cuts drive the rhythm.",
            "Bottom subtitles name the item currently being shown.",
        ],
        "setting": {"place": "generic living room", "era": "retro nostalgia", "culture": "Chinese everyday nostalgia"},
        "visual_language": "flat black-outline cutout comedy, simple shapes, fixed camera, prop-led rhythm",
        "style_preset": "simple-comic",
        "tone": "deadpan nostalgic list comedy",
        "format": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "duration_frames": sum(DURATIONS)},
        "assumptions": ["Synthetic art recreates structure and pacing rather than copying the source artwork pixel-for-pixel."],
    }
    characters = {
        "version": "0.1",
        "project_id": brief["project_id"],
        "characters": [
            _manifest("panda", "熊猫头大人", "left static reaction character"),
            _manifest("kid", "怀旧小孩", "right presenting character"),
        ],
    }
    board = {
        "version": "0.1",
        "project_id": brief["project_id"],
        "scenes": [{
            "id": "living-room",
            "space": "Fixed front-facing couch scene with left and right character slots.",
            "time": "day",
            "lighting": "flat even cartoon lighting",
            "anchors": ["panda left", "kid right", "prop center-right", "subtitle bottom"],
        }],
        "beats": [],
        "shots": [],
    }
    motion = {
        "version": "0.4",
        "project_id": brief["project_id"],
        "asset_mode": "fixture",
        "shots": [],
    }

    bg_base = _background()
    cursor = 0
    for index, (item, duration) in enumerate(zip(ITEMS, DURATIONS)):
        sid = f"shot_{index + 1:03d}"
        beat_id = f"b{index + 1:02d}"
        folder = project / "shots" / sid / "layers"
        folder.mkdir(parents=True, exist_ok=True)

        bg = bg_base.copy()
        panda = _panda(index)
        kid = _kid(index)
        prop = _prop(index)

        bg_path = folder / "bg.png"
        panda_path = folder / "panda.png"
        kid_path = folder / "kid.png"
        prop_path = folder / "prop.png"
        bg.save(bg_path)
        panda.save(panda_path)
        kid.save(kid_path)
        prop.save(prop_path)

        master = bg.copy()
        for layer in (panda, kid, prop):
            master = Image.alpha_composite(master, layer)
        master.save(project / "shots" / sid / "master.png")

        board["beats"].append({
            "id": beat_id,
            "source_excerpt": item,
            "change": f"Replace the displayed object with {item}.",
            "emotion": "nostalgic deadpan",
        })
        board["shots"].append({
            "id": sid,
            "source_panel": f"reference-structure-{index + 1}",
            "beat_id": beat_id,
            "duration_frames": duration,
            "purpose": f"Present {item} as the next rapid nostalgia item.",
            "transition": "cut",
            "setting": "fixed couch living room",
            "shot_size": "medium",
            "angle": "eye_level",
            "composition": "locked two-shot; panda on left, child on right, prop between them",
            "composition_tag": "locked_two_shot",
            "characters": [
                {"character_id": "panda", "action": "stand still and react", "pose_tag": "idle", "expression": "deadpan smile", "gaze": "kid"},
                {"character_id": "kid", "action": f"present {item}", "pose_tag": "present", "expression": "matter-of-fact", "gaze": "prop"},
            ],
            "continuity": "Background, screen direction and character slots do not change; only the prop and tiny hand angle vary.",
            "master": f"shots/{sid}/master.png",
            "layers": [
                {"id": "bg", "role": "background", "elements": "wall, couch and dark floor", "method": "reconstruct", "reason": "locked scene"},
                {"id": "panda", "role": "character", "character_id": "panda", "elements": "left panda-headed adult", "method": "reconstruct", "reason": "fixed character slot"},
                {"id": "kid", "role": "character", "character_id": "kid", "elements": "right child presenter", "method": "reconstruct", "reason": "fixed presenter slot"},
                {"id": "prop", "role": "foreground", "elements": item, "method": "reconstruct", "reason": "rapid item replacement"},
            ],
            "repetition_exception": "Locked composition is intentional; repetition is the format.",
            "dialogue": [{"speaker": "kid", "text": item, "start_frame": 1, "end_frame": duration - 1}],
            "direction": {
                "scene_id": "living-room",
                "camera_position": "front locked",
                "background_view": "same couch view",
                "view_id": "fixed-front",
                "incoming_state": "Both characters remain in the same slots.",
                "outgoing_state": "The displayed prop is replaced on the next hard cut.",
                "micro_actions": "Only a tiny presenting-hand variation; otherwise still.",
                "cut_reason": "Advance the rapid nostalgia list.",
                "next_shot_id": f"shot_{index + 2:03d}" if index + 1 < len(ITEMS) else None,
                "handoff": "Hard cut on the next item with identical geography.",
                "reaction_hold_frames": 1,
                "listening_reactions": [{"character_id": "panda", "response": "remain still"}],
            },
        })

        identity = {"x": 0, "y": 0, "scale": 1}
        motion["shots"].append({
            "shot_id": sid,
            "start_frame": cursor,
            "duration_frames": duration,
            "transition": "cut",
            "performance": {
                "mode": "cutout-comedy",
                "intent": f"Locked list-comedy display for {item}.",
                "static_reason": "Reference format is intentionally nearly static; the hard-cut prop replacement carries the beat.",
                "reviewed": False,
            },
            "camera": {"type": "static", "parallax_enabled": False},
            "layers": [
                {"layer_id": "bg", "asset": f"shots/{sid}/layers/bg.png", "depth": "background", "z": 0, "from": identity, "to": identity},
                {"layer_id": "panda", "asset": f"shots/{sid}/layers/panda.png", "depth": "character", "z": 10, "from": identity, "to": identity},
                {"layer_id": "kid", "asset": f"shots/{sid}/layers/kid.png", "depth": "character", "z": 20, "from": identity, "to": identity},
                {"layer_id": "prop", "asset": f"shots/{sid}/layers/prop.png", "depth": "foreground", "z": 30, "from": identity, "to": identity},
            ],
            "review": {
                "master_alignment": False,
                "background_completed": False,
                "motion_bounds_checked": False,
                "notes": "Synthetic reference-structure replica fixture; not production art.",
            },
        })
        cursor += duration

    save(project / "production_brief.json", brief)
    save(project / "characters.json", characters)
    save(project / "storyboard.json", board)
    save(project / "motion_plan.json", motion)
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path)
    print(build(parser.parse_args().project.resolve()))

"""Resolve semantic shot intent against reusable scene and character manifests."""
from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPTHS = {"foreground", "character", "midground", "background", "sky"}


def framing_config():
    return json.loads((ROOT / "config" / "framing_presets.json").read_text(encoding="utf-8"))


def _point(value, width, height):
    return float(value[0]) * width, float(value[1]) * height


def _rect(value, width, height):
    return {
        "left": value["left"] * width, "top": value["top"] * height,
        "right": value["right"] * width, "bottom": value["bottom"] * height,
    }


def _union(rects):
    return {
        "left": min(rect["left"] for rect in rects),
        "top": min(rect["top"] for rect in rects),
        "right": max(rect["right"] for rect in rects),
        "bottom": max(rect["bottom"] for rect in rects),
    }


def _center(rect):
    return (rect["left"] + rect["right"]) / 2, (rect["top"] + rect["bottom"]) / 2


def _character_world(character_id, slot_id, scene, character_assets):
    slots = scene["character_slots"]
    if slot_id not in slots:
        raise ValueError(f"Character {character_id} binds to unknown scene slot {slot_id}")
    manifest = next((item for item in character_assets["characters"]
                     if item["character_id"] == character_id), None)
    if not manifest:
        raise ValueError(f"Character {character_id} has no Character Asset Manifest")
    slot = slots[slot_id]
    ref_w, ref_h = manifest["reference_size"]["width"], manifest["reference_size"]["height"]
    root_x, root_y = _point(slot["position"], scene["reference_size"]["width"], scene["reference_size"]["height"])
    root_anchor = manifest["root_anchor"]
    facing = slot["facing"]

    def world_point(norm):
        return (root_x + (norm[0] - root_anchor[0]) * ref_w * slot["scale"] * facing,
                root_y + (norm[1] - root_anchor[1]) * ref_h * slot["scale"])

    def world_rect(norm):
        first = world_point([norm["left"], norm["top"]])
        second = world_point([norm["right"], norm["bottom"]])
        return {"left": min(first[0], second[0]), "top": min(first[1], second[1]),
                "right": max(first[0], second[0]), "bottom": max(first[1], second[1])}

    anchors = manifest["anchors"]
    return {
        "character_id": character_id, "slot_id": slot_id,
        "root": (root_x, root_y), "face": world_point(anchors["face"]["position"]),
        "body": world_point(anchors["body"]["position"]),
        "head": world_point(anchors.get("head", anchors["face"])["position"]),
        "bounds": world_rect(manifest["bounds"]),
        "face_bounds": world_rect(anchors["face"]["bounds"]),
        "body_bounds": world_rect(anchors["body"]["bounds"]),
        "head_bounds": world_rect(anchors.get("head", anchors["face"])["bounds"]),
        "scale": slot["scale"], "facing": facing,
    }


def _object_world(object_id, scene, width, height):
    item = next((obj for obj in scene["objects"] if obj["id"] == object_id), None)
    if item:
        x, y = _point(item["position"], width, height)
        w, h = item["size"][0] * width, item["size"][1] * height
        return {"id": object_id, "point": (x, y),
                "bounds": {"left": x - w * item["pivot"][0], "top": y - h * item["pivot"][1],
                           "right": x + w * (1 - item["pivot"][0]), "bottom": y + h * (1 - item["pivot"][1])}}
    anchor = scene["composition_anchors"].get(object_id)
    if anchor is None:
        raise ValueError(f"Unknown focus object/composition anchor {object_id}")
    if isinstance(anchor, list):
        position, bounds = anchor, None
    else:
        position, bounds = anchor["position"], anchor.get("bounds")
    point = _point(position, width, height)
    return {"id": object_id, "point": point,
            "bounds": _rect(bounds, width, height) if bounds else {"left": point[0] - 16, "top": point[1] - 16,
                                                                      "right": point[0] + 16, "bottom": point[1] + 16}}


def _clamp_camera_target(target, desired_zoom, screen, scene, viewport, parallax, parallax_strengths=None):
    """Find a safe focus/zoom pair that keeps background coverage and safe bounds."""
    width, height = viewport["width"], viewport["height"]
    ref_w, ref_h = scene["reference_size"]["width"], scene["reference_size"]["height"]
    coverage = _rect(scene["background_coverage_bounds"], ref_w, ref_h)
    safe = _rect(scene["camera_safe_bounds"], ref_w, ref_h)
    strengths = {layer["depth"]: {"foreground": 1.2, "character": 1.0, "midground": .55,
                                  "background": .2, "sky": .05}[layer["depth"]]
                 for layer in scene["layers"] if layer["kind"] == "render_layer"}
    strengths.update(parallax_strengths or {})
    background_depth = "background" if "background" in strengths else ("sky" if "sky" in strengths else None)
    strength = strengths.get(background_depth, 1) if parallax and background_depth else 1
    # Preserve the focal subject and planned zoom first. If the background has no
    # overscan, move its screen placement just enough to keep the entire viewport
    # on painted background. Escalate zoom only if no placement is possible.
    zoom = max(desired_zoom, 1)
    for _ in range(1000):
        effective_zoom = 1 + (zoom - 1) * strength
        camera_target = (min(max(target[0], safe["left"]), safe["right"]),
                         min(max(target[1], safe["top"]), safe["bottom"]))
        screen_x_low = max(0, 1 - (coverage["right"] - camera_target[0]) * effective_zoom / width)
        screen_x_high = min(1, (camera_target[0] - coverage["left"]) * effective_zoom / width)
        screen_y_low = max(0, 1 - (coverage["bottom"] - camera_target[1]) * effective_zoom / height)
        screen_y_high = min(1, (camera_target[1] - coverage["top"]) * effective_zoom / height)
        if screen_x_low <= screen_x_high and screen_y_low <= screen_y_high:
            safe_screen = (min(max(screen[0], screen_x_low), screen_x_high),
                           min(max(screen[1], screen_y_low), screen_y_high))
            changed = (camera_target != target or safe_screen != screen or zoom > desired_zoom + 1e-7)
            return camera_target, safe_screen, zoom, changed
        zoom += .01
    raise ValueError("Scene camera_safe_bounds cannot contain the requested camera viewport")


def resolve_composition(scene, character_assets, shot_intent, visible_characters,
                        focus_character=None, focus_object=None, character_bindings=None,
                        visible_objects=None, viewport=None, presets=None,
                        parallax_enabled=None, parallax_strengths=None):
    """Map high-level shot intent and bound scene instances to a camera target."""
    config = presets or framing_config()
    framing = config["shot_intents"][shot_intent]
    preset = config["framing"][framing]
    ref_w, ref_h = scene["reference_size"]["width"], scene["reference_size"]["height"]
    viewport = viewport or {"width": ref_w, "height": ref_h}
    visible = list(dict.fromkeys(visible_characters))
    binding_defaults = {item["character_id"]: item["slot_id"] for item in scene["character_instances"]}
    bindings = {**binding_defaults, **(character_bindings or {})}
    if not set(visible) <= set(bindings):
        raise ValueError("Visible character has no Scene Character Slot binding: " + ", ".join(sorted(set(visible) - set(bindings))))
    character_world = {cid: _character_world(cid, bindings[cid], scene, character_assets) for cid in visible}
    objects = list(visible_objects or ([focus_object] if focus_object else []))
    for object_id in objects:
        _object_world(object_id, scene, ref_w, ref_h)

    target_type = preset["target"]
    target_id = None
    if target_type == "scene_bounds":
        target_bounds = {"left": 0, "top": 0, "right": ref_w, "bottom": ref_h}
        target = _center(target_bounds)
    elif target_type == "characters_bounds":
        needed = 2 if framing == "two_shot" else 1
        if len(visible) < needed:
            raise ValueError(f"{framing} framing needs at least {needed} visible characters")
        selected = [character_world[cid] for cid in visible]
        target_bounds = _union([item["bounds"] for item in selected])
        target = _center(target_bounds)
        target_id = ",".join(visible)
    elif target_type in ("body_anchor", "face_anchor", "head_anchor"):
        target_id = focus_character
        if target_id is None and shot_intent == "speaker_closeup":
            target_id = focus_character
        if target_id not in character_world:
            raise ValueError(f"{shot_intent} needs a visible focus_character with a {target_type}")
        subject = character_world[target_id]
        target = subject[{"body_anchor": "body", "face_anchor": "face", "head_anchor": "head"}[target_type]]
        target_bounds = subject[{"body_anchor": "body_bounds", "face_anchor": "face_bounds", "head_anchor": "head_bounds"}[target_type]]
    elif target_type == "object_anchor":
        target_id = focus_object
        if not target_id:
            raise ValueError("insert framing needs focus_object")
        subject = _object_world(target_id, scene, ref_w, ref_h)
        target, target_bounds = subject["point"], subject["bounds"]
    else:
        raise ValueError(f"Unsupported framing target type {target_type}")

    bounds_w = max(1, target_bounds["right"] - target_bounds["left"])
    bounds_h = max(1, target_bounds["bottom"] - target_bounds["top"])
    coverage_x, coverage_y = preset["subject_coverage"]
    zoom = min(viewport["width"] * coverage_x / bounds_w,
               viewport["height"] * coverage_y / bounds_h)
    # Wide means reveal the room rather than zooming until a tiny stage fills it.
    if framing == "wide":
        zoom = min(zoom, min(viewport["width"] / ref_w, viewport["height"] / ref_h))
    screen = tuple(preset["screen_position"])
    has_depth_layers = len({layer["depth"] for layer in scene["layers"] if layer["kind"] == "render_layer"}) > 1
    safe_target, safe_screen, safe_zoom, safe_clamped = _clamp_camera_target(
        target, zoom, screen, scene, viewport,
        parallax=has_depth_layers if parallax_enabled is None else parallax_enabled,
        parallax_strengths=parallax_strengths)
    target_details = {"id": target_id, "x": safe_target[0], "y": safe_target[1],
                      "subject_x": target[0], "subject_y": target[1]}
    return {
        "shot_intent": shot_intent, "framing": framing, "target_type": target_type,
        "target": target_details, "target_bounds": target_bounds,
        "zoom": safe_zoom, "screen_target": {"x": safe_screen[0], "y": safe_screen[1]},
        "parallax_enabled": has_depth_layers if parallax_enabled is None else parallax_enabled,
        "safe_clamped": safe_clamped,
        "visible_characters": visible, "visible_objects": objects,
        "scene_instances": [{"character_id": cid, "slot_id": bindings[cid], "visible": True}
                            for cid in visible],
        "warnings": (["Camera target/zoom adjusted to stay inside scene coverage bounds"] if safe_clamped else []),
    }


def validate_scene_manifests(scene, character_assets, capabilities, project, local, canvas):
    """Cross-check graph links, capabilities, file paths, dimensions, slots and anchors."""
    from PIL import Image
    errors = []
    if scene["project_id"] != character_assets["project_id"]:
        errors.append("scene/character asset project_id mismatch")
    if scene["reference_size"] != {"width": canvas["width"], "height": canvas["height"]}:
        errors.append("Scene reference_size must match renderer format")
    cap_by_id = {item["id"]: item.get("capabilities", {}) for item in capabilities}
    asset_by_id = {item["character_id"]: item for item in character_assets["characters"]}
    if set(cap_by_id) != set(asset_by_id):
        errors.append("Character Capability/Asset Manifest ids must match")
    graph_nodes = {item["id"]: item for item in scene["layers"]}
    graph_nodes.update({item["id"]: item for item in scene["objects"]})
    for item in scene["layers"]:
        if item["parent_id"] is not None and item["parent_id"] not in graph_nodes:
            errors.append(f"Scene layer {item['id']} has unknown parent {item['parent_id']}")
    for item in scene["objects"]:
        if item["parent_id"] not in graph_nodes:
            errors.append(f"Scene object {item['id']} has unknown parent {item['parent_id']}")
    for node_id, node in graph_nodes.items():
        seen, parent = {node_id}, node.get("parent_id")
        while parent:
            if parent in seen:
                errors.append(f"Scene Graph parent cycle at {node_id}")
                break
            seen.add(parent)
            parent_node = graph_nodes.get(parent)
            parent = parent_node.get("parent_id") if parent_node else None
    for slot_id, slot in scene["character_slots"].items():
        if slot["parent_id"] not in graph_nodes:
            errors.append(f"Character slot {slot_id} has unknown parent {slot['parent_id']}")
    for instance in scene["character_instances"]:
        if instance["character_id"] not in asset_by_id:
            errors.append("Scene Character Instance has unknown character " + instance["character_id"])
        if instance["slot_id"] not in scene["character_slots"]:
            errors.append("Scene Character Instance has unknown slot " + instance["slot_id"])
    depths = {item["depth"] for item in scene["layers"]}
    if not depths <= DEPTHS:
        errors.append("Scene layer uses unsupported depth")
    for rect_name in ("camera_safe_bounds", "background_coverage_bounds"):
        rect = scene[rect_name]
        if rect["right"] <= rect["left"] or rect["bottom"] <= rect["top"]:
            errors.append(f"{rect_name} must have positive width and height")
    for item in [*scene["layers"], *scene["objects"]]:
        if item.get("kind") == "group":
            continue
        asset_names = [item["asset"]] if item.get("asset") else []
        for name in asset_names:
            path = local(project, name)
            if not path.is_file():
                errors.append("Missing Scene Asset " + name)
                continue
            try:
                with Image.open(path) as image:
                    if image.width < 1 or image.height < 1:
                        errors.append("Invalid image dimensions " + name)
                    if item in scene["layers"] and item.get("fit") == "canvas" and image.size != (scene["reference_size"]["width"], scene["reference_size"]["height"]):
                        errors.append("Canvas size mismatch for Scene Asset " + name)
            except Exception as exc:
                errors.append(f"Invalid image {name}: {exc}")
    for character_id, manifest in asset_by_id.items():
        capability = cap_by_id.get(character_id, {})
        parts = manifest["parts"]
        if not set(capability.get("parts", [])) <= set(parts):
            errors.append(f"Character Asset Manifest misses capability parts for {character_id}")
        for part_name, part in parts.items():
            for state, path_name in {"base": part["asset"], **part["state_assets"]}.items():
                path = local(project, path_name)
                if not path.is_file():
                    errors.append(f"Missing Character Part Asset {character_id}/{part_name}/{state}: {path_name}")
                    continue
                try:
                    with Image.open(path) as image:
                        if image.size != (part["pixel_size"]["width"], part["pixel_size"]["height"]):
                            errors.append(f"Character part pixel_size mismatch {character_id}/{part_name}/{state}")
                except Exception as exc:
                    errors.append(f"Invalid image {path_name}: {exc}")
            if part_name in ("eyes", "mouth"):
                if part_name == "eyes" and "blink" not in part["state_assets"]:
                    if "blink" in capability.get("poses", []):
                        errors.append(f"Blink capability is missing state mapping {character_id}")
                if part_name == "mouth" and not {"open", "closed"} <= set(part["state_assets"]):
                    errors.append(f"Mouth part needs open/closed states {character_id}")
        available_states = {state for part in parts.values() for state in part["state_assets"]}
        for expression in capability.get("expressions", []):
            if f"expression:{expression}" not in available_states:
                errors.append(f"Capability expression has no Character Asset mapping {character_id}/{expression}")
        for pose in capability.get("poses", []):
            if f"pose:{pose}" not in available_states:
                errors.append(f"Capability pose has no Character Asset mapping {character_id}/{pose}")
        for anchor_name, anchor in manifest["anchors"].items():
            anchor_position = anchor if isinstance(anchor, list) else anchor["position"]
            if any(not 0 <= value <= 1 for value in anchor_position):
                errors.append(f"Anchor outside normalized range {character_id}/{anchor_name}")
            if isinstance(anchor, dict) and "bounds" in anchor and not (anchor["bounds"]["right"] > anchor["bounds"]["left"] and anchor["bounds"]["bottom"] > anchor["bounds"]["top"]):
                errors.append(f"Invalid Character Anchor bounds {character_id}/{anchor_name}")
        if manifest["anchors"]["root"] != manifest["root_anchor"]:
            errors.append(f"Character root_anchor and anchors.root must match {character_id}")
    return errors

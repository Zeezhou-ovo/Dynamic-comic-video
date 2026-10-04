"""Copy a comic project to a new FPS while preserving time in seconds.
Run pipeline validate/preview on the result: cached reviews are invalidated.
"""
import argparse
import json
import shutil
from pathlib import Path


def retime(value, ratio):
    if isinstance(value, list):
        return [retime(item, ratio) for item in value]
    if isinstance(value, dict):
        return {key: max(0, int(number * ratio + .5))
                if isinstance(number, int) and not isinstance(number, bool) and
                (key == 'frame' or key.endswith('_frame') or key.endswith('_frames'))
                else retime(number, ratio) for key, number in value.items()}
    return value


def convert(source, destination, fps):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination == source or source in destination.parents:
        raise ValueError('Destination must be separate from source project')
    if (source / 'director_plan.json').exists() or (source / 'production_profile.json').exists():
        raise ValueError('Retime the authoritative director/template timeline before changing FPS; this helper supports direct four-contract projects only')
    brief = json.loads((source / 'production_brief.json').read_text())
    old = brief['format']['fps']
    if fps not in (24,25,30,60):
        raise ValueError('Unsupported FPS')
    shutil.copytree(source, destination)
    for name in ('production_brief.json','storyboard.json','motion_plan.json'):
        path = destination / name
        data = retime(json.loads(path.read_text()), fps / old)
        if name == 'production_brief.json':
            data['format']['fps'] = fps
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    # Round each shot duration then recompute starts to avoid gaps at cuts.
    path = destination / 'motion_plan.json'
    motion = json.loads(path.read_text()); start = 0
    for shot in motion['shots']:
        shot['start_frame'] = start
        start += shot['duration_frames']
        shot['performance']['reviewed'] = False
    path.write_text(json.dumps(motion,ensure_ascii=False,indent=2)+'\n')
    path = destination / 'production_brief.json'
    brief = json.loads(path.read_text()); brief['format']['duration_frames'] = start
    path.write_text(json.dumps(brief,ensure_ascii=False,indent=2)+'\n')
    review = destination / 'visual_review.json'
    if review.exists():
        data = json.loads(review.read_text()); data['review_status'] = 'pending'
        data['review_notes'] = 'FPS changed; old media and reviews are historical. Render and review again.'
        for frame in data.get('frames',[]): frame['reviewed'] = False
        review.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return {'old_fps':old,'fps':fps,'duration_frames':start}

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('destination'); parser.add_argument('--fps',type=int,required=True)
    args=parser.parse_args()
    print(json.dumps(convert(args.source,args.destination,args.fps)))

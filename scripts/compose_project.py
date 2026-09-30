"""Create a project from authored content + Mode + Template; no asset path assembly."""
import argparse
from pathlib import Path
from mode_system import read_json,validate_schema
from template_system import instantiate_template,resolve_project_mode
from pipeline import NAMES,read,save,validate


def compose_project(project, script, mode, template, scene=None, overrides=None):
    script=dict(script)
    script['project_id']=Path(project).name
    validate_schema('dialogue_script',script)
    instantiate_template(template,project,mode,scene,overrides)
    project=Path(project).resolve()
    save(project/'dialogue_script.json',script)
    brief=read(project/'production_brief.json');brief['original_content']='\n'.join(b['text'] for b in script['beats'])
    brief['title']=f'{template} · {mode}'
    save(project/'production_brief.json',brief)
    board=read(project/'storyboard.json')
    for beat in board['beats']:beat['source_excerpt']=brief['original_content']
    save(project/'storyboard.json',board)
    data={n:read(project/(n+'.json')) for n in (*NAMES,'scene_manifest','character_assets')}
    save(project/'director_plan.json',resolve_project_mode(project,data))
    _,errors,_=validate(project,assets=True)
    if errors:raise ValueError('\n'.join(errors))
    return project


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('project',type=Path);p.add_argument('--content',type=Path,required=True)
    p.add_argument('--mode',required=True);p.add_argument('--template',required=True)
    p.add_argument('--scene');p.add_argument('--overrides',type=Path)
    a=p.parse_args()
    print(compose_project(a.project,read_json(a.content),a.mode,a.template,a.scene,
                          read_json(a.overrides) if a.overrides else None))

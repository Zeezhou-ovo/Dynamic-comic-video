"""One authored dialogue, switchable Mode and Template; prepare through pipeline."""
import argparse
from pathlib import Path
from pipeline import read,save
from mode_system import plan_metrics


def build(project, mode='dialogue-comedy', template='generic-room'):
    script={'version':'0.1','project_id':project.name,'beats':[
        {'beat_id':'question','speaker':'lin','text':'为什么冰放在桌上会变成水？','intent':'ask','emphasis':'normal'},
        {'beat_id':'explanation','speaker':'bo','text':'因为它吸收了周围环境的热量。','intent':'explain','emphasis':'normal','reaction':'interested','reaction_target':'lin'},
        {'beat_id':'misunderstanding','speaker':'lin','text':'所以不是桌子把它弄湿了？','intent':'ask','emphasis':'normal'},
        {'beat_id':'punchline','speaker':'bo','text':'……不是。','intent':'confirm','emphasis':'punchline','reaction':'speechless','reaction_target':'bo'}]}
    from compose_project import compose_project
    compose_project(project,script,mode,template)
    plan=read(project/'director_plan.json')
    save(project/'director_plan.json',plan);save(project/'mode_metrics.json',plan_metrics(plan))
    return project


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    p.add_argument('--mode',default='dialogue-comedy');p.add_argument('--template',default='generic-room')
    a=p.parse_args();print(build(a.project.resolve(),a.mode,a.template))

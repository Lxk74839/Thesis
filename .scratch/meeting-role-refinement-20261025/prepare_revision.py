"""Prepare a sibling revision of the group meeting assets, preserving prior deliverables."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(r'D:\Work\Codex\Project\Thesis')
BUILD=ROOT/'.scratch/meeting-role-refinement-20261025'
OLD=ROOT/'reports/组会汇报_实验结果与提示词模板_20261024'
NEW=ROOT/'reports/组会汇报_角色完善版_20261025'
NEW.mkdir(parents=True,exist_ok=True)
excluded={'配图/用户画像智能体_卡通提示词模板.png','配图/卡通图生成提示词.txt'}
for source in OLD.rglob('*'):
    if not source.is_file():
        continue
    relative=source.relative_to(OLD)
    if relative.as_posix() in excluded:
        continue
    target=NEW/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
roles=[
 '身份定位：你是农产品推荐系统中的用户偏好分析员。',
 '工作目标：形成有依据、可复用的结构化偏好画像。',
 '核心职责：辨别喜好与抱怨，区分偏好与偶然提及，筛选属性并赋权。',
 '协作关系：向农产品画像和推荐管理提供偏好与问题说明。',
 '能力边界：不负责最终排序或生命周期核验，不推断批次质量、产地或认证。',
]
template=NEW/'用户画像智能体提示词模板.txt'
text=template.read_text(encoding='utf-8-sig')
before='角色\n你是农产品推荐系统的用户画像分析员。\n'
assert before in text
text=text.replace(before,'角色\n'+'\n'.join(roles)+'\n',1)
text=text.replace('以上是旧版Compact已用英文提示词的中文展示模板，图中展示同一内容。',
                  '以上根据既有Compact英文提示词与六角色分工整理，补充身份、目标、职责、协作和边界；图中展示同一内容。')
template.write_text(text,encoding='utf-8-sig')
shutil.copyfile(BUILD/'image-edit-prompt.txt',NEW/'配图/卡通图修改提示词.txt')
readme=NEW/'阅读说明.txt'
readme.write_text(readme.read_text(encoding='utf-8-sig')+'\n角色完善版：角色面板已补齐身份定位、工作目标、核心职责、协作关系与能力边界；实验和数据内容沿用已核对版本。\n',encoding='utf-8-sig')
meta={'old':str(OLD),'new':str(NEW),'roles':roles,'old_image_sha256':hashlib.sha256((OLD/'配图/用户画像智能体_卡通提示词模板.png').read_bytes()).hexdigest()}
(BUILD/'revision.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(NEW),'role_dimensions':len(roles)},ensure_ascii=False))

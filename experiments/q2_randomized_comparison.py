"""第二问随机源位置、随机检测候选点、随机误差的独立留出验证。

复现：python experiments/q2_randomized_comparison.py
保留既有标准几何与评价器，输出是探索结果，非官方成绩。
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

import q2_strategy_comparison as geometry


ROOT = Path(__file__).resolve().parents[1]
BASE_SEED = 20260911


def draw_sources(rng, count, distribution):
    u = rng.random(count)
    ranges = np.sqrt(25 + u*(1500**2-25)) if distribution == 'area' else 5+1495*u
    angles = rng.uniform(-geometry.EPS, geometry.EPS, count)
    errors = rng.uniform(-geometry.EPS, geometry.EPS, count)
    return np.column_stack([ranges*np.cos(angles), ranges*np.sin(angles)]), errors


def feasible_mask(poly, points):
    return np.max(np.sum((points[:, None, :]-poly[None, :, :])**2, axis=2),axis=1) <= 1e6+1e-6


def draw_plane(rng, poly, count):
    """在含上下两侧的矩形内均匀抽样，拒绝不可行点，得到面积均匀可行候选。"""
    accepted=[]
    remaining=count
    while remaining:
        points=rng.uniform([499.,-1000.],[1006.,1000.],size=(max(256,3*remaining),2))
        points=points[feasible_mask(poly,points)][:remaining]
        accepted.append(points)
        remaining-=len(points)
    return np.concatenate(accepted)


def draw_boundary(rng, poly, count):
    # 接收边界可能包含最优解；用随机横坐标生成边界候选，无规则搜索网格。
    accepted=[]
    while len(accepted)<count:
        a=float(rng.uniform(499.,1006.))
        b=geometry.safe_b(poly,a)
        if b is not None:
            accepted.append([a,float(b)*rng.choice([-1,1])])
    return np.array(accepted)


def draw_local(rng, poly, centers, count, radius):
    accepted=[]
    remaining=count
    while remaining:
        n=max(128,3*remaining)
        bases=centers[rng.integers(0,len(centers),n)]
        angles=rng.uniform(0,2*math.pi,n)
        distances=radius*np.sqrt(rng.random(n))
        points=bases+np.column_stack([distances*np.cos(angles),distances*np.sin(angles)])
        points=points[feasible_mask(poly,points)][:remaining]
        accepted.append(points)
        remaining-=len(points)
    return np.concatenate(accepted)


def values(poly, point, samples, chunk=1024):
    source,errors=samples
    return np.concatenate([geometry.radii(poly,np.array(point),source[j:j+chunk],errors[j:j+chunk])
                           for j in range(0,len(source),chunk)])


def means(poly, points, samples):
    return np.array([values(poly,point,samples).mean() for point in points])


def paired_result(baseline, candidate, p):
    difference=baseline-candidate
    mean_difference=float(difference.mean())
    se=float(difference.std(ddof=1)/math.sqrt(len(difference)))
    return {'point_m':p.tolist(),'mean_radius_m':float(candidate.mean()),
            'mean_gain_m':mean_difference,'gain_percent':100*mean_difference/float(baseline.mean()),
            'paired_mean_gain_95ci_m':[mean_difference-1.96*se,mean_difference+1.96*se],
            'p95_radius_m':float(np.quantile(candidate,.95)),
            'sample_max_radius_m':float(candidate.max()),
            'radius_le20_fraction':float(np.mean(candidate<=20)),
            'move_seconds':float(np.linalg.norm(p)/5)}


def run_one(distribution, repetition, settings):
    started=time.perf_counter()
    code=0 if distribution=='area' else 1
    seed_sequence=np.random.SeedSequence([BASE_SEED,code,repetition])
    streams=seed_sequence.spawn(3)
    rng_train,rng_candidate,rng_test=[np.random.default_rng(s) for s in streams]
    poly=geometry.initial_polygon()
    first=np.array([750.,float(geometry.safe_b(poly))])
    anchors=np.array([first, first*np.array([1.,-1.])])
    train=draw_sources(rng_train,settings['train_n'],distribution)
    # 测试集在选点结束后才生成和使用。
    interior=draw_plane(rng_candidate,poly,settings['interior_n'])
    boundary=draw_boundary(rng_candidate,poly,settings['boundary_n'])
    pool=np.vstack([anchors,interior,boundary])
    pure_pool=pool[:2+len(interior)]
    screen=(train[0][:settings['screen_n']],train[1][:settings['screen_n']])
    screen_scores=means(poly,pool,screen)
    pure_indices=np.argsort(screen_scores[:len(pure_pool)])[:settings['shortlist_n']]
    all_indices=np.argsort(screen_scores)[:settings['shortlist_n']]
    pure_indices=np.unique(np.r_[0,1,pure_indices])
    all_indices=np.unique(np.r_[0,1,all_indices])
    pure_scores=means(poly,pool[pure_indices],train)
    pure_best=pool[pure_indices[int(np.argmin(pure_scores))]]
    current=pool[all_indices]
    current_scores=means(poly,current,train)
    # 随机局部搜索只围绕训练优胜点，不查看旧网格解或测试集。
    for radius in [80.,20.]:
        centers=current[np.argsort(current_scores)[:3]]
        local=draw_local(rng_candidate,poly,centers,settings['local_n'],radius)
        # 额外随机边界点：横坐标来自局部候选，避免最优解位于边界时抽不到。
        projected=[]
        for a,b in local[::2]:
            upper=geometry.safe_b(poly,a)
            if upper is not None:
                projected.append([float(a),math.copysign(float(upper),b)])
        new=np.vstack([local,np.array(projected).reshape(-1,2)])
        current=np.vstack([current,new])
        current_scores=np.r_[current_scores,means(poly,new,train)]
    best=current[int(np.argmin(current_scores))]
    train_a=float(values(poly,first,train).mean())
    assert min(current_scores)<=train_a+1e-9
    assert feasible_mask(poly,np.array([first,pure_best,best])).all()
    testing=draw_sources(rng_test,settings['test_n'],distribution)
    base=values(poly,first,testing)
    result={'distribution':distribution,'repetition':repetition,
            'seed_entropy':[BASE_SEED,code,repetition],
            'seed_spawn_keys':{'train':list(streams[0].spawn_key),'candidate':list(streams[1].spawn_key),'test':list(streams[2].spawn_key)},
            'train_baseline_mean_m':train_a,'train_random_best_mean_m':float(min(current_scores)),
            'train_gain_percent':100*(train_a-float(min(current_scores)))/train_a,
            'initial_pool_size':len(pool),'refinement_pool_size':len(current),
            'baseline':paired_result(base,base,first),'strategies':{}}
    # 固定旧解只用于独立测试作参照，不加入随机搜索，不引导局部中心。
    fixed=np.array([870.,501.683285691096] if distribution=='area' else [788.,621.933483162453])
    for name,p in [('random_interior',pure_best),('random_refined',best),('previous_grid_reference',fixed)]:
        vals=values(poly,p,testing)
        result['strategies'][name]=paired_result(base,vals,p)
    result['seconds']=time.perf_counter()-started
    return result


def random_checks(poly):
    checks=geometry.checks(poly)
    n=50000
    results={}
    for distribution in ['area','radial']:
        src,e=draw_sources(np.random.default_rng(BASE_SEED),n,distribution)
        src2,e2=draw_sources(np.random.default_rng(BASE_SEED),n,distribution)
        assert np.array_equal(src,src2) and np.array_equal(e,e2)
        r=np.linalg.norm(src,axis=1)
        u=(r*r-25)/(1500**2-25) if distribution=='area' else (r-5)/1495
        cdf_error=float(np.max(abs(np.sort(u)-(np.arange(n)+.5)/n)))
        assert cdf_error<.01
        assert np.all((r>5)&(r<=1500))
        assert np.max(abs(np.arctan2(src[:,1],src[:,0])))<=geometry.EPS
        assert np.max(abs(e))<=geometry.EPS
        results[distribution]={'sample_count':n,'transformed_radius_cdf_max_error':cdf_error,'reproducible':True}
    pts=draw_plane(np.random.default_rng(BASE_SEED+1),poly,2000)
    assert feasible_mask(poly,pts).all()
    # 随机源包含在结果包围圆中；随机二次误差处于容許范围。
    src,e=draw_sources(np.random.default_rng(BASE_SEED+2),40,'area')
    p=pts[0]
    rad,center,_,_=geometry.radii(poly,p,src,e,True)
    assert np.all(np.linalg.norm(src-center,axis=1)<=rad+1e-6)
    checks.update({'random_source_checks':results,'random_candidate_feasibility_checks':len(pts),
                   'random_truth_containment_checks':len(src)})
    return checks


def aggregate(rows, repetitions):
    output={}
    bootstrap=np.random.default_rng(BASE_SEED+999)
    for distribution in ['area','radial']:
        subset=[r for r in rows if r['distribution']==distribution]
        if len(subset)!=repetitions:
            continue
        item={'repetitions':len(subset),'baseline_mean_radius_m':float(np.mean([r['baseline']['mean_radius_m'] for r in subset])),
              'strategies':{}}
        for strategy in ['random_interior','random_refined','previous_grid_reference']:
            stats=[r['strategies'][strategy] for r in subset]
            gain=np.array([s['gain_percent'] for s in stats])
            boot=bootstrap.choice(gain,size=(10000,len(gain)),replace=True).mean(axis=1)
            item['strategies'][strategy]={
                'mean_radius_m':float(np.mean([s['mean_radius_m'] for s in stats])),
                'mean_gain_percent':float(gain.mean()),'run_gain_percent_std':float(gain.std(ddof=1)),
                'run_gain_percent_range':[float(gain.min()),float(gain.max())],
                'mean_gain_bootstrap_95ci_percent':[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))],
                'positive_test_gain_runs':int(np.sum(gain>0)),
                'positive_paired_ci_runs':sum(s['paired_mean_gain_95ci_m'][0]>0 for s in stats),
                'mean_added_move_seconds':float(np.mean([s['move_seconds']-r['baseline']['move_seconds'] for s,r in zip(stats,subset)])),
                'mean_radius_le20_fraction':float(np.mean([s['radius_le20_fraction'] for s in stats])),
                'point_abs_y_mean_m':np.mean([[s['point_m'][0],abs(s['point_m'][1])] for s in stats],axis=0).tolist()}
        item['mean_train_gain_percent']=float(np.mean([r['train_gain_percent'] for r in subset]))
        item['baseline_radius_le20_fraction']=float(np.mean([r['baseline']['radius_le20_fraction'] for r in subset]))
        output[distribution]=item
    return output


def write_report(result, folder):
    settings=result['settings']
    lines=['# 第二问随机抽样验证报告','',
           '状态：合成标准场景的探索性验证，非官方模拟器成绩。', '',
           '首次检测点为原点，首次示向朝东，完整扇形半径1500米、半角1度；源距离大于5米。与前一轮共用连续区域几何外包及最小包围圆评价器。', '',
           f"每种分布独立重复{settings['repetitions']}轮；每轮{settings['train_n']}个随机训练位置及误差、{settings['test_n']}个独立测试位置及误差。第一种方案仍为中垂线最大最小锐交会角，点为(750,635.518174)。", '',
           f"第二种初始候选包括{settings['interior_n']}个平面面积均匀随机点、{settings['boundary_n']}个随机边界点，以及基线及其镜像两个固定锚点。前{settings['screen_n']}个训练样本预筛，优胜候选在全部训练样本上重排，再做两轮随机局部搜索。所有检测候选均满足对完整源可行集合的1000米保守接收约束。", '',
           '纯内部随机对照只使用面积均匀随机候选及两个锚点；随机细化方案另外使用边界及局部随机候选。旧网格选点仅参加最后的留出测试，不加入随机搜索。', '',
           '源位置分别使用面积均匀和径向均匀随机分布。二次测向误差独立从[-1度,1度]均匀抽样；源的第一次真实方位与已知示向的偏差由其在扇形内的角度体现。两种概率分布均是实验假设，不是题目事实。', '',
           '每轮测试在选点完成后才生成；两种方法面对同一批随机源位置及误差，用成对差值降低比较噪声。不同方法共用误差随机数是比较技术，不是声称不同位置的实际误差相同；该试验没有拟合真实空间误差场，也没有在固定位置反复测量并平均掉误差。', '',
           '|位置分布|方案|测试平均半径/米|平均改善|各轮改善范围|平均改善95%自助区间|',
           '|---|---|---:|---:|---|---|']
    labels={'area':'面积均匀','radial':'径向均匀'}
    for distribution,item in result['aggregate'].items():
        lines.append(f"|{labels[distribution]}|中垂线基线|{item['baseline_mean_radius_m']:.5f}|—|—|—|")
        for key,label in [('random_interior','纯内部随机'),('random_refined','随机搜索＋随机细化'),('previous_grid_reference','旧网格点留出参照')]:
            s=item['strategies'][key]
            lo,hi=s['run_gain_percent_range'];cl,ch=s['mean_gain_bootstrap_95ci_percent']
            lines.append(f"|{labels[distribution]}|{label}|{s['mean_radius_m']:.5f}|{s['mean_gain_percent']:.3f}%|{lo:.3f}%—{hi:.3f}%|[{cl:.3f}%, {ch:.3f}%]|")
    lines+=['','区间解释：每轮成对均值差采用正态近似区间；上表采用固定种子10000次按独立轮次重抽样估计平均改善区间。这些区间描述本实验分布与搜索预算下的抽样不确定性，不描述未知官方场景分布，也不是全局最优保证。', '',
            '检查包含源抽样分布、固定种子复现、接收约束、随机真源包含性，以及复用评价器的独立标量几何对照、镜像和圆弧加密检查。', '',
            f"完整运行墙钟耗时：{result['runtime']['seconds']:.2f}秒。源代码哈希、NumPy版本、每轮种子及独立随机流、候选点、训练/测试差异、移动时间和20米阈值样本比例见同目录JSON。", '',
            '复现：`python experiments/q2_randomized_comparison.py`。默认参数随代码保存，也可通过命令行调整重复轮数、训练样本、测试样本与候选数量。', '',
            '本结果仅适用于首次完整扇形的标准几何及当前概率假设；尚未改变第一检测点位置、目标圆域裁剪方式、误差空间相关性或接收约束口径。代码经团队人工核验和采纳后，须晋升至src才能作为正式论文依据。']
    (folder/'randomized_comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repetitions',type=int,default=12)
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--train-n',type=int,default=1024)
    parser.add_argument('--test-n',type=int,default=20000)
    parser.add_argument('--interior-n',type=int,default=384)
    parser.add_argument('--boundary-n',type=int,default=64)
    parser.add_argument('--local-n',type=int,default=48)
    args=parser.parse_args()
    settings=vars(args)|{'screen_n':256,'shortlist_n':16,'base_seed':BASE_SEED}
    assert settings['repetitions']>=2 and settings['train_n']>=settings['screen_n']
    assert settings['test_n']>=1000 and min(settings['workers'],settings['interior_n'],settings['boundary_n'],settings['local_n'])>0
    started=time.perf_counter()
    validation=random_checks(geometry.initial_polygon())
    folder=ROOT/'outputs'/'q2'
    folder.mkdir(parents=True,exist_ok=True)
    result={'status':'进行中','settings':settings,'validation':validation,'runs':[]}
    print('checks passed; randomized jobs',2*settings['repetitions'],flush=True)
    with ProcessPoolExecutor(max_workers=settings['workers']) as executor:
        futures=[executor.submit(run_one,distribution,i,settings)
                 for distribution in ['area','radial'] for i in range(settings['repetitions'])]
        for future in as_completed(futures):
            row=future.result()
            result['runs'].append(row)
            result['runs'].sort(key=lambda r:(r['distribution'],r['repetition']))
            (folder/'randomized_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            refined=row['strategies']['random_refined']
            print(json.dumps({'completed':len(result['runs']),'distribution':row['distribution'],
                              'repetition':row['repetition'],'gain_percent':refined['gain_percent'],
                              'point':refined['point_m'],'seconds':row['seconds']}),flush=True)
    result['status']='已完成探索性随机验证，非官方成绩'
    result['aggregate']=aggregate(result['runs'],settings['repetitions'])
    result['code_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [Path(__file__).resolve(),Path(geometry.__file__).resolve()]}
    result['runtime']={'seconds':time.perf_counter()-started,'python':sys.version,'numpy':np.__version__}
    (folder/'randomized_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    write_report(result,folder)
    print('DONE',json.dumps(result['aggregate'],ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()

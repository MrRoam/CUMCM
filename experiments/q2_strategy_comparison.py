"""第二问两种选点策略的探索性比较；输出不作为正式论文结果。

复现：python experiments/q2_strategy_comparison.py
只用确定性网格，无随机抽样。长度单位米，内部角度单位弧度。
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EPS = math.pi / 180
R = 1500.0


def clip(poly, normal, bound):
    """标量凸多边形半平面裁剪，保留 normal.dot(x)<=bound。"""
    out = []
    for start, end in zip(poly, np.roll(poly, -1, axis=0)):
        fs, fe = np.dot(start, normal) - bound, np.dot(end, normal) - bound
        if (fs <= 0) != (fe <= 0):
            out.append(start + fs / (fs - fe) * (end - start))
        if fe <= 0:
            out.append(end)
    return np.array(out)


def initial_polygon(arc_steps=16):
    # 1500米圆弧采用切线外包；内侧5米圆弧用端点弦外包。
    # 该区域包含真实P1；最大圆弧外包偏差 R*(sec(EPS/arc_steps)-1)。
    poly = np.array([[5*math.cos(EPS), -5*math.sin(EPS)],
                     [R*1.001, -R*1.001*math.tan(EPS)],
                     [R*1.001, R*1.001*math.tan(EPS)],
                     [5*math.cos(EPS), 5*math.sin(EPS)]])
    for angle in np.linspace(-EPS, EPS, arc_steps+1):
        poly = clip(poly, np.array([math.cos(angle), math.sin(angle)]), R)
    return poly


def batch_clip(points, counts, normals, bounds):
    n, cap, _ = points.shape
    ii = np.arange(n)[:, None]
    jj = np.arange(cap)[None, :]
    nxt = (jj + 1) % counts[:, None]
    ends = points[ii, nxt]
    fs = np.einsum('nvi,ni->nv', points, normals) - bounds[:, None]
    fe = np.einsum('nvi,ni->nv', ends, normals) - bounds[:, None]
    valid = jj < counts[:, None]
    crossing = valid & ((fs <= 0) != (fe <= 0))
    keep_end = valid & (fe <= 0)
    additions = crossing.astype(int) + keep_end.astype(int)
    offsets = np.cumsum(additions, axis=1) - additions
    out = np.zeros((n, cap+1, 2))
    rows, cols = np.where(crossing)
    frac = fs[rows, cols] / (fs[rows, cols]-fe[rows, cols])
    out[rows, offsets[rows, cols]] = points[rows, cols] + frac[:, None]*(ends[rows, cols]-points[rows, cols])
    rows, cols = np.where(keep_end)
    out[rows, offsets[rows, cols]+crossing[rows, cols]] = ends[rows, cols]
    new_counts = additions.sum(axis=1)
    assert np.all(new_counts >= 1), '非空观测被错误裁为空集'
    # 删除无用尾列以降低后续直径矩阵规模。
    return out[:, :int(new_counts.max())], new_counts


def brute_circle(poly):
    """独立的候选圆枚举：单点、两点直径圆、三点外接圆。"""
    best = (float('inf'), None)
    candidates = [(p, 0.0) for p in poly]
    for a, b in itertools.combinations(poly, 2):
        c = (a+b)/2
        candidates.append((c, float(np.sum((a-c)**2))))
    for a, b, c in itertools.combinations(poly, 3):
        matrix = 2*np.array([b-a, c-a])
        if abs(np.linalg.det(matrix)) < 1e-12:
            continue
        center = np.linalg.solve(matrix, np.array([np.dot(b,b)-np.dot(a,a), np.dot(c,c)-np.dot(a,a)]))
        candidates.append((center, float(np.sum((a-center)**2))))
    for center, r2 in candidates:
        if r2 < best[0] and np.all(np.sum((poly-center)**2, axis=1) <= r2+1e-6):
            best = (r2, center)
    assert best[1] is not None
    return math.sqrt(best[0]), best[1]


def radii(poly, s, source, errors, return_polys=False):
    delta = source - s
    angles = np.arctan2(delta[:, 1], delta[:, 0]) + errors
    points = np.broadcast_to(poly, (len(angles), len(poly), 2)).copy()
    counts = np.full(len(angles), len(poly))
    for a, sign in [(angles-EPS, 1), (angles+EPS, -1)]:
        normals = sign*np.column_stack([np.sin(a), -np.cos(a)])
        points, counts = batch_clip(points, counts, normals, normals @ s + 1e-9)
    valid = np.arange(points.shape[1])[None, :] < counts[:, None]
    dif = points[:, :, None, :] - points[:, None, :, :]
    dist2 = np.einsum('nvwi,nvwi->nvw', dif, dif)
    dist2 = np.where(valid[:, :, None] & valid[:, None, :], dist2, -1)
    k = points.shape[1]
    pair = dist2.reshape(len(angles), -1).argmax(axis=1)
    rows = np.arange(len(angles))
    centers = (points[rows, pair//k]+points[rows, pair % k])/2
    rad2 = dist2[rows, pair//k, pair % k]/4
    far2 = np.sum((points-centers[:, None, :])**2, axis=2)
    bad = np.any(valid & (far2 > rad2[:, None]+1e-7), axis=1)
    result = np.sqrt(np.maximum(0, rad2))
    for j in np.flatnonzero(bad):
        result[j], centers[j] = brute_circle(points[j, :counts[j]])
    near = np.linalg.norm(delta, axis=1) <= 5
    # near反馈给出5米圆，足够直接清除；搜索中仍以5米作保守半径计分。
    result[near] = 5.0
    if return_polys:
        return result, centers, points, counts
    return result


def source_grid(nr, na, ne, distribution='area', zero_error=False, endpoints=False):
    if endpoints:
        u = np.linspace(0, 1, nr)
        angles = np.linspace(-EPS, EPS, na)
        errors = np.array([0.0]) if zero_error else np.linspace(-EPS, EPS, ne)
    else:
        u = (np.arange(nr)+0.5)/nr
        angles = -EPS+2*EPS*(np.arange(na)+0.5)/na
        errors = np.array([0.0]) if zero_error else -EPS+2*EPS*(np.arange(ne)+0.5)/ne
    ranges = np.sqrt(25+u*(R*R-25)) if distribution=='area' else 5+u*(R-5)
    rr, aa, ee = np.meshgrid(ranges, angles, errors, indexing='ij')
    src = np.column_stack([rr.ravel()*np.cos(aa.ravel()), rr.ravel()*np.sin(aa.ravel())])
    return src, ee.ravel()


def feasible(poly, s):
    # 使用相同的保守接收条件，不把失联案例从平均值中删去。
    return np.max(np.linalg.norm(poly-s, axis=1)) <= 1000+1e-8


def safe_b(poly, a=750.0):
    dx = poly[:, 0]-a
    if np.any(abs(dx)>1000):
        return None
    lower = np.max(poly[:, 1]-np.sqrt(1e6-dx*dx))
    upper = np.min(poly[:, 1]+np.sqrt(1e6-dx*dx))
    return upper if upper >= max(0, lower) else None


def score(poly, point, samples):
    return float(np.mean(radii(poly, np.array(point), *samples)))


def optimize(poly, samples, first_point):
    # 两级穷举加局部细化；把方案一点显式收入方案二，保证训练分数不更差。
    best = (score(poly, first_point, samples), first_point)
    evaluated = 1
    t0 = time.perf_counter()
    for a in np.arange(0, 1501, 25):
        bm = safe_b(poly, a)
        if bm is None:
            continue
        for b in list(np.arange(0, bm+1e-9, 25))+[bm]:
            p = (float(a), float(b))
            val = score(poly, p, samples)
            evaluated += 1
            if val < best[0]:
                best = (val, p)
    for step, span in [(5, 30), (1, 6)]:
        a0, b0 = best[1]
        for a in np.arange(a0-span, a0+span+step/2, step):
            bm = safe_b(poly, a)
            if bm is None:
                continue
            for b in list(np.arange(max(0,b0-span), min(bm,b0+span)+step/2, step))+[bm]:
                p = (float(a), float(b))
                if not feasible(poly, p):
                    continue
                val = score(poly, p, samples)
                evaluated += 1
                if val < best[0]:
                    best = (val, p)
    bmax = safe_b(poly)
    line_best = (float('inf'), None)
    for b in list(np.arange(0, bmax, 2))+[bmax]:
        p = (750., float(b))
        val = score(poly, p, samples)
        if val < line_best[0]:
            line_best = val, p
    return {'full':best, 'line_mean':line_best, 'evaluations':evaluated,
            'search_seconds':time.perf_counter()-t0}


def summary(poly, p, samples):
    t0 = time.perf_counter()
    # 分块控制长验证网格内存。
    src, errors = samples
    values = np.concatenate([radii(poly, np.array(p), src[j:j+2048], errors[j:j+2048])
                             for j in range(0, len(src), 2048)])
    return {'point':list(p), 'mean_radius_m':float(np.mean(values)),
            'p95_radius_m':float(np.quantile(values, .95)),
            'sample_max_radius_m':float(np.max(values)),
            'radius_le20_fraction':float(np.mean(values<=20)),
            'move_distance_m':math.hypot(*p), 'move_seconds':math.hypot(*p)/5,
            'guaranteed_receive_max_distance_m':float(np.max(np.linalg.norm(poly-p, axis=1))),
            'eval_seconds':time.perf_counter()-t0, 'sample_count':len(values)}


def checks(poly):
    # 固定、不共用裁剪过程的圆几何特例。
    for vertices, expected in [([[0,0],[2,0],[1,math.sqrt(3)]],2/math.sqrt(3)),
                               ([[0,0],[4,0],[4,2],[0,2]],math.sqrt(5)),
                               ([[0,0],[1,0],[3,0]],1.5)]:
        got, _ = brute_circle(np.array(vertices,dtype=float))
        assert abs(got-expected)<1e-9
    src, err = source_grid(6, 3, 3, endpoints=True)
    s = np.array([800., 400.])
    result, centers, polygons, counts = radii(poly, s, src, err, True)
    max_circle_delta = 0.0
    for j in range(len(src)):
        angle = math.atan2(*(src[j]-s)[::-1])+err[j]
        independent = poly.copy()
        for a, sign in [(angle-EPS,1),(angle+EPS,-1)]:
            normal = sign*np.array([math.sin(a),-math.cos(a)])
            independent = clip(independent, normal, float(normal@s)+1e-9)
        r, c = brute_circle(independent)
        max_circle_delta = max(max_circle_delta, abs(result[j]-r))
        assert abs(result[j]-r)<1e-6
        assert np.linalg.norm(src[j]-centers[j]) <= result[j]+1e-6
    # 镜像对称性以及加密圆弧的数值稳定性。
    mirrored = radii(poly, np.array([800.,-400.]), src*np.array([1,-1]), -err)
    assert np.max(abs(mirrored-result))<1e-7
    fine = radii(initial_polygon(64), s, src, err)
    assert np.max(abs(fine-result))<0.01
    return {'circle_special_cases':3, 'scalar_clip_crosschecks':len(src),
            'max_circle_difference_m':max_circle_delta,
            'mirror_max_difference_m':float(np.max(abs(mirrored-result))),
            'arc_refinement_max_difference_m':float(np.max(abs(fine-result))),
            'truth_containment':'通过', 'randomness':'无；全部确定性网格'}


def main():
    started = time.perf_counter()
    poly = initial_polygon()
    check = checks(poly)
    print('checks',json.dumps(check,ensure_ascii=False),flush=True)
    # 对完整窄扇形，中垂线向外移动增加最小锐交会角；取接收边界。
    first = (750., safe_b(poly))
    out = {'status':'探索性合成算例，非官方模拟器成绩，非全局最优证明',
           'geometry':{'S1':[0,0],'theta1_deg':0,'sector_radius_m':1500,
                       'inner_radius_m':5,'angle_error_deg':1,'target_radius_m':1800,
                       'receive_rule':'max distance to outer polygon <=1000',
                       'arc_steps':16,'arc_outer_error_bound_m':R*(1/math.cos(EPS/16)-1),
                       'inner_convexification_error_m':5*(1-math.cos(EPS))},
           'validation':check, 'runs':[]}
    for distribution, zero_error in [('area',False),('radial',False),('area',True)]:
        print('search',distribution,'zero_error',zero_error,flush=True)
        training = source_grid(24,3,3,distribution,zero_error)
        opt = optimize(poly, training, first)
        testing = source_grid(160,9,9,distribution,zero_error)
        row = {'distribution':distribution,'zero_error':zero_error,'optimization':opt,
               'training_samples':len(training[0]),'strategies':{}}
        for name, p in [('A_angle_bisector',first),('A_line_mean',opt['line_mean'][1]),('B_plane_mean',opt['full'][1])]:
            row['strategies'][name] = summary(poly,p,testing)
        boundary = source_grid(151,7,7,'radial',False,True)
        for name, item in row['strategies'].items():
            item['boundary_grid_max_radius_m'] = summary(poly,item['point'],boundary)['sample_max_radius_m']
        out['runs'].append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    # 第一套方案使用更密集训练网格做局部重优化，排查粗采样假优势。
    p0 = out['runs'][0]['strategies']['B_plane_mean']['point']
    dense = source_grid(64,5,5,'area',False)
    best = (score(poly,p0,dense),p0)
    for a in np.arange(p0[0]-10,p0[0]+10.1,2):
        for b in np.arange(p0[1]-10,p0[1]+10.1,2):
            if feasible(poly,(a,b)):
                val = score(poly,(a,b),dense)
                if val<best[0]:
                    best = val,[float(a),float(b)]
    out['dense_local_recheck']={'best':best,'original_on_dense':score(poly,p0,dense),
                                 'training_samples':len(dense[0])}
    # 独立加密评价网格，不使用训练点的平均值冒充泛化表现。
    out['fine_evaluation'] = []
    for row in out['runs'][:2]:
        fine_grid = source_grid(320,17,17,row['distribution'],False)
        fine_result = {'distribution':row['distribution'],'strategies':{}}
        for name in ['A_angle_bisector','B_plane_mean']:
            p = row['strategies'][name]['point']
            fine_result['strategies'][name] = summary(poly,p,fine_grid)
        out['fine_evaluation'].append(fine_result)
        print('fine',json.dumps(fine_result,ensure_ascii=False),flush=True)
    # 第一种方案的最小交会角：在中垂线上用401个位置作确定性核对。
    angle_sources, _ = source_grid(301,31,1,'radial',True,True)
    angle_scores=[]
    for b in np.linspace(0, first[1], 401):
        delta=angle_sources-np.array([750.,b])
        sine=abs(angle_sources[:,0]*delta[:,1]-angle_sources[:,1]*delta[:,0])
        sine/=np.linalg.norm(angle_sources,axis=1)*np.linalg.norm(delta,axis=1)
        angle_scores.append(float(np.degrees(np.arcsin(np.clip(sine,0,1))).min()))
    assert int(np.argmax(angle_scores))==400
    out['angle_baseline_check']={'line_points':401,'source_points':len(angle_sources),
                                 'best_b_m':first[1],'min_angle_deg':angle_scores[-1]}
    out['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out['runtime']={'python':sys.version,'numpy':np.__version__,
                    'seconds':time.perf_counter()-started}
    folder=ROOT/'outputs'/'q2'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'strategy_comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('finished',out['runtime'],'dense',out['dense_local_recheck'],flush=True)


if __name__=='__main__':
    main()

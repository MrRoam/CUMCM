"""方法 A：精确有理系数谓词 + 极角排序 + 真双端队列。

三角函数先由标准库计算，之后对所得有理近似精确计算；不声称
消除了三角函数对理想角度的舍入误差。O(n log n) 指算术操作次数，
不把任意精度整数的位运算成本视为常数。无第三方依赖。
"""

from collections import deque
from dataclasses import dataclass
from fractions import Fraction as F
from functools import cmp_to_key
import math

Point = tuple[F, F]


def rational(value) -> F:
    """拒绝非有限数、布尔值；十进制字符串不先转为浮点数。"""
    if isinstance(value, bool):
        raise ValueError("布尔值不是坐标或角度")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("数值必须有限")
    return F(str(value)) if isinstance(value, float) else F(value)


@dataclass(frozen=True)
class HalfPlane:
    """整数系数 ax+by<=c，法向量指向禁止侧。"""

    a: int
    b: int
    c: int
    label: str = ""

    def __post_init__(self):
        values = [rational(v) for v in (self.a, self.b, self.c)]
        den = math.lcm(*(v.denominator for v in values))
        ints = [int(v * den) for v in values]
        g = math.gcd(*ints)
        if not ints[0] and not ints[1]:
            raise ValueError("半平面法向量不能为零")
        for key, value in zip(("a", "b", "c"), ints):
            object.__setattr__(self, key, value // g)

    @property
    def direction(self):
        return -self.b, self.a  # 沿该方向行进时允许侧在左边。

    def slack(self, p: Point):
        return self.c - self.a * p[0] - self.b * p[1]


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def intersection(a: HalfPlane, b: HalfPlane) -> Point | None:
    det = a.a * b.b - b.a * a.b
    if not det:
        return None
    return F(a.c * b.b - b.c * a.b, det), F(a.a * b.c - b.a * a.c, det)


def _half(d):
    return 0 if d[1] > 0 or (d[1] == 0 and d[0] >= 0) else 1


def _compare(a, b):
    da, db = a.direction, b.direction
    if _half(da) != _half(db):
        return _half(da) - _half(db)
    turn = cross(da, db)
    return -1 if turn > 0 else (1 if turn < 0 else 0)


def _sorted_unique(planes):
    result = []
    for h in sorted(planes, key=cmp_to_key(_compare)):
        if result and _compare(result[-1], h) == 0:
            prev = result[-1]
            # 同向时用 L1 法向长度归一化比较；只做整数乘法。
            if h.c * (abs(prev.a) + abs(prev.b)) < prev.c * (abs(h.a) + abs(h.b)):
                result[-1] = h
        else:
            result.append(h)
    return result


@dataclass
class Region:
    status: str  # polygon / segment / point / empty / unbounded
    vertices: list[Point]
    edge_labels: list[str]
    stats: dict


def halfplane_intersection(planes: list[HalfPlane]) -> Region:
    """不枚举所有直线对。辅助框具有整数系数界证明，见配套文档。

    unbounded 不返回框裁剪顶点，避免调用者把人工边界当成真实边界。
    """
    if not planes:
        return Region("unbounded", [], [], {"input_halfplanes": 0, "intersections": 0})
    # 清分母后的整数系数绝对值<=M，任意有限顶点坐标<=2M²。
    magnitude = max(1, *(abs(v) for p in planes for v in (p.a, p.b, p.c)))
    bound = 2 * magnitude * magnitude + 1
    box = [HalfPlane(1, 0, bound, "aux:right"), HalfPlane(0, 1, bound, "aux:top"),
           HalfPlane(-1, 0, bound, "aux:left"), HalfPlane(0, -1, bound, "aux:bottom")]
    ordered = _sorted_unique([*planes, *box])
    stats = {"input_halfplanes": len(planes), "sorted_halfplanes": len(ordered),
             "intersections": 0, "pushes": 0, "pops": 0,
             "aux_bound_bits": bound.bit_length()}
    q = deque()

    def meet(a, b):
        stats["intersections"] += 1
        return intersection(a, b)

    def empty():
        return Region("empty", [], [], stats)

    for h in ordered:
        while len(q) >= 2:
            p = meet(q[-2], q[-1])
            if p is None:
                return empty()
            if h.slack(p) >= 0:
                break
            q.pop()
            stats["pops"] += 1
        while len(q) >= 2:
            p = meet(q[0], q[1])
            if p is None:
                return empty()
            if h.slack(p) >= 0:
                break
            q.popleft()
            stats["pops"] += 1
        if q and cross(q[-1].direction, h.direction) == 0:
            # 已去重同向约束且加入四向框；此时反向相邻说明不可行。
            return empty()
        q.append(h)
        stats["pushes"] += 1
    while len(q) >= 3:
        p = meet(q[-2], q[-1])
        if p is None:
            return empty()
        if q[0].slack(p) >= 0:
            break
        q.pop()
        stats["pops"] += 1
    while len(q) >= 3:
        p = meet(q[0], q[1])
        if p is None:
            return empty()
        if q[-1].slack(p) >= 0:
            break
        q.popleft()
        stats["pops"] += 1
    if len(q) < 3:
        return empty()
    active = list(q)
    vertices, labels = [], []
    for i, h in enumerate(active):
        p = meet(active[i - 1], h)
        if p is None:
            return empty()
        # 相同顶点的后一个约束才对应下一条非零长度边。
        if vertices and p == vertices[-1]:
            labels[-1] = h.label
        else:
            vertices.append(p)
            labels.append(h.label)
    if len(vertices) > 1 and vertices[0] == vertices[-1]:
        vertices.pop()
        labels.pop()
    if any(abs(x) == bound or abs(y) == bound for x, y in vertices):
        return Region("unbounded", [], [], stats)
    area2 = sum(cross(vertices[i], vertices[(i + 1) % len(vertices)]) for i in range(len(vertices)))
    if area2 == 0:
        lo, hi = min(vertices), max(vertices)
        return Region("point" if lo == hi else "segment", [lo] if lo == hi else [lo, hi], [], stats)
    if area2 < 0:
        raise ArithmeticError("内部错误：边界没有按逆时针排列")
    return Region("polygon", vertices, labels, stats)


def _unit(deg: F):
    deg %= 360
    if deg.denominator == 1 and deg.numerator % 90 == 0:
        return [(F(1), F(0)), (F(0), F(1)), (F(-1), F(0)), (F(0), F(-1))][int(deg) // 90]
    rad = math.radians(float(deg))
    return F.from_float(math.cos(rad)), F.from_float(math.sin(rad))


def bearing_halfplanes(observations: list[dict]) -> list[HalfPlane]:
    """每条观测含 x、y、bearing_deg；固定采用题面的 ±1°。"""
    if not observations:
        raise ValueError("至少需要一个检测点；未闭合的观测将返回 unbounded")
    planes = []
    for i, obs in enumerate(observations):
        x, y, theta = (rational(obs[k]) for k in ("x", "y", "bearing_deg"))
        if not 0 <= theta < 360:
            raise ValueError("bearing_deg 必须位于 [0,360)")
        low, high = _unit(theta - 1), _unit(theta + 1)
        for side, a, b in [("lower", low[1], -low[0]), ("upper", -high[1], high[0])]:
            planes.append(HalfPlane(a, b, a * x + b * y, f"observation:{i}:{side}"))
    return planes


def distance2(a, b):
    dx, dy = sub(a, b)
    return dx * dx + dy * dy


def diameter(vertices: list[Point]):
    """对逆时针凸多边形用旋转卡壳，返回 D²、端点索引、推进次数。"""
    n = len(vertices)
    if not n:
        raise ValueError("空集没有本程序定义的直径")
    if n <= 2:
        return distance2(vertices[0], vertices[-1]), (0, n - 1), 0
    best, pair, steps = F(-1), (0, 0), 0
    j = 1
    for i in range(n):
        nxt = (i + 1) % n
        edge = sub(vertices[nxt], vertices[i])

        def height(index):
            return cross(edge, sub(vertices[index % n], vertices[i]))

        while height(j + 1) > height(j):
            j += 1
            steps += 1
            if steps > 2 * n:
                raise ArithmeticError("卡壳推进异常：输入需为逆时针凸边界")
        opposite = [j % n]
        if height(j + 1) == height(j):
            opposite.append((j + 1) % n)
        for a in (i, nxt):
            for b in opposite:
                value = distance2(vertices[a], vertices[b])
                if value > best:
                    best, pair = value, (a, b)
    return best, pair, steps


def analyze(planes: list[HalfPlane]) -> dict:
    region = halfplane_intersection(planes)

    def encoded(p):
        return {"xy_m": [float(v) for v in p], "xy_rational": [str(v) for v in p]}

    result = {"status": region.status, "vertices": [encoded(p) for p in region.vertices],
              "edge_labels": region.edge_labels, "stats": region.stats,
              "diameter_m": None, "diameter_squared_m2_exact": None,
              "diameter_circle_covers": None}
    if region.status in ("empty", "unbounded"):
        result["diameter_note"] = "空集不定义直径" if region.status == "empty" else "无界区域直径为无穷大，无有限覆盖圆"
        return result
    d2, pair, steps = diameter(region.vertices)
    a, b = (region.vertices[i] for i in pair)
    center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    excess = [distance2(p, center) - d2 / 4 for p in region.vertices]
    worst = max(range(len(excess)), key=excess.__getitem__)
    result.update(diameter_m=math.sqrt(float(d2)), diameter_squared_m2_exact=str(d2),
                  diameter_pair_indices=list(pair), circle_center=encoded(center),
                  circle_radius_m=math.sqrt(float(d2)) / 2,
                  diameter_circle_covers=excess[worst] <= 0,
                  max_circle_excess_m2_exact=str(excess[worst]),
                  outside_vertex_index=worst if excess[worst] > 0 else None)
    result["stats"]["caliper_advances"] = steps
    return result

import pandas as pd
from sklearn.neighbors import NearestNeighbors
from django.db.models import Q
from userauths.models import User
from hardware.models import Product, SearchHistory, OrderItem, cartOrderItem

# ---------- text helpers ----------
def _tokens(text):
    return {w.lower().strip() for w in str(text or '').split()}

def _similarity(p1, p2):
    a = _tokens(p1.name) | _tokens(p1.description)
    b = _tokens(p2.name) | _tokens(p2.description)
    return len(a & b) / (len(a | b) or 1)

# ---------- collaborative KNN ----------
def build_user_item_matrix():
    interactions = {}
    for uid, pid in SearchHistory.objects.filter(
        user__isnull=False, product__isnull=False
    ).values_list('user_id', 'product_id'):
        interactions[(uid, pid)] = interactions.get((uid, pid), 0) + 1

    name2pid = {p.name: p.pid for p in Product.objects.all()}
    for uid, item_name in OrderItem.objects.filter(
        order__user__isnull=False
    ).values_list('order__user_id', 'item'):
        pid = name2pid.get(item_name)
        if pid:
            interactions[(uid, pid)] = interactions.get((uid, pid), 0) + 1

    if not interactions:
        return pd.DataFrame(index=pd.Index([], dtype='int64'),
                            columns=pd.Index([], dtype='object'))

    df = pd.DataFrame([(u, p, c) for (u, p), c in interactions.items()],
                      columns=['user_id', 'product_id', 'score'])
    return df.pivot(index='user_id', columns='product_id',
                    values='score').fillna(0).astype(float)


def knn_recommend(user_id, matrix, k_neighbors=3, top_n=8):
    if matrix.empty or user_id not in matrix.index:
        return []

    k_neighbors = min(k_neighbors, len(matrix) - 1)
    if k_neighbors < 1:
        popular = matrix.sum(axis=0).sort_values(ascending=False).head(top_n)
        return popular.index.tolist()

    model = NearestNeighbors(metric='cosine', algorithm='brute')
    model.fit(matrix.values)
    user_vec = matrix.loc[[user_id]].values
    distances, indices = model.kneighbors(user_vec,
                                          n_neighbors=k_neighbors + 1)
    neighbours = indices[0][1:]
    neighbour_scores = matrix.iloc[neighbours].sum(axis=0)
    already_interacted = matrix.loc[user_id]
    neighbour_scores = neighbour_scores[already_interacted == 0]
    return neighbour_scores.sort_values(ascending=False).head(top_n).index.tolist()

# ---------- seed extractor ----------
def _user_seeds(user):
    seed_pids = set(
        SearchHistory.objects.filter(
            user=user, product__isnull=False
        ).values_list('product_id', flat=True)
    )

    # raw query → best product match
    for sh in SearchHistory.objects.filter(user=user, product__isnull=True):
        matched = Product.objects.filter(name__icontains=sh.query).first()
        if matched:
            seed_pids.add(matched.pid)

    # cart items
    seed_pids.update(
        cartOrderItem.objects.filter(
            user=user, order__order_status='processing'
        ).values_list('item__pid', flat=True)
    )
    return Product.objects.filter(pid__in=seed_pids)

# ---------- hybrid recommender ----------
def recommend_for_user(user, top_n=8):
    if not user.is_authenticated:
        return Product.objects.none()

    # products to exclude (already in cart)
    exclude_pids = set(
        cartOrderItem.objects.filter(
            user=user, order__order_status='processing'
        ).values_list('item__pid', flat=True)
    )

    # 1) KNN list
    matrix = build_user_item_matrix()
    knn_ids = knn_recommend(user.id, matrix, k_neighbors=3, top_n=top_n * 2)

    # 2) seed list
    seeds = _user_seeds(user)

    # 3) candidate pool
    if knn_ids:
        candidates = Product.objects.filter(pid__in=knn_ids).exclude(pid__in=exclude_pids)
    else:
        candidates = Product.objects.exclude(pid__in=exclude_pids)

    # 4) score each candidate against all seeds
    scored = []
    for prod in candidates:
        sim = max(_similarity(seed, prod) for seed in seeds) if seeds.exists() else 0.0
        scored.append((sim, prod))

    scored.sort(key=lambda t: (-t[0], t[1].pid))
    recommended = [p for _, p in scored][:top_n]

    # 5) pad if still short
    if len(recommended) < top_n:
        extra = top_n - len(recommended)
        extra_qs = Product.objects.exclude(
            pid__in=exclude_pids | {p.pid for p in recommended}
        ).order_by('-created_at')[:extra]
        recommended.extend(extra_qs)

    return recommended

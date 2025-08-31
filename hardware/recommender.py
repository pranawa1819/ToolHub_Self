import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from django.db.models import Q
from userauths.models import User
from hardware.models import Product, SearchHistory, OrderItem, cartOrderItem
from sklearn.metrics.pairwise import cosine_similarity



# text helpers 
def _tokens(text):
    return {w.lower().strip() for w in str(text or '').split() if w}


def _similarity(p1, p2):
    a = _tokens(p1.name) | _tokens(p1.description)
    b = _tokens(p2.name) | _tokens(p2.description)
    denom = len(a | b) or 1
    return len(a & b) / denom


def _query_match(query, product):
    """ fuzzy token overlap between query and product """
    q_tokens = _tokens(query)
    p_tokens = _tokens(product.name) | _tokens(product.description)
    denom = len(q_tokens | p_tokens) or 1
    return len(q_tokens & p_tokens) / denom


# collaborative KNN 
def build_user_item_matrix():
    interactions = {}

    # from search history
    for uid, pid in SearchHistory.objects.filter(
        user__isnull=False, product__isnull=False
    ).values_list('user_id', 'product_id'):
        interactions[(uid, pid)] = interactions.get((uid, pid), 0) + 1

    # cache product names → pid
    name2pid = {p.name.lower(): p.pid for p in Product.objects.all()}

    # from orders (OrderItem.item is a CharField)
    for uid, item_name in OrderItem.objects.filter(
        order__user__isnull=False
    ).values_list('order__user_id', 'item'):
        pid = name2pid.get(str(item_name).lower().strip())
        if pid:
            interactions[(uid, pid)] = interactions.get((uid, pid), 0) + 2  # weighted

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
    distances, indices = model.kneighbors(user_vec, n_neighbors=k_neighbors + 1)

    neighbours = indices[0][1:]
    neighbour_distances = distances[0][1:]

    # weighted neighbour scores
    neighbour_matrix = matrix.iloc[neighbours]
    weights = 1 - neighbour_distances
    weighted_scores = np.dot(weights, neighbour_matrix.values)

    scores = pd.Series(weighted_scores, index=matrix.columns)
    already_interacted = matrix.loc[user_id]
    scores = scores[already_interacted == 0]

    return scores.sort_values(ascending=False).head(top_n).index.tolist()


# seed extractor (fuzzy query handling)
def _user_seeds(user):
    seed_pids = set(
        SearchHistory.objects.filter(
            user=user, product__isnull=False
        ).values_list('product_id', flat=True)
    )

    # handle queries without direct product
    for sh in SearchHistory.objects.filter(user=user, product__isnull=True):
        candidates = Product.objects.all()
        best_match = max(candidates, key=lambda p: _query_match(sh.query, p), default=None)
        best_match and seed_pids.add(best_match.pid)

    # include cart items
    seed_pids.update(
        cartOrderItem.objects.filter(
            user=user, order__order_status='processing'
        ).values_list('item__pid', flat=True)
    )
    return Product.objects.filter(pid__in=seed_pids)


# hybrid recommender 
def recommend_for_user(user, top_n=8):
    if not user.is_authenticated:
        return Product.objects.none()
    
    exclude_pids = set(
        cartOrderItem.objects.filter(
            user=user, order__order_status='processing'
        ).values_list('item__pid', flat=True)
    )
    
    matrix = build_user_item_matrix()
    knn_ids = knn_recommend(user.id, matrix, k_neighbors=3, top_n=top_n * 2)  
    seeds = _user_seeds(user)
    
    candidates = Product.objects.filter(pid__in=knn_ids).exclude(pid__in=exclude_pids) if knn_ids else Product.objects.exclude(pid__in=exclude_pids)

    scored = []
    for prod in candidates:
        sim_values = [_similarity(seed, prod) for seed in seeds]
        sim = max(sim_values, default=0.0)
        scored.append((sim, prod))

    scored.sort(key=lambda t: (-t[0], t[1].pid))
    recommended = [p for _, p in scored][:top_n]
    
    if len(recommended) < top_n:
        extra = top_n - len(recommended)
        extra_qs = Product.objects.exclude(
            pid__in=exclude_pids | {p.pid for p in recommended}
        ).order_by('-created_at')[:extra]
        recommended.extend(extra_qs)
        
    return recommended


def knn_similar_products(product, top_n=4):
    """
    Recommend products similar to the given product using both
    collaborative KNN and content similarity.
    """
    matrix = build_user_item_matrix()
    candidates = Product.objects.exclude(pid=product.pid)

    # --- collaborative score list ---
    knn_ids, collab_scores = [], {}
    if not matrix.empty and product.pid in matrix.columns:
        model = NearestNeighbors(metric='cosine', algorithm='brute')
        model.fit(matrix.T.values)

        prod_index = list(matrix.columns).index(product.pid)
        n_samples = matrix.T.shape[0]
        n_neighbors = min(top_n + 1, n_samples)

        distances, indices = model.kneighbors(
            [matrix.T.values[prod_index]], n_neighbors=n_neighbors
        )

        # build {pid: score} dict (score = 1 - cosine_distance)
        for idx, d in zip(indices[0][1:], distances[0][1:]):
            pid = matrix.columns[idx]
            collab_scores[pid] = 1.0 - d
        knn_ids = list(collab_scores.keys())

    # --- content similarity fallback ---
    def _tokens(text):
        return {w.lower().strip() for w in str(text or '').split()}

    def _sim_content(p1, p2):
        a = _tokens(p1.name) | _tokens(p1.description)
        b = _tokens(p2.name) | _tokens(p2.description)
        return len(a & b) / (len(a | b) or 1)

    # final weighted score: collaborative if exists, else content
    scored = []
    for p in candidates:
        if p.pid in collab_scores:
            score = collab_scores[p.pid]          # collaborative takes precedence
        else:
            score = _sim_content(product, p)      # pure content fallback
        scored.append((score, p))

    # highest score first
    scored.sort(key=lambda x: (-x[0], x[1].pid))
    return [p for _, p in scored[:top_n]]



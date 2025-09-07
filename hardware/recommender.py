import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from userauths.models import User
from hardware.models import (
    Product, SearchHistory, OrderItem, cartOrderItem,
    ProductView
)

# ------------------------------
# Globals to hold trained model
# ------------------------------
_knn_model = None
_feature_matrix = None
_product_ids = None
_vectorizer = None


# ------------------------------
# TRAINING STEP
# ------------------------------
def train_model(k_neighbors=3):
    """
    Build TF-IDF feature matrix for all products and train a KNN model.
    Falls back to popular products if k_neighbors < 1.
    """
    global _knn_model, _feature_matrix, _product_ids, _vectorizer

    products = Product.objects.all()
    if not products.exists():
        print("No products found for training.")
        return None

    # fallback for very small datasets
    if k_neighbors < 1:
        print("k_neighbors < 1, falling back to popular products only.")
        popular_products = products.order_by('-popularity')[:8]  # assuming 'popularity' field exists
        _product_ids = [p.pid for p in popular_products]
        _feature_matrix = None
        _knn_model = None
        return _product_ids

    docs, pids = [], []
    for p in products:
        text = f"{p.name} {p.description} {p.specification} {p.label} {p.category_id}"
        docs.append(text)
        pids.append(p.pid)

    _vectorizer = TfidfVectorizer(stop_words='english')
    _feature_matrix = _vectorizer.fit_transform(docs)
    _product_ids = pids

    _knn_model = NearestNeighbors(metric='cosine', algorithm='brute')
    _knn_model.fit(_feature_matrix)

    print(f"KNN model trained successfully on {len(products)} products.")
    return _knn_model



# ------------------------------
# USER SEEDS (history, cart, orders, views) with weights
# ------------------------------
def _user_seeds(user):
    seeds = []
    # From search history (weight 1.0)
    for sh in SearchHistory.objects.filter(user=user):
        if sh.product:  # product search
            seeds.append((sh.product.pid, 1.0))
        elif sh.query:  # text-based search → find similar products
            # Vectorize query and find nearest neighbors
            if _knn_model is None or _feature_matrix is None:
                train_model()
            query_vec = _vectorizer.transform([sh.query])
            distances, indices = _knn_model.kneighbors(query_vec, n_neighbors=5)
            for i, d in zip(indices[0], distances[0]):
                pid = _product_ids[i]
                seeds.append((pid, 0.8 * (1 - d)))  # smaller weight than exact product
                
    # Active cart (weight 2.0)
    for pid in cartOrderItem.objects.filter(
        user=user, order__order_status="processing"
    ).values_list('item__pid', flat=True):
        seeds.append((pid, 2.0))
        
    # Completed orders (weight 2.0)
    for pid in cartOrderItem.objects.filter(
        user=user, order__order_status="completed"
    ).values_list('item__pid', flat=True):
        
        seeds.append((pid, 2.0))
    # Recently viewed (weight 1.5)
    for pid in ProductView.objects.filter(user=user).values_list('product__pid', flat=True):
        seeds.append((pid, 1.5))
    # Remove duplicates, keep max weight per product
    seed_dict = {}
    for pid, w in seeds:
        if pid in seed_dict:
            seed_dict[pid] = max(seed_dict[pid], w)
        else:
            seed_dict[pid] = w
    # Return list of tuples (Product, weight)
    seed_list = []
    for pid, weight in seed_dict.items():
        try:
            product = Product.objects.get(pid=pid)
            seed_list.append((product, weight))
        except Product.DoesNotExist:
            continue
    return seed_list






# ------------------------------
# Similar product recommender
# ------------------------------
def knn_similar_products(product, top_n=4):
    global _knn_model, _feature_matrix, _product_ids, _vectorizer

    if _knn_model is None or _feature_matrix is None:
        train_model()

    if product.pid not in _product_ids:
        return Product.objects.none()

    idx = _product_ids.index(product.pid)
    query_vec = _feature_matrix[idx]

    distances, indices = _knn_model.kneighbors(query_vec, n_neighbors=top_n + 1)
    similar_indices = indices[0][1:]
    similar_pids = [_product_ids[i] for i in similar_indices]

    return Product.objects.filter(pid__in=similar_pids)


# ------------------------------
# Hybrid recommender for user with weighted seeds
# ------------------------------
def recommend_for_user(user, top_n=8):
    if not user.is_authenticated:
        # Guest user fallback
        return Product.objects.all().order_by("-created_at")[:top_n]

    # Exclude items already in cart
    exclude_pids = set(
        cartOrderItem.objects.filter(user=user, order__order_status='processing')
        .values_list('item__pid', flat=True)
    )
    # Collect seeds (Product, weight)
    seed_products = _user_seeds(user)
    if not seed_products:
        # Fallback for cold-start users
        return Product.objects.exclude(pid__in=exclude_pids).order_by("-created_at")[:top_n]

    if _knn_model is None or _feature_matrix is None:
        train_model()
    scored = []
    for seed, weight in seed_products:
        if seed.pid not in _product_ids:
            continue
        idx = _product_ids.index(seed.pid)
        query_vec = _feature_matrix[idx]

        distances, indices = _knn_model.kneighbors(query_vec, n_neighbors=top_n + 1)
        for i, d in zip(indices[0][1:], distances[0][1:]):
            pid = _product_ids[i]
            if pid not in exclude_pids:
                # Multiply similarity by seed weight
                scored.append((weight * (1 - d), pid))
    # Rank by weighted similarity
    scored.sort(key=lambda x: -x[0])
    top_pids = [pid for _, pid in scored[:top_n]]
    # Convert queryset to list
    recommended = list(Product.objects.filter(pid__in=top_pids))
    
    
    if len(recommended) < top_n:
        extra = top_n - len(recommended)
        extra_qs = Product.objects.exclude(
            pid__in=exclude_pids | {p.pid for p in recommended}
        ).order_by('-created_at')[:extra]
        recommended.extend(extra_qs)

    return recommended

import pandas as pd
import numpy as np
import os
import uuid
import json
from typing import Dict, Any, Callable

# Clustering
from sklearn.cluster import KMeans, DBSCAN, MeanShift
import hdbscan
from sklearn.metrics import silhouette_score, davies_bouldin_score

# Classification / Regression
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from xgboost import XGBClassifier, XGBRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    mean_squared_error, mean_absolute_error, r2_score
)

def run_clustering_task(
    dataset_id: int,
    file_path: str,
    config: Dict[str, Any],
    project_id: int,
    update_progress: Callable[[float, str], None]
) -> Dict[str, Any]:
    update_progress(10.0, "正在加载数据...")
    df = pd.read_parquet(file_path)
    
    features = config.get("features", [])
    if not features:
        raise ValueError("未选择聚类特征")
        
    missing_cols = [c for c in features if c not in df.columns]
    if missing_cols:
        raise ValueError(f"列不存在: {', '.join(missing_cols)}")
        
    X = df[features].dropna()
    if len(X) < 10:
        raise ValueError("有效数据量太少，无法聚类")
        
    algo = config.get("algorithm", "kmeans")
    update_progress(40.0, f"正在训练 {algo} 模型...")
    
    model = None
    labels = None
    
    if algo == "kmeans":
        n_clusters = config.get("n_clusters", 0) # 0 means auto-K
        if n_clusters <= 1:
            # Auto-K using Silhouette Score
            best_k = 2
            best_score = -1
            max_k = min(10, len(X) - 1)
            for k in range(2, max_k + 1):
                temp_model = KMeans(n_clusters=k, random_state=42)
                temp_labels = temp_model.fit_predict(X)
                score = silhouette_score(X, temp_labels)
                if score > best_score:
                    best_score = score
                    best_k = k
            n_clusters = best_k
            
        model = KMeans(n_clusters=n_clusters, random_state=42)
        labels = model.fit_predict(X)
        
    elif algo == "dbscan":
        eps = config.get("eps", 0.5)
        min_samples = config.get("min_samples", 5)
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(X)
        
    elif algo == "hdbscan":
        min_cluster_size = config.get("min_cluster_size", 5)
        model = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
        labels = model.fit_predict(X)
        
    elif algo == "meanshift":
        model = MeanShift()
        labels = model.fit_predict(X)
        
    else:
        raise ValueError(f"不支持的聚类算法: {algo}")
        
    update_progress(80.0, "计算聚类指标...")
    
    # Evaluate if more than 1 cluster and not all noise
    unique_labels = np.unique(labels)
    valid_labels = [l for l in unique_labels if l != -1]
    
    metrics = {}
    if len(valid_labels) > 1:
        metrics["silhouette_score"] = float(silhouette_score(X, labels))
        metrics["davies_bouldin_score"] = float(davies_bouldin_score(X, labels))
    else:
        metrics["silhouette_score"] = None
        metrics["davies_bouldin_score"] = None
        
    metrics["n_clusters"] = len(valid_labels)
    metrics["noise_points"] = int(np.sum(labels == -1))
    
    update_progress(90.0, "保存结果...")
    # Add labels back to original df (aligning indices)
    df.loc[X.index, f"cluster_{algo}"] = labels
    df.to_parquet(file_path)
    
    update_progress(100.0, "聚类完成")
    return {
        "message": "聚类完成",
        "algorithm": algo,
        "metrics": metrics
    }

def run_predictive_modeling_task(
    dataset_id: int,
    file_path: str,
    config: Dict[str, Any],
    project_id: int,
    update_progress: Callable[[float, str], None]
) -> Dict[str, Any]:
    update_progress(10.0, "正在加载数据...")
    df = pd.read_parquet(file_path)
    
    target = config.get("target")
    features = config.get("features", [])
    task_type = config.get("task_type", "classification") # classification or regression
    algo = config.get("algorithm", "rf") # rf, xgb, lgbm, mlp
    
    if not target or not features:
        raise ValueError("目标列或特征列未选择")
        
    cols = features + [target]
    missing_cols = [c for c in cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"列不存在: {', '.join(missing_cols)}")
        
    df_clean = df[cols].dropna()
    if len(df_clean) < 10:
        raise ValueError("有效数据量太少，无法建模")
        
    X = df_clean[features]
    y = df_clean[target]
    
    # Basic encoding for target if classification
    is_multiclass = False
    if task_type == "classification":
        y = y.astype(str)
        unique_classes = y.nunique()
        is_multiclass = unique_classes > 2
        
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    update_progress(40.0, f"正在训练 {algo} 模型...")
    
    model = None
    if task_type == "classification":
        if algo == "rf":
            model = RandomForestClassifier(random_state=42)
        elif algo == "xgb":
            # XGBoost needs numeric labels
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            y_train = le.fit_transform(y_train)
            y_test = le.transform(y_test)
            model = XGBClassifier(random_state=42, use_label_encoder=False, eval_metric="logloss")
        elif algo == "lgbm":
            model = LGBMClassifier(random_state=42)
        elif algo == "mlp":
            model = MLPClassifier(random_state=42, max_iter=500)
        else:
            raise ValueError(f"不支持的算法: {algo}")
    else: # regression
        if algo == "rf":
            model = RandomForestRegressor(random_state=42)
        elif algo == "xgb":
            model = XGBRegressor(random_state=42)
        elif algo == "lgbm":
            model = LGBMRegressor(random_state=42)
        elif algo == "mlp":
            model = MLPRegressor(random_state=42, max_iter=500)
        else:
            raise ValueError(f"不支持的算法: {algo}")
            
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    update_progress(80.0, "计算模型指标...")
    metrics = {}
    if task_type == "classification":
        metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
        
        # for multiclass, use weighted
        avg_method = "weighted" if is_multiclass else "binary"
        try:
            metrics["precision"] = float(precision_score(y_test, y_pred, average=avg_method))
            metrics["recall"] = float(recall_score(y_test, y_pred, average=avg_method))
            metrics["f1"] = float(f1_score(y_test, y_pred, average=avg_method))
        except:
            pass
            
        if not is_multiclass and hasattr(model, "predict_proba"):
            try:
                y_prob = model.predict_proba(X_test)[:, 1]
                metrics["auc"] = float(roc_auc_score(y_test, y_prob))
            except:
                pass
    else:
        metrics["mse"] = float(mean_squared_error(y_test, y_pred))
        metrics["mae"] = float(mean_absolute_error(y_test, y_pred))
        metrics["r2"] = float(r2_score(y_test, y_pred))
        
    update_progress(90.0, "保存结果...")
    
    feature_importance = None
    if hasattr(model, "feature_importances_"):
        fi = model.feature_importances_
        feature_importance = [{"feature": f, "importance": float(imp)} for f, imp in zip(features, fi)]
        feature_importance.sort(key=lambda x: x["importance"], reverse=True)
        
    update_progress(100.0, "建模完成")
    return {
        "message": "建模完成",
        "algorithm": algo,
        "task_type": task_type,
        "metrics": metrics,
        "feature_importance": feature_importance
    }

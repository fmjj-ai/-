import hashlib
import json
import os
import logging
import re
import uuid
from typing import Any, Callable, Dict, Optional

import jieba
import numpy as np
import pandas as pd
import pyLDAvis
import pyLDAvis.lda_model
from openai import OpenAI
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from snownlp import SnowNLP
from wordcloud import WordCloud

logger = logging.getLogger(__name__)


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_int(value: Any, default: int, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _normalize_float(value: Any, default: float, minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _clean_token(token: str) -> str:
    token = str(token or "").strip()
    token = re.sub(r"\s+", "", token)
    return token


def _tokenize_text(text: str, stopwords: set[str]) -> list[str]:
    words = jieba.lcut(text)
    cleaned_tokens = []
    punctuation_chars = "，。！？；：、（）()[]{}<>《》【】“”‘’\"'.,!?;:-_/\\|@#$%^&*+=~`"
    for word in words:
        cleaned = _clean_token(word)
        if not cleaned:
            continue
        if cleaned in stopwords:
            continue
        if len(cleaned) == 1 and not cleaned.isalnum():
            continue
        if all(ch in punctuation_chars for ch in cleaned):
            continue
        cleaned_tokens.append(cleaned)
    return cleaned_tokens


def _build_effective_corpus(tokens_list: list[list[str]]) -> list[str]:
    return [" ".join(tokens) for tokens in tokens_list if tokens]


def _build_word_pattern() -> str:
    return r"(?u)\b\w+\b"


def _resolve_wordcloud_font_path(config: Dict[str, Any]) -> Optional[str]:
    candidate_paths: list[str] = []

    explicit_font_path = config.get("wc_font_path") or config.get("font_path")
    if explicit_font_path:
        candidate_paths.append(str(explicit_font_path))

    font_name = str(config.get("wc_font") or "").strip()
    if os.name == "nt":
        windows_font_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        windows_font_map = {
            "SimHei": ["simhei.ttf", "simhei.ttc"],
            "SimSun": ["simsun.ttc", "simsun.ttf"],
            "Microsoft YaHei": ["msyh.ttc", "msyh.ttf", "msyhbd.ttc"],
        }
        for file_name in windows_font_map.get(font_name, []):
            candidate_paths.append(os.path.join(windows_font_dir, file_name))
        if font_name and os.path.isabs(font_name):
            candidate_paths.append(font_name)
        candidate_paths.extend([
            os.path.join(windows_font_dir, "msyh.ttc"),
            os.path.join(windows_font_dir, "simhei.ttf"),
            os.path.join(windows_font_dir, "simsun.ttc"),
        ])
    else:
        if font_name and os.path.isabs(font_name):
            candidate_paths.append(font_name)
        candidate_paths.extend([
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
        ])

    for path in candidate_paths:
        if path and os.path.exists(path):
            return path

    logger.warning("No available CJK font found for wordcloud; Chinese rendering may fail")
    return None




def build_sentiment_signature(dataset_fingerprint: str, config: Dict[str, Any]) -> str:
    normalized_stopwords = sorted({_clean_token(word) for word in config.get("stopwords", []) if _clean_token(word)})
    signature_payload = {
        "dataset_fingerprint": dataset_fingerprint,
        "text_column": str(config.get("text_column", "content") or "content").strip(),
        "method": str(config.get("method", "snownlp") or "snownlp").strip().lower(),
        "stopwords": normalized_stopwords,
        "extract_tfidf": _normalize_bool(config.get("extract_tfidf", True), True),
        "top_k": _normalize_int(config.get("top_k", 20), 20, minimum=1),
        "generate_wordcloud": _normalize_bool(config.get("generate_wordcloud", True), True),
        "run_lda": _normalize_bool(config.get("run_lda", False), False),
        "lda_k": _normalize_int(config.get("lda_k", config.get("lda_n_topics", 5)), 5, minimum=2, maximum=50),
        "lda_min_k": _normalize_int(config.get("lda_min_k", 2), 2, minimum=2, maximum=50),
        "lda_max_k": _normalize_int(config.get("lda_max_k", 10), 10, minimum=3, maximum=50),
        "generate_lda_vis": _normalize_bool(config.get("generate_lda_vis", False), False),
        "wc_colormap": str(config.get("wc_colormap", "viridis") or "viridis"),
        "wc_font": str(config.get("wc_font", "") or ""),
        "wc_contour": _normalize_bool(config.get("wc_contour", False), False),
        "base_url": str(config.get("base_url", "") or "").strip(),
        "model_name": str(config.get("model_name", "") or "").strip(),
        "api_key_present": bool(str(config.get("api_key", "") or "").strip()),
    }
    payload = json.dumps(signature_payload, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def run_sentiment_task(
    dataset_id: int,
    file_path: str,
    config: Dict[str, Any],
    project_id: int,
    update_progress: Callable[[float, str], None],
) -> Dict[str, Any]:
    dataset_fingerprint = hashlib.md5()
    with open(file_path, "rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            dataset_fingerprint.update(chunk)
    dataset_fingerprint_hex = dataset_fingerprint.hexdigest()
    signature = build_sentiment_signature(dataset_fingerprint_hex, config)
    text_column = config.get("text_column", "content")
    method = str(config.get("method", "snownlp")).strip().lower()
    stopwords = {_clean_token(word) for word in config.get("stopwords", []) if _clean_token(word)}
    extract_tfidf = _normalize_bool(config.get("extract_tfidf", True), True)
    top_k = _normalize_int(config.get("top_k", 20), 20, minimum=1)
    generate_wordcloud = _normalize_bool(config.get("generate_wordcloud", True), True)

    run_lda = _normalize_bool(config.get("run_lda", False), False)
    lda_n_topics = _normalize_int(config.get("lda_k", config.get("lda_n_topics", 5)), 5, minimum=2, maximum=50)
    lda_min_k = _normalize_int(config.get("lda_min_k", 2), 2, minimum=2, maximum=50)
    lda_max_k = _normalize_int(config.get("lda_max_k", max(lda_min_k + 1, lda_n_topics)), max(lda_min_k + 1, lda_n_topics), minimum=lda_min_k + 1, maximum=50)
    lda_top_words = _normalize_int(config.get("lda_top_words", 10), 10, minimum=3, maximum=30)
    lda_max_features = _normalize_int(config.get("lda_max_features", 1000), 1000, minimum=50, maximum=5000)
    lda_max_iter = _normalize_int(config.get("lda_max_iter", 10), 10, minimum=5, maximum=100)
    lda_learning_method = str(config.get("lda_learning_method", "batch") or "batch").strip().lower()
    if lda_learning_method not in {"batch", "online"}:
        lda_learning_method = "batch"
    lda_min_df_raw = config.get("lda_min_df", 1)
    lda_min_df = _normalize_float(lda_min_df_raw, 1.0, minimum=0.0)
    if isinstance(lda_min_df_raw, str) and "." in lda_min_df_raw:
        lda_min_df = _normalize_float(lda_min_df_raw, 0.01, minimum=0.0, maximum=1.0)
    elif lda_min_df >= 1:
        lda_min_df = int(lda_min_df)
    lda_max_df = _normalize_float(config.get("lda_max_df", 0.95), 0.95, minimum=0.1, maximum=1.0)
    evaluate_lda_candidates = _normalize_bool(config.get("evaluate_lda_candidates", True), True)
    generate_lda_vis = _normalize_bool(config.get("generate_lda_vis", False), False)

    api_key = str(config.get("api_key", "") or "").strip()
    base_url = str(config.get("base_url", "https://api.deepseek.com/v1") or "https://api.deepseek.com/v1").strip()
    model_name = str(config.get("model_name", "deepseek-chat") or "deepseek-chat").strip()

    update_progress(10.0, "正在加载数据...")
    df = pd.read_parquet(file_path)

    if text_column not in df.columns:
        raise ValueError(f"列 {text_column} 不存在")

    df[text_column] = df[text_column].fillna("").astype(str)
    total_rows = len(df)
    if total_rows == 0:
        raise ValueError("数据为空")

    update_progress(20.0, "开始分词...")
    tokens_list: list[list[str]] = []
    for i, text in enumerate(df[text_column]):
        if i % max(1, total_rows // 10) == 0:
            update_progress(20.0 + (10.0 * i / total_rows), f"分词进度 {i}/{total_rows}")
        tokens_list.append(_tokenize_text(text, stopwords))

    df["tokens"] = [" ".join(words) for words in tokens_list]
    corpus = df["tokens"].tolist()
    effective_corpus = _build_effective_corpus(tokens_list)

    if method == "snownlp":
        update_progress(30.0, "开始 SnowNLP 情感打分...")
        sentiment_scores = []
        sentiment_labels = []
        for i, text in enumerate(df[text_column]):
            if i % max(1, total_rows // 10) == 0:
                update_progress(30.0 + (30.0 * i / total_rows), f"打分进度 {i}/{total_rows}")
            if not text.strip():
                sentiment_scores.append(0.5)
                sentiment_labels.append("中")
                continue
            try:
                score = float(SnowNLP(text).sentiments)
                score = max(0.0, min(1.0, score))
                sentiment_scores.append(score)
                if score > 0.6:
                    sentiment_labels.append("正")
                elif score < 0.4:
                    sentiment_labels.append("负")
                else:
                    sentiment_labels.append("中")
            except Exception as exc:
                logger.warning("SnowNLP sentiment failed at row %s: %s", i, exc)
                sentiment_scores.append(0.5)
                sentiment_labels.append("中")
        df["sentiment_score"] = sentiment_scores
        df["sentiment_label"] = sentiment_labels
    elif method == "deepseek":
        update_progress(30.0, "开始 DeepSeek API 情感打分...")
        if not api_key:
            raise ValueError("DeepSeek 分析需要提供 API Key")
        client = OpenAI(api_key=api_key, base_url=base_url)
        sentiment_scores = []
        sentiment_labels = []
        for i, text in enumerate(df[text_column]):
            if i % max(1, total_rows // 10) == 0:
                update_progress(30.0 + (30.0 * i / total_rows), f"API 请求进度 {i}/{total_rows}")
            if not text.strip():
                sentiment_scores.append(0.5)
                sentiment_labels.append("中")
                continue
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "你是一个情感分析助手。请对用户的文本进行情感打分，返回一个0到1之间的小数，表示情感倾向（0表示极度负面，1表示极度正面，0.5表示中性）。只返回数字，不要返回其他任何内容。"},
                        {"role": "user", "content": text[:1000]},
                    ],
                    temperature=0.0,
                )
                score = float((response.choices[0].message.content or "").strip())
                score = max(0.0, min(1.0, score))
                sentiment_scores.append(score)
                if score > 0.6:
                    sentiment_labels.append("正")
                elif score < 0.4:
                    sentiment_labels.append("负")
                else:
                    sentiment_labels.append("中")
            except Exception as exc:
                logger.warning("DeepSeek sentiment failed at row %s: %s", i, exc)
                sentiment_scores.append(0.5)
                sentiment_labels.append("中")
        df["sentiment_score"] = sentiment_scores
        df["sentiment_label"] = sentiment_labels
    else:
        raise ValueError(f"暂不支持的方法: {method}")

    update_progress(60.0, "保存分析结果...")
    df.to_parquet(file_path)

    artifacts = []
    artifacts_dir = f"storage/projects/{project_id}/artifacts/charts"
    os.makedirs(artifacts_dir, exist_ok=True)

    tfidf_result = None
    if extract_tfidf and effective_corpus:
        update_progress(65.0, "计算 TF-IDF 关键词...")
        vectorizer = TfidfVectorizer(max_features=top_k, token_pattern=_build_word_pattern())
        try:
            tfidf_matrix = vectorizer.fit_transform(effective_corpus)
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            word_scores = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
            tfidf_result = [{"word": w, "score": float(s)} for w, s in word_scores[:top_k]]
        except ValueError as exc:
            logger.warning("TF-IDF generation skipped: %s", exc)
    elif extract_tfidf:
        logger.warning("TF-IDF generation skipped: no effective tokens after tokenization")

    lda_result = None
    if run_lda:
        update_progress(70.0, "正在运行 LDA 主题模型分析...")
        try:
            if len(effective_corpus) < 2:
                raise ValueError("可用于 LDA 的有效文本不足，至少需要 2 条非空文本")

            tf_vectorizer = CountVectorizer(
                max_df=lda_max_df,
                min_df=lda_min_df,
                max_features=lda_max_features,
                token_pattern=_build_word_pattern(),
            )
            tf = tf_vectorizer.fit_transform(effective_corpus)
            feature_names = tf_vectorizer.get_feature_names_out()
            if tf.shape[0] < 2 or tf.shape[1] < 2:
                raise ValueError("有效词项不足，无法执行 LDA")

            effective_topic_count = min(lda_n_topics, tf.shape[0], tf.shape[1])
            if effective_topic_count < 2:
                raise ValueError("可用语料或词项不足，无法形成至少 2 个主题")
            if effective_topic_count != lda_n_topics:
                logger.warning("LDA topic count adjusted from %s to %s due to corpus limits", lda_n_topics, effective_topic_count)

            lda_model = LatentDirichletAllocation(
                n_components=effective_topic_count,
                max_iter=lda_max_iter,
                learning_method=lda_learning_method,
                random_state=42,
                evaluate_every=-1,
            )
            lda_model.fit(tf)

            topics = []
            for topic_idx, topic in enumerate(lda_model.components_):
                top_features_ind = topic.argsort()[:-lda_top_words - 1:-1]
                top_features = [feature_names[i] for i in top_features_ind]
                topics.append({"topic": int(topic_idx), "keywords": top_features})

            lda_result = {
                "topics": topics,
                "n_topics": int(effective_topic_count),
                "feature_count": int(len(feature_names)),
                "perplexity": float(lda_model.perplexity(tf)),
                "candidates": None,
                "vis_path": None,
            }

            if evaluate_lda_candidates:
                candidates = []
                for candidate_k in range(min(lda_min_k, lda_max_k), max(lda_min_k, lda_max_k) + 1):
                    if candidate_k < 2 or candidate_k > tf.shape[0] or candidate_k > tf.shape[1]:
                        continue
                    candidate_model = LatentDirichletAllocation(
                        n_components=candidate_k,
                        max_iter=min(lda_max_iter, 8),
                        learning_method=lda_learning_method,
                        random_state=42,
                        evaluate_every=-1,
                    )
                    candidate_model.fit(tf)
                    candidates.append({"k": int(candidate_k), "perplexity": float(candidate_model.perplexity(tf))})
                lda_result["candidates"] = candidates or None

            if generate_lda_vis:
                panel = pyLDAvis.lda_model.prepare(lda_model, tf, tf_vectorizer, mds="tsne")
                lda_html_id = str(uuid.uuid4())
                lda_html_path = os.path.join(artifacts_dir, f"lda_vis_{lda_html_id}.html")
                pyLDAvis.save_html(panel, lda_html_path)
                artifacts.append({
                    "name": f"LDA_可视化_{lda_html_id}.html",
                    "type": "html",
                    "file_path": lda_html_path,
                    "size": os.path.getsize(lda_html_path),
                })
                lda_result["vis_path"] = lda_html_path
        except Exception as exc:
            logger.warning("LDA generation skipped: %s", exc)
            lda_result = None

    if generate_wordcloud and tfidf_result:
        update_progress(90.0, "生成词云图...")
        font_path = _resolve_wordcloud_font_path(config)
        mask = None
        mask_path = config.get("mask_path")
        if mask_path and os.path.exists(mask_path):
            try:
                from PIL import Image
                mask = np.array(Image.open(mask_path))
            except Exception as exc:
                logger.warning("Failed to load wordcloud mask %s: %s", mask_path, exc)
                mask = None
        try:
            wc_kwargs: Dict[str, Any] = {
                "width": 800,
                "height": 600,
                "background_color": "white",
                "max_words": 100,
                "colormap": config.get("wc_colormap") or "viridis",
                "mask": mask,
                "contour_width": 3 if (mask is not None and _normalize_bool(config.get("wc_contour", False), False)) else 0,
                "contour_color": "steelblue" if (mask is not None and _normalize_bool(config.get("wc_contour", False), False)) else None,
            }
            if font_path:
                wc_kwargs["font_path"] = font_path
            wc = WordCloud(**wc_kwargs).generate_from_frequencies({item["word"]: item["score"] for item in tfidf_result})
            wc_id = str(uuid.uuid4())
            wc_path = os.path.join(artifacts_dir, f"wordcloud_{wc_id}.png")
            wc.to_file(wc_path)
            artifacts.append({
                "name": f"词云图_{wc_id}",
                "type": "png",
                "file_path": wc_path,
                "size": os.path.getsize(wc_path),
            })
        except Exception as exc:
            logger.warning("Wordcloud generation skipped: %s", exc)

    update_progress(100.0, "情感分析完成")
    return {
        "message": "情感分析完成",
        "signature": signature,
        "dataset_fingerprint": dataset_fingerprint_hex,
        "dataset_id": dataset_id,
        "row_count": total_rows,
        "text_column": text_column,
        "artifacts": artifacts,
        "sentiment_summary": pd.Series(df["sentiment_label"]).value_counts().to_dict() if "sentiment_label" in df else {},
        "tfidf": tfidf_result,
        "lda": lda_result,
    }

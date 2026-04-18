import hashlib
import json
import logging
import os
import re
import tempfile
import uuid
from collections import Counter
from pathlib import Path
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
from snownlp import sentiment as snownlp_sentiment
from wordcloud import WordCloud

logger = logging.getLogger(__name__)

DEFAULT_SNOW_MODEL_PATH = getattr(snownlp_sentiment, "data_path", "")
DEFAULT_POSITIVE_THRESHOLD = 0.9
DEFAULT_NEGATIVE_THRESHOLD = 0.1
DEFAULT_SENTIMENT_POSITIVE = 0.6
DEFAULT_SENTIMENT_NEGATIVE = 0.4
WORDCLOUD_SCOPE_LABELS = {
    "overall": "整体",
    "positive": "正向",
    "negative": "负向",
}


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


def _sanitize_file_part(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", str(value or "").strip())
    return cleaned or "数据集"


def _normalize_wordcloud_scopes(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple, set)):
        candidates = list(value)
    else:
        candidates = ["overall"]

    normalized: list[str] = []
    for raw in candidates:
        scope = str(raw or "").strip().lower()
        if scope in WORDCLOUD_SCOPE_LABELS and scope not in normalized:
            normalized.append(scope)
    return normalized or ["overall"]


def _build_word_pattern() -> str:
    return r"(?u)\b\w+\b"


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


def _build_sentiment_label(score: float) -> str:
    if score > DEFAULT_SENTIMENT_POSITIVE:
        return "正"
    if score < DEFAULT_SENTIMENT_NEGATIVE:
        return "负"
    return "中"


def _score_with_snownlp(
    texts: list[str],
    update_progress: Callable[[float, str], None],
    start_progress: float,
    end_progress: float,
    stage_label: str,
) -> list[float]:
    total = max(len(texts), 1)
    scores: list[float] = []
    for index, text in enumerate(texts):
        if index % max(1, total // 10) == 0:
            progress = start_progress + ((end_progress - start_progress) * index / total)
            update_progress(progress, f"{stage_label} {index}/{total}")

        if not str(text or "").strip():
            scores.append(0.5)
            continue

        try:
            score = float(SnowNLP(text).sentiments)
            scores.append(max(0.0, min(1.0, score)))
        except Exception as exc:
            logger.warning("SnowNLP sentiment failed at row %s: %s", index, exc)
            scores.append(0.5)
    return scores


def _restore_default_snownlp_model() -> None:
    if DEFAULT_SNOW_MODEL_PATH:
        try:
            snownlp_sentiment.load(DEFAULT_SNOW_MODEL_PATH)
        except Exception as exc:
            logger.warning("Failed to restore default SnowNLP model: %s", exc)


def _run_second_pass_snownlp(
    texts: list[str],
    first_pass_scores: list[float],
    positive_threshold: float,
    negative_threshold: float,
    update_progress: Callable[[float, str], None],
) -> Dict[str, Any]:
    pseudo_positive = [text for text, score in zip(texts, first_pass_scores) if str(text or "").strip() and score >= positive_threshold]
    pseudo_negative = [text for text, score in zip(texts, first_pass_scores) if str(text or "").strip() and score <= negative_threshold]
    summary = {
        "enabled": True,
        "trained": False,
        "positive_threshold": positive_threshold,
        "negative_threshold": negative_threshold,
        "pseudo_positive_count": len(pseudo_positive),
        "pseudo_negative_count": len(pseudo_negative),
        "warning": None,
    }

    if len(pseudo_positive) < 2 or len(pseudo_negative) < 2:
        summary["warning"] = "高置信度伪标签样本不足，已保留首轮 SnowNLP 结果"
        return summary

    update_progress(45.0, "正在训练第二轮 SnowNLP 模型...")
    with tempfile.TemporaryDirectory() as temp_dir:
        neg_file = Path(temp_dir) / "neg.txt"
        pos_file = Path(temp_dir) / "pos.txt"
        model_file = Path(temp_dir) / "snownlp-second-pass.zip"
        neg_file.write_text("\n".join(pseudo_negative), encoding="utf-8")
        pos_file.write_text("\n".join(pseudo_positive), encoding="utf-8")

        try:
            snownlp_sentiment.train(str(neg_file), str(pos_file))
            snownlp_sentiment.save(str(model_file))
            snownlp_sentiment.load(str(model_file))
            summary["trained"] = True
        except Exception as exc:
            logger.warning("Second-pass SnowNLP training failed: %s", exc)
            summary["warning"] = f"第二轮 SnowNLP 训练失败，已保留首轮结果: {exc}"
        return summary


def _score_with_deepseek(
    texts: list[str],
    api_key: str,
    base_url: str,
    model_name: str,
    update_progress: Callable[[float, str], None],
) -> list[float]:
    if not api_key:
        raise ValueError("DeepSeek 分析需要提供 API Key")

    client = OpenAI(api_key=api_key, base_url=base_url)
    total = max(len(texts), 1)
    scores: list[float] = []
    for index, text in enumerate(texts):
        if index % max(1, total // 10) == 0:
            update_progress(30.0 + (30.0 * index / total), f"API 请求进度 {index}/{total}")

        if not str(text or "").strip():
            scores.append(0.5)
            continue

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个情感分析助手。请对用户的文本进行情感打分，返回一个0到1之间的小数，表示情感倾向（0表示极度负面，1表示极度正面，0.5表示中性）。只返回数字，不要返回其他任何内容。",
                    },
                    {"role": "user", "content": text[:1000]},
                ],
                temperature=0.0,
            )
            score = float((response.choices[0].message.content or "").strip())
            scores.append(max(0.0, min(1.0, score)))
        except Exception as exc:
            logger.warning("DeepSeek sentiment failed at row %s: %s", index, exc)
            scores.append(0.5)
    return scores


def _write_csv_artifact(rows: list[dict[str, Any]], file_path: str) -> int:
    pd.DataFrame(rows).to_csv(file_path, index=False, encoding="utf-8")
    return int(os.path.getsize(file_path))


def _build_scope_counter(tokens_list: list[list[str]], sentiment_labels: list[str], scope: str) -> Counter:
    counter: Counter = Counter()
    for tokens, label in zip(tokens_list, sentiment_labels):
        if scope == "positive" and label != "正":
            continue
        if scope == "negative" and label != "负":
            continue
        counter.update(tokens)
    return counter


def build_sentiment_signature(dataset_fingerprint: str, config: Dict[str, Any]) -> str:
    normalized_stopwords = sorted({_clean_token(word) for word in config.get("stopwords", []) if _clean_token(word)})
    normalized_scopes = _normalize_wordcloud_scopes(config.get("wordcloud_scopes"))
    signature_payload = {
        "dataset_fingerprint": dataset_fingerprint,
        "text_column": str(config.get("text_column", "content") or "content").strip(),
        "method": str(config.get("method", "snownlp") or "snownlp").strip().lower(),
        "stopwords": normalized_stopwords,
        "extract_tfidf": _normalize_bool(config.get("extract_tfidf", True), True),
        "top_k": _normalize_int(config.get("top_k", 20), 20, minimum=1),
        "generate_wordcloud": _normalize_bool(config.get("generate_wordcloud", True), True),
        "wordcloud_scopes": normalized_scopes,
        "wordcloud_max_words": _normalize_int(config.get("wordcloud_max_words", 120), 120, minimum=10, maximum=500),
        "wordcloud_palette_key": str(config.get("wordcloud_palette_key", config.get("wc_colormap", "viridis")) or "viridis"),
        "wordcloud_mask_artifact_id": str(config.get("wordcloud_mask_artifact_id", "") or ""),
        "run_lda": _normalize_bool(config.get("run_lda", False), False),
        "lda_k": _normalize_int(config.get("lda_k", config.get("lda_n_topics", 5)), 5, minimum=2, maximum=50),
        "lda_min_k": _normalize_int(config.get("lda_min_k", 2), 2, minimum=2, maximum=50),
        "lda_max_k": _normalize_int(config.get("lda_max_k", 10), 10, minimum=3, maximum=50),
        "generate_lda_vis": _normalize_bool(config.get("generate_lda_vis", False), False),
        "enable_second_pass_snownlp": _normalize_bool(config.get("enable_second_pass_snownlp", True), True),
        "pseudo_label_positive_threshold": _normalize_float(config.get("pseudo_label_positive_threshold", DEFAULT_POSITIVE_THRESHOLD), DEFAULT_POSITIVE_THRESHOLD, minimum=0.5, maximum=1.0),
        "pseudo_label_negative_threshold": _normalize_float(config.get("pseudo_label_negative_threshold", DEFAULT_NEGATIVE_THRESHOLD), DEFAULT_NEGATIVE_THRESHOLD, minimum=0.0, maximum=0.5),
        "export_tfidf_table": _normalize_bool(config.get("export_tfidf_table", True), True),
        "export_lda_table": _normalize_bool(config.get("export_lda_table", True), True),
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
    dataset_name: Optional[str] = None,
) -> Dict[str, Any]:
    dataset_fingerprint = hashlib.md5()
    with open(file_path, "rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            dataset_fingerprint.update(chunk)
    dataset_fingerprint_hex = dataset_fingerprint.hexdigest()
    signature = build_sentiment_signature(dataset_fingerprint_hex, config)

    dataset_display_name = _sanitize_file_part(dataset_name or f"数据集{dataset_id}")
    text_column = str(config.get("text_column", "content") or "content").strip()
    method = str(config.get("method", "snownlp") or "snownlp").strip().lower()
    stopwords = {_clean_token(word) for word in config.get("stopwords", []) if _clean_token(word)}
    extract_tfidf = _normalize_bool(config.get("extract_tfidf", True), True)
    top_k = _normalize_int(config.get("top_k", 20), 20, minimum=1)
    generate_wordcloud = _normalize_bool(config.get("generate_wordcloud", True), True)
    wordcloud_scopes = _normalize_wordcloud_scopes(config.get("wordcloud_scopes"))
    wordcloud_max_words = _normalize_int(config.get("wordcloud_max_words", 120), 120, minimum=10, maximum=500)
    wordcloud_palette_key = str(config.get("wordcloud_palette_key", config.get("wc_colormap", "viridis")) or "viridis")

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

    enable_second_pass_snownlp = _normalize_bool(config.get("enable_second_pass_snownlp", True), True)
    pseudo_positive_threshold = _normalize_float(
        config.get("pseudo_label_positive_threshold", DEFAULT_POSITIVE_THRESHOLD),
        DEFAULT_POSITIVE_THRESHOLD,
        minimum=0.5,
        maximum=1.0,
    )
    pseudo_negative_threshold = _normalize_float(
        config.get("pseudo_label_negative_threshold", DEFAULT_NEGATIVE_THRESHOLD),
        DEFAULT_NEGATIVE_THRESHOLD,
        minimum=0.0,
        maximum=0.5,
    )

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
    for index, text in enumerate(df[text_column].tolist()):
        if index % max(1, total_rows // 10) == 0:
            update_progress(20.0 + (10.0 * index / total_rows), f"分词进度 {index}/{total_rows}")
        tokens_list.append(_tokenize_text(text, stopwords))

    texts = df[text_column].tolist()
    df["tokens"] = [" ".join(words) for words in tokens_list]
    effective_corpus = _build_effective_corpus(tokens_list)
    warnings: list[str] = []
    second_pass_summary: Optional[Dict[str, Any]] = None

    if method == "snownlp":
        update_progress(30.0, "开始 SnowNLP 首轮情感打分...")
        first_pass_scores = _score_with_snownlp(
            texts,
            update_progress=update_progress,
            start_progress=30.0,
            end_progress=45.0,
            stage_label="SnowNLP 首轮进度",
        )

        final_scores = first_pass_scores
        if enable_second_pass_snownlp:
            try:
                second_pass_summary = _run_second_pass_snownlp(
                    texts=texts,
                    first_pass_scores=first_pass_scores,
                    positive_threshold=pseudo_positive_threshold,
                    negative_threshold=pseudo_negative_threshold,
                    update_progress=update_progress,
                )
                if second_pass_summary.get("trained"):
                    final_scores = _score_with_snownlp(
                        texts,
                        update_progress=update_progress,
                        start_progress=45.0,
                        end_progress=60.0,
                        stage_label="SnowNLP 二轮进度",
                    )
                if second_pass_summary.get("warning"):
                    warnings.append(str(second_pass_summary["warning"]))
            finally:
                _restore_default_snownlp_model()

        df["sentiment_score"] = final_scores
        df["sentiment_label"] = [_build_sentiment_label(score) for score in final_scores]
    elif method == "deepseek":
        update_progress(30.0, "开始 DeepSeek API 情感打分...")
        deepseek_scores = _score_with_deepseek(
            texts,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            update_progress=update_progress,
        )
        df["sentiment_score"] = deepseek_scores
        df["sentiment_label"] = [_build_sentiment_label(score) for score in deepseek_scores]
    else:
        raise ValueError(f"暂不支持的方法: {method}")

    update_progress(60.0, "保存分析结果...")
    df.to_parquet(file_path)

    artifacts: list[dict[str, Any]] = []
    charts_dir = Path(f"storage/projects/{project_id}/artifacts/charts")
    tables_dir = Path(f"storage/projects/{project_id}/artifacts/tables")
    charts_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    sentiment_summary_rows = []
    label_counts = pd.Series(df["sentiment_label"]).value_counts()
    for label in ["正", "中", "负"]:
        count = int(label_counts.get(label, 0))
        sentiment_summary_rows.append(
            {
                "label": label,
                "count": count,
                "ratio": round(count / total_rows, 6) if total_rows else 0.0,
            }
        )
    summary_path = tables_dir / f"sentiment_summary_{uuid.uuid4().hex}.csv"
    artifacts.append(
        {
            "name": f"{dataset_display_name}情感分析汇总.csv",
            "type": "csv",
            "file_path": str(summary_path),
            "size": _write_csv_artifact(sentiment_summary_rows, str(summary_path)),
        }
    )

    tfidf_result = None
    if extract_tfidf and effective_corpus:
        update_progress(66.0, "计算 TF-IDF 关键词...")
        vectorizer = TfidfVectorizer(max_features=top_k, token_pattern=_build_word_pattern())
        try:
            tfidf_matrix = vectorizer.fit_transform(effective_corpus)
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            word_scores = sorted(zip(feature_names, scores), key=lambda item: item[1], reverse=True)
            tfidf_result = [{"word": word, "score": float(score)} for word, score in word_scores[:top_k]]

            if _normalize_bool(config.get("export_tfidf_table", True), True) and tfidf_result:
                tfidf_path = tables_dir / f"tfidf_{uuid.uuid4().hex}.csv"
                artifacts.append(
                    {
                        "name": f"{dataset_display_name}TFIDF关键词.csv",
                        "type": "csv",
                        "file_path": str(tfidf_path),
                        "size": _write_csv_artifact(tfidf_result, str(tfidf_path)),
                    }
                )
        except ValueError as exc:
            logger.warning("TF-IDF generation skipped: %s", exc)
            warnings.append(f"TF-IDF 关键词生成跳过: {exc}")
    elif extract_tfidf:
        warnings.append("TF-IDF 关键词生成跳过：有效分词为空")

    lda_result = None
    if run_lda:
        update_progress(72.0, "正在运行 LDA 主题模型分析...")
        try:
            if len(effective_corpus) < 2:
                raise ValueError("可用于 LDA 的有效文本不足，至少需要 2 条非空文本")

            tf_vectorizer = CountVectorizer(
                max_df=lda_max_df,
                min_df=lda_min_df,
                max_features=lda_max_features,
                token_pattern=_build_word_pattern(),
            )
            tf_matrix = tf_vectorizer.fit_transform(effective_corpus)
            feature_names = tf_vectorizer.get_feature_names_out()
            if tf_matrix.shape[0] < 2 or tf_matrix.shape[1] < 2:
                raise ValueError("有效词项不足，无法执行 LDA")

            effective_topic_count = min(lda_n_topics, tf_matrix.shape[0], tf_matrix.shape[1])
            if effective_topic_count < 2:
                raise ValueError("可用语料或词项不足，无法形成至少 2 个主题")
            if effective_topic_count != lda_n_topics:
                warnings.append(f"LDA 主题数已根据语料规模调整为 {effective_topic_count}")

            lda_model = LatentDirichletAllocation(
                n_components=effective_topic_count,
                max_iter=lda_max_iter,
                learning_method=lda_learning_method,
                random_state=42,
                evaluate_every=-1,
            )
            lda_model.fit(tf_matrix)

            topics = []
            topic_rows = []
            for topic_idx, topic in enumerate(lda_model.components_):
                top_features_ind = topic.argsort()[:-lda_top_words - 1 : -1]
                top_features = [feature_names[index] for index in top_features_ind]
                topics.append({"topic": int(topic_idx + 1), "keywords": top_features})
                for rank, keyword in enumerate(top_features, start=1):
                    topic_rows.append({"topic": int(topic_idx + 1), "rank": rank, "keyword": keyword})

            lda_result = {
                "topics": topics,
                "n_topics": int(effective_topic_count),
                "feature_count": int(len(feature_names)),
                "perplexity": float(lda_model.perplexity(tf_matrix)),
                "candidates": None,
                "vis_path": None,
            }

            if evaluate_lda_candidates:
                candidates = []
                for candidate_k in range(min(lda_min_k, lda_max_k), max(lda_min_k, lda_max_k) + 1):
                    if candidate_k < 2 or candidate_k > tf_matrix.shape[0] or candidate_k > tf_matrix.shape[1]:
                        continue
                    candidate_model = LatentDirichletAllocation(
                        n_components=candidate_k,
                        max_iter=min(lda_max_iter, 8),
                        learning_method=lda_learning_method,
                        random_state=42,
                        evaluate_every=-1,
                    )
                    candidate_model.fit(tf_matrix)
                    candidates.append({"k": int(candidate_k), "perplexity": float(candidate_model.perplexity(tf_matrix))})
                lda_result["candidates"] = candidates or None

            if _normalize_bool(config.get("export_lda_table", True), True) and topic_rows:
                lda_csv_path = tables_dir / f"lda_topics_{uuid.uuid4().hex}.csv"
                artifacts.append(
                    {
                        "name": f"{dataset_display_name}LDA分析.csv",
                        "type": "csv",
                        "file_path": str(lda_csv_path),
                        "size": _write_csv_artifact(topic_rows, str(lda_csv_path)),
                    }
                )

            if generate_lda_vis:
                panel = pyLDAvis.lda_model.prepare(lda_model, tf_matrix, tf_vectorizer, mds="tsne")
                lda_html_path = charts_dir / f"lda_vis_{uuid.uuid4().hex}.html"
                pyLDAvis.save_html(panel, str(lda_html_path))
                artifacts.append(
                    {
                        "name": f"{dataset_display_name}LDA可视化.html",
                        "type": "html",
                        "file_path": str(lda_html_path),
                        "size": int(os.path.getsize(lda_html_path)),
                    }
                )
                lda_result["vis_path"] = str(lda_html_path)
        except Exception as exc:
            logger.warning("LDA generation skipped: %s", exc)
            warnings.append(f"LDA 主题模型生成跳过: {exc}")
            lda_result = None

    generated_wordclouds = []
    if generate_wordcloud:
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
                warnings.append(f"词云轮廓图加载失败，已使用默认矩形画布: {exc}")
                mask = None

        for scope in wordcloud_scopes:
            counter = _build_scope_counter(tokens_list, df["sentiment_label"].tolist(), scope)
            if not counter:
                warnings.append(f"{WORDCLOUD_SCOPE_LABELS[scope]}词云没有可用词项，已跳过")
                continue
            try:
                wc_kwargs: Dict[str, Any] = {
                    "width": 800,
                    "height": 600,
                    "background_color": "white",
                    "max_words": wordcloud_max_words,
                    "colormap": wordcloud_palette_key,
                    "mask": mask,
                    "contour_width": 3 if (mask is not None and _normalize_bool(config.get("wc_contour", False), False)) else 0,
                    "contour_color": "steelblue" if (mask is not None and _normalize_bool(config.get("wc_contour", False), False)) else None,
                }
                if font_path:
                    wc_kwargs["font_path"] = font_path

                wordcloud = WordCloud(**wc_kwargs).generate_from_frequencies(dict(counter.most_common(wordcloud_max_words)))
                wc_path = charts_dir / f"wordcloud_{scope}_{uuid.uuid4().hex}.png"
                wordcloud.to_file(str(wc_path))
                artifact_name = f"{dataset_display_name}{WORDCLOUD_SCOPE_LABELS[scope]}词云.png"
                artifacts.append(
                    {
                        "name": artifact_name,
                        "type": "png",
                        "file_path": str(wc_path),
                        "size": int(os.path.getsize(wc_path)),
                    }
                )
                generated_wordclouds.append({"scope": scope, "name": artifact_name})
            except Exception as exc:
                logger.warning("Wordcloud generation skipped for scope %s: %s", scope, exc)
                warnings.append(f"{WORDCLOUD_SCOPE_LABELS[scope]}词云生成失败: {exc}")

    update_progress(100.0, "情感分析完成")
    return {
        "message": "情感分析完成",
        "kind": "sentiment_analysis",
        "signature": signature,
        "dataset_fingerprint": dataset_fingerprint_hex,
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "row_count": total_rows,
        "text_column": text_column,
        "artifacts": artifacts,
        "warnings": warnings,
        "second_pass": second_pass_summary,
        "sentiment_summary": {row["label"]: row["count"] for row in sentiment_summary_rows},
        "sentiment_distribution": sentiment_summary_rows,
        "tfidf": tfidf_result,
        "lda": lda_result,
        "wordclouds": generated_wordclouds,
    }

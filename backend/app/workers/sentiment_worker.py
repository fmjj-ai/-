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
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL_NAME = "deepseek-chat"
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


def _normalize_stopwords(value: Any) -> set[str]:
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {_clean_token(word) for word in value if _clean_token(word)}


def _normalize_text_column(config: Dict[str, Any]) -> str:
    return str(config.get("text_column", "content") or "content").strip()


def _normalize_method(config: Dict[str, Any]) -> str:
    return str(config.get("method", "snownlp") or "snownlp").strip().lower()


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


def _normalize_wordcloud_palette_key(config: Dict[str, Any]) -> str:
    return str(config.get("wordcloud_palette_key", config.get("wc_colormap", "viridis")) or "viridis")


def _normalize_lda_learning_method(value: Any) -> str:
    learning_method = str(value or "batch").strip().lower()
    return learning_method if learning_method in {"batch", "online"} else "batch"


def _normalize_lda_min_df(value: Any) -> float | int:
    normalized = _normalize_float(value, 1.0, minimum=0.0)
    if isinstance(value, str) and "." in value:
        return _normalize_float(value, 0.01, minimum=0.0, maximum=1.0)
    if normalized >= 1:
        return int(normalized)
    return normalized


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
        candidate_paths.extend(
            [
                os.path.join(windows_font_dir, "msyh.ttc"),
                os.path.join(windows_font_dir, "simhei.ttf"),
                os.path.join(windows_font_dir, "simsun.ttc"),
            ]
        )
    else:
        if font_name and os.path.isabs(font_name):
            candidate_paths.append(font_name)
        candidate_paths.extend(
            [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
            ]
        )

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


def _build_signature_payload(dataset_fingerprint: str, config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "dataset_fingerprint": dataset_fingerprint,
        "text_column": _normalize_text_column(config),
        "method": _normalize_method(config),
        "stopwords": sorted(_normalize_stopwords(config.get("stopwords"))),
        "extract_tfidf": _normalize_bool(config.get("extract_tfidf", True), True),
        "top_k": _normalize_int(config.get("top_k", 20), 20, minimum=1),
        "generate_wordcloud": _normalize_bool(config.get("generate_wordcloud", True), True),
        "wordcloud_scopes": _normalize_wordcloud_scopes(config.get("wordcloud_scopes")),
        "wordcloud_max_words": _normalize_int(config.get("wordcloud_max_words", 120), 120, minimum=10, maximum=500),
        "wordcloud_palette_key": _normalize_wordcloud_palette_key(config),
        "wordcloud_mask_artifact_id": str(config.get("wordcloud_mask_artifact_id", "") or ""),
        "run_lda": _normalize_bool(config.get("run_lda", False), False),
        "lda_k": _normalize_int(config.get("lda_k", config.get("lda_n_topics", 5)), 5, minimum=2, maximum=50),
        "lda_min_k": _normalize_int(config.get("lda_min_k", 2), 2, minimum=2, maximum=50),
        "lda_max_k": _normalize_int(config.get("lda_max_k", 10), 10, minimum=3, maximum=50),
        "generate_lda_vis": _normalize_bool(config.get("generate_lda_vis", False), False),
        "enable_second_pass_snownlp": _normalize_bool(config.get("enable_second_pass_snownlp", True), True),
        "pseudo_label_positive_threshold": _normalize_float(
            config.get("pseudo_label_positive_threshold", DEFAULT_POSITIVE_THRESHOLD),
            DEFAULT_POSITIVE_THRESHOLD,
            minimum=0.5,
            maximum=1.0,
        ),
        "pseudo_label_negative_threshold": _normalize_float(
            config.get("pseudo_label_negative_threshold", DEFAULT_NEGATIVE_THRESHOLD),
            DEFAULT_NEGATIVE_THRESHOLD,
            minimum=0.0,
            maximum=0.5,
        ),
        "export_tfidf_table": _normalize_bool(config.get("export_tfidf_table", True), True),
        "export_lda_table": _normalize_bool(config.get("export_lda_table", True), True),
        "wc_font": str(config.get("wc_font", "") or ""),
        "wc_contour": _normalize_bool(config.get("wc_contour", False), False),
        "base_url": str(config.get("base_url", "") or "").strip(),
        "model_name": str(config.get("model_name", "") or "").strip(),
        "api_key_present": bool(str(config.get("api_key", "") or "").strip()),
    }


def build_sentiment_signature(dataset_fingerprint: str, config: Dict[str, Any]) -> str:
    payload = json.dumps(_build_signature_payload(dataset_fingerprint, config), ensure_ascii=False, sort_keys=True)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _build_dataset_fingerprint(file_path: str) -> str:
    dataset_fingerprint = hashlib.md5()
    with open(file_path, "rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            dataset_fingerprint.update(chunk)
    return dataset_fingerprint.hexdigest()


def _build_runtime_options(config: Dict[str, Any]) -> Dict[str, Any]:
    lda_n_topics = _normalize_int(config.get("lda_k", config.get("lda_n_topics", 5)), 5, minimum=2, maximum=50)
    lda_min_k = _normalize_int(config.get("lda_min_k", 2), 2, minimum=2, maximum=50)

    return {
        "text_column": _normalize_text_column(config),
        "method": _normalize_method(config),
        "stopwords": _normalize_stopwords(config.get("stopwords")),
        "extract_tfidf": _normalize_bool(config.get("extract_tfidf", True), True),
        "top_k": _normalize_int(config.get("top_k", 20), 20, minimum=1),
        "export_tfidf_table": _normalize_bool(config.get("export_tfidf_table", True), True),
        "generate_wordcloud": _normalize_bool(config.get("generate_wordcloud", True), True),
        "wordcloud_scopes": _normalize_wordcloud_scopes(config.get("wordcloud_scopes")),
        "wordcloud_max_words": _normalize_int(config.get("wordcloud_max_words", 120), 120, minimum=10, maximum=500),
        "wordcloud_palette_key": _normalize_wordcloud_palette_key(config),
        "wc_font": str(config.get("wc_font", "") or ""),
        "wc_font_path": config.get("wc_font_path"),
        "font_path": config.get("font_path"),
        "wc_contour": _normalize_bool(config.get("wc_contour", False), False),
        "mask_path": str(config.get("mask_path", "") or "").strip(),
        "run_lda": _normalize_bool(config.get("run_lda", False), False),
        "lda_n_topics": lda_n_topics,
        "lda_min_k": lda_min_k,
        "lda_max_k": _normalize_int(
            config.get("lda_max_k", max(lda_min_k + 1, lda_n_topics)),
            max(lda_min_k + 1, lda_n_topics),
            minimum=lda_min_k + 1,
            maximum=50,
        ),
        "lda_top_words": _normalize_int(config.get("lda_top_words", 10), 10, minimum=3, maximum=30),
        "lda_max_features": _normalize_int(config.get("lda_max_features", 1000), 1000, minimum=50, maximum=5000),
        "lda_max_iter": _normalize_int(config.get("lda_max_iter", 10), 10, minimum=5, maximum=100),
        "lda_learning_method": _normalize_lda_learning_method(config.get("lda_learning_method", "batch")),
        "lda_min_df": _normalize_lda_min_df(config.get("lda_min_df", 1)),
        "lda_max_df": _normalize_float(config.get("lda_max_df", 0.95), 0.95, minimum=0.1, maximum=1.0),
        "evaluate_lda_candidates": _normalize_bool(config.get("evaluate_lda_candidates", True), True),
        "generate_lda_vis": _normalize_bool(config.get("generate_lda_vis", False), False),
        "export_lda_table": _normalize_bool(config.get("export_lda_table", True), True),
        "enable_second_pass_snownlp": _normalize_bool(config.get("enable_second_pass_snownlp", True), True),
        "pseudo_positive_threshold": _normalize_float(
            config.get("pseudo_label_positive_threshold", DEFAULT_POSITIVE_THRESHOLD),
            DEFAULT_POSITIVE_THRESHOLD,
            minimum=0.5,
            maximum=1.0,
        ),
        "pseudo_negative_threshold": _normalize_float(
            config.get("pseudo_label_negative_threshold", DEFAULT_NEGATIVE_THRESHOLD),
            DEFAULT_NEGATIVE_THRESHOLD,
            minimum=0.0,
            maximum=0.5,
        ),
        "api_key": str(config.get("api_key", "") or "").strip(),
        "base_url": str(config.get("base_url", DEFAULT_DEEPSEEK_BASE_URL) or DEFAULT_DEEPSEEK_BASE_URL).strip(),
        "model_name": str(config.get("model_name", DEFAULT_DEEPSEEK_MODEL_NAME) or DEFAULT_DEEPSEEK_MODEL_NAME).strip(),
    }


def _load_sentiment_dataframe(file_path: str, text_column: str) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_parquet(file_path)
    if text_column not in df.columns:
        raise ValueError(f"列 {text_column} 不存在")

    df[text_column] = df[text_column].fillna("").astype(str)
    texts = df[text_column].tolist()
    if not texts:
        raise ValueError("数据为空")
    return df, texts


def _tokenize_texts(
    texts: list[str],
    stopwords: set[str],
    update_progress: Callable[[float, str], None],
) -> list[list[str]]:
    total_rows = len(texts)
    tokens_list: list[list[str]] = []
    for index, text in enumerate(texts):
        if index % max(1, total_rows // 10) == 0:
            update_progress(20.0 + (10.0 * index / total_rows), f"分词进度 {index}/{total_rows}")
        tokens_list.append(_tokenize_text(text, stopwords))
    return tokens_list


def _analyze_with_snownlp(
    texts: list[str],
    options: Dict[str, Any],
    update_progress: Callable[[float, str], None],
    warnings: list[str],
) -> tuple[list[float], Optional[Dict[str, Any]]]:
    update_progress(30.0, "开始 SnowNLP 首轮情感打分...")
    first_pass_scores = _score_with_snownlp(
        texts,
        update_progress=update_progress,
        start_progress=30.0,
        end_progress=45.0,
        stage_label="SnowNLP 首轮进度",
    )

    final_scores = first_pass_scores
    second_pass_summary: Optional[Dict[str, Any]] = None
    if options["enable_second_pass_snownlp"]:
        try:
            second_pass_summary = _run_second_pass_snownlp(
                texts=texts,
                first_pass_scores=first_pass_scores,
                positive_threshold=options["pseudo_positive_threshold"],
                negative_threshold=options["pseudo_negative_threshold"],
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

    return final_scores, second_pass_summary


def _analyze_sentiment(
    texts: list[str],
    options: Dict[str, Any],
    update_progress: Callable[[float, str], None],
    warnings: list[str],
) -> tuple[list[float], Optional[Dict[str, Any]]]:
    if options["method"] == "snownlp":
        return _analyze_with_snownlp(texts, options, update_progress, warnings)
    if options["method"] == "deepseek":
        update_progress(30.0, "开始 DeepSeek API 情感打分...")
        deepseek_scores = _score_with_deepseek(
            texts,
            api_key=options["api_key"],
            base_url=options["base_url"],
            model_name=options["model_name"],
            update_progress=update_progress,
        )
        return deepseek_scores, None
    raise ValueError(f"暂不支持的方法: {options['method']}")


def _build_sentiment_summary_rows(sentiment_labels: list[str], total_rows: int) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []
    label_counts = pd.Series(sentiment_labels).value_counts()
    for label in ["正", "中", "负"]:
        count = int(label_counts.get(label, 0))
        summary_rows.append(
            {
                "label": label,
                "count": count,
                "ratio": round(count / total_rows, 6) if total_rows else 0.0,
            }
        )
    return summary_rows


def _create_csv_artifact(name: str, file_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "type": "csv",
        "file_path": str(file_path),
        "size": _write_csv_artifact(rows, str(file_path)),
    }


def _build_tfidf_result(
    effective_corpus: list[str],
    options: Dict[str, Any],
    tables_dir: Path,
    artifacts: list[dict[str, Any]],
    warnings: list[str],
    dataset_display_name: str,
    update_progress: Callable[[float, str], None],
) -> Optional[list[dict[str, Any]]]:
    if not options["extract_tfidf"]:
        return None
    if not effective_corpus:
        warnings.append("TF-IDF 关键词生成跳过：有效分词为空")
        return None

    update_progress(66.0, "计算 TF-IDF 关键词...")
    vectorizer = TfidfVectorizer(max_features=options["top_k"], token_pattern=_build_word_pattern())
    try:
        tfidf_matrix = vectorizer.fit_transform(effective_corpus)
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.sum(axis=0).A1
        word_scores = sorted(zip(feature_names, scores), key=lambda item: item[1], reverse=True)
        tfidf_result = [{"word": word, "score": float(score)} for word, score in word_scores[: options["top_k"]]]

        if options["export_tfidf_table"] and tfidf_result:
            tfidf_path = tables_dir / f"tfidf_{uuid.uuid4().hex}.csv"
            artifacts.append(
                _create_csv_artifact(
                    name=f"{dataset_display_name}TFIDF关键词.csv",
                    file_path=tfidf_path,
                    rows=tfidf_result,
                )
            )
        return tfidf_result
    except ValueError as exc:
        logger.warning("TF-IDF generation skipped: %s", exc)
        warnings.append(f"TF-IDF 关键词生成跳过: {exc}")
        return None


def _build_lda_result(
    effective_corpus: list[str],
    options: Dict[str, Any],
    charts_dir: Path,
    tables_dir: Path,
    artifacts: list[dict[str, Any]],
    warnings: list[str],
    dataset_display_name: str,
    update_progress: Callable[[float, str], None],
) -> Optional[Dict[str, Any]]:
    if not options["run_lda"]:
        return None

    update_progress(72.0, "正在运行 LDA 主题模型分析...")
    try:
        if len(effective_corpus) < 2:
            raise ValueError("可用于 LDA 的有效文本不足，至少需要 2 条非空文本")

        tf_vectorizer = CountVectorizer(
            max_df=options["lda_max_df"],
            min_df=options["lda_min_df"],
            max_features=options["lda_max_features"],
            token_pattern=_build_word_pattern(),
        )
        tf_matrix = tf_vectorizer.fit_transform(effective_corpus)
        feature_names = tf_vectorizer.get_feature_names_out()
        if tf_matrix.shape[0] < 2 or tf_matrix.shape[1] < 2:
            raise ValueError("有效词项不足，无法执行 LDA")

        effective_topic_count = min(options["lda_n_topics"], tf_matrix.shape[0], tf_matrix.shape[1])
        if effective_topic_count < 2:
            raise ValueError("可用语料或词项不足，无法形成至少 2 个主题")
        if effective_topic_count != options["lda_n_topics"]:
            warnings.append(f"LDA 主题数已根据语料规模调整为 {effective_topic_count}")

        lda_model = LatentDirichletAllocation(
            n_components=effective_topic_count,
            max_iter=options["lda_max_iter"],
            learning_method=options["lda_learning_method"],
            random_state=42,
            evaluate_every=-1,
        )
        lda_model.fit(tf_matrix)

        topics: list[dict[str, Any]] = []
        topic_rows: list[dict[str, Any]] = []
        for topic_index, topic in enumerate(lda_model.components_):
            top_features_index = topic.argsort()[: -options["lda_top_words"] - 1 : -1]
            top_features = [feature_names[index] for index in top_features_index]
            topics.append({"topic": int(topic_index + 1), "keywords": top_features})
            for rank, keyword in enumerate(top_features, start=1):
                topic_rows.append({"topic": int(topic_index + 1), "rank": rank, "keyword": keyword})

        lda_result: Dict[str, Any] = {
            "topics": topics,
            "n_topics": int(effective_topic_count),
            "feature_count": int(len(feature_names)),
            "perplexity": float(lda_model.perplexity(tf_matrix)),
            "candidates": None,
            "vis_path": None,
        }

        if options["evaluate_lda_candidates"]:
            candidates = []
            for candidate_k in range(min(options["lda_min_k"], options["lda_max_k"]), max(options["lda_min_k"], options["lda_max_k"]) + 1):
                if candidate_k < 2 or candidate_k > tf_matrix.shape[0] or candidate_k > tf_matrix.shape[1]:
                    continue
                candidate_model = LatentDirichletAllocation(
                    n_components=candidate_k,
                    max_iter=min(options["lda_max_iter"], 8),
                    learning_method=options["lda_learning_method"],
                    random_state=42,
                    evaluate_every=-1,
                )
                candidate_model.fit(tf_matrix)
                candidates.append({"k": int(candidate_k), "perplexity": float(candidate_model.perplexity(tf_matrix))})
            lda_result["candidates"] = candidates or None

        if options["export_lda_table"] and topic_rows:
            lda_csv_path = tables_dir / f"lda_topics_{uuid.uuid4().hex}.csv"
            artifacts.append(
                _create_csv_artifact(
                    name=f"{dataset_display_name}LDA分析.csv",
                    file_path=lda_csv_path,
                    rows=topic_rows,
                )
            )

        if options["generate_lda_vis"]:
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
        return lda_result
    except Exception as exc:
        logger.warning("LDA generation skipped: %s", exc)
        warnings.append(f"LDA 主题模型生成跳过: {exc}")
        return None


def _load_wordcloud_mask(mask_path: str, warnings: list[str]) -> Optional[np.ndarray]:
    if not mask_path or not os.path.exists(mask_path):
        return None

    try:
        from PIL import Image

        return np.array(Image.open(mask_path))
    except Exception as exc:
        logger.warning("Failed to load wordcloud mask %s: %s", mask_path, exc)
        warnings.append(f"词云轮廓图加载失败，已使用默认矩形画布: {exc}")
        return None


def _generate_wordclouds(
    tokens_list: list[list[str]],
    sentiment_labels: list[str],
    options: Dict[str, Any],
    charts_dir: Path,
    artifacts: list[dict[str, Any]],
    warnings: list[str],
    dataset_display_name: str,
    update_progress: Callable[[float, str], None],
) -> list[dict[str, Any]]:
    if not options["generate_wordcloud"]:
        return []

    update_progress(90.0, "生成词云图...")
    font_path = _resolve_wordcloud_font_path(options)
    mask = _load_wordcloud_mask(options["mask_path"], warnings)
    generated_wordclouds: list[dict[str, Any]] = []

    for scope in options["wordcloud_scopes"]:
        counter = _build_scope_counter(tokens_list, sentiment_labels, scope)
        if not counter:
            warnings.append(f"{WORDCLOUD_SCOPE_LABELS[scope]}词云没有可用词项，已跳过")
            continue

        try:
            wc_kwargs: Dict[str, Any] = {
                "width": 800,
                "height": 600,
                "background_color": "white",
                "max_words": options["wordcloud_max_words"],
                "colormap": options["wordcloud_palette_key"],
                "mask": mask,
                "contour_width": 3 if (mask is not None and options["wc_contour"]) else 0,
                "contour_color": "steelblue" if (mask is not None and options["wc_contour"]) else None,
            }
            if font_path:
                wc_kwargs["font_path"] = font_path

            wordcloud = WordCloud(**wc_kwargs).generate_from_frequencies(
                dict(counter.most_common(options["wordcloud_max_words"]))
            )
            wordcloud_path = charts_dir / f"wordcloud_{scope}_{uuid.uuid4().hex}.png"
            wordcloud.to_file(str(wordcloud_path))
            artifact_name = f"{dataset_display_name}{WORDCLOUD_SCOPE_LABELS[scope]}词云.png"
            artifacts.append(
                {
                    "name": artifact_name,
                    "type": "png",
                    "file_path": str(wordcloud_path),
                    "size": int(os.path.getsize(wordcloud_path)),
                }
            )
            generated_wordclouds.append({"scope": scope, "name": artifact_name})
        except Exception as exc:
            logger.warning("Wordcloud generation skipped for scope %s: %s", scope, exc)
            warnings.append(f"{WORDCLOUD_SCOPE_LABELS[scope]}词云生成失败: {exc}")

    return generated_wordclouds


def _ensure_artifact_dirs(project_id: int) -> tuple[Path, Path]:
    charts_dir = Path(f"storage/projects/{project_id}/artifacts/charts")
    tables_dir = Path(f"storage/projects/{project_id}/artifacts/tables")
    charts_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    return charts_dir, tables_dir


def run_sentiment_task(
    dataset_id: int,
    file_path: str,
    config: Dict[str, Any],
    project_id: int,
    update_progress: Callable[[float, str], None],
    dataset_name: Optional[str] = None,
) -> Dict[str, Any]:
    dataset_fingerprint_hex = _build_dataset_fingerprint(file_path)
    signature = build_sentiment_signature(dataset_fingerprint_hex, config)
    options = _build_runtime_options(config)
    dataset_display_name = _sanitize_file_part(dataset_name or f"数据集{dataset_id}")

    update_progress(10.0, "正在加载数据...")
    df, texts = _load_sentiment_dataframe(file_path, options["text_column"])
    total_rows = len(texts)

    update_progress(20.0, "开始分词...")
    tokens_list = _tokenize_texts(texts, options["stopwords"], update_progress)
    df["tokens"] = [" ".join(words) for words in tokens_list]
    effective_corpus = _build_effective_corpus(tokens_list)
    warnings: list[str] = []

    scores, second_pass_summary = _analyze_sentiment(texts, options, update_progress, warnings)
    df["sentiment_score"] = scores
    df["sentiment_label"] = [_build_sentiment_label(score) for score in scores]

    update_progress(60.0, "保存分析结果...")
    df.to_parquet(file_path)

    charts_dir, tables_dir = _ensure_artifact_dirs(project_id)
    artifacts: list[dict[str, Any]] = []
    sentiment_summary_rows = _build_sentiment_summary_rows(df["sentiment_label"].tolist(), total_rows)
    summary_path = tables_dir / f"sentiment_summary_{uuid.uuid4().hex}.csv"
    artifacts.append(
        _create_csv_artifact(
            name=f"{dataset_display_name}情感分析汇总.csv",
            file_path=summary_path,
            rows=sentiment_summary_rows,
        )
    )

    tfidf_result = _build_tfidf_result(
        effective_corpus=effective_corpus,
        options=options,
        tables_dir=tables_dir,
        artifacts=artifacts,
        warnings=warnings,
        dataset_display_name=dataset_display_name,
        update_progress=update_progress,
    )
    lda_result = _build_lda_result(
        effective_corpus=effective_corpus,
        options=options,
        charts_dir=charts_dir,
        tables_dir=tables_dir,
        artifacts=artifacts,
        warnings=warnings,
        dataset_display_name=dataset_display_name,
        update_progress=update_progress,
    )
    generated_wordclouds = _generate_wordclouds(
        tokens_list=tokens_list,
        sentiment_labels=df["sentiment_label"].tolist(),
        options=options,
        charts_dir=charts_dir,
        artifacts=artifacts,
        warnings=warnings,
        dataset_display_name=dataset_display_name,
        update_progress=update_progress,
    )

    update_progress(100.0, "情感分析完成")
    return {
        "message": "情感分析完成",
        "kind": "sentiment_analysis",
        "signature": signature,
        "dataset_fingerprint": dataset_fingerprint_hex,
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "row_count": total_rows,
        "text_column": options["text_column"],
        "artifacts": artifacts,
        "warnings": warnings,
        "second_pass": second_pass_summary,
        "sentiment_summary": {row["label"]: row["count"] for row in sentiment_summary_rows},
        "sentiment_distribution": sentiment_summary_rows,
        "tfidf": tfidf_result,
        "lda": lda_result,
        "wordclouds": generated_wordclouds,
    }

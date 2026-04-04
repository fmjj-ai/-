import os
import pandas as pd
import jieba
from snownlp import SnowNLP
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from typing import Dict, Any, Callable
import uuid

def run_sentiment_task(
    dataset_id: int,
    file_path: str,
    config: Dict[str, Any],
    project_id: int,
    update_progress: Callable[[float, str], None]
) -> Dict[str, Any]:
    text_column = config.get("text_column", "content")
    method = config.get("method", "snownlp")
    stopwords = set(config.get("stopwords", []))
    extract_tfidf = config.get("extract_tfidf", True)
    top_k = config.get("top_k", 20)
    generate_wordcloud = config.get("generate_wordcloud", True)

    update_progress(10.0, "正在加载数据...")
    df = pd.read_parquet(file_path)

    if text_column not in df.columns:
        raise ValueError(f"列 {text_column} 不存在")

    # 处理缺失值
    df[text_column] = df[text_column].fillna("").astype(str)
    
    total_rows = len(df)
    if total_rows == 0:
        raise ValueError("数据为空")

    update_progress(20.0, "开始分词...")
    # jieba 分词 & 去停用词
    tokens_list = []
    
    # 手动实现带进度的分词
    for i, text in enumerate(df[text_column]):
        if i % max(1, total_rows // 10) == 0:
            update_progress(20.0 + (30.0 * i / total_rows), f"分词进度 {i}/{total_rows}")
        
        words = jieba.lcut(text)
        filtered_words = [w for w in words if w.strip() and w not in stopwords]
        tokens_list.append(filtered_words)

    df["tokens"] = [" ".join(words) for words in tokens_list]

    # 情感打分
    if method == "snownlp":
        update_progress(50.0, "开始 SnowNLP 情感打分...")
        sentiment_scores = []
        sentiment_labels = []
        for i, text in enumerate(df[text_column]):
            if i % max(1, total_rows // 10) == 0:
                update_progress(50.0 + (30.0 * i / total_rows), f"打分进度 {i}/{total_rows}")
            
            if not text.strip():
                sentiment_scores.append(0.5)
                sentiment_labels.append("中")
                continue
            
            try:
                s = SnowNLP(text)
                score = s.sentiments
                sentiment_scores.append(score)
                if score > 0.6:
                    sentiment_labels.append("正")
                elif score < 0.4:
                    sentiment_labels.append("负")
                else:
                    sentiment_labels.append("中")
            except Exception:
                sentiment_scores.append(0.5)
                sentiment_labels.append("中")

        df["sentiment_score"] = sentiment_scores
        df["sentiment_label"] = sentiment_labels
    else:
        raise ValueError(f"暂不支持的方法: {method}")

    update_progress(80.0, "保存分析结果...")
    # 把打分结果写回工作副本
    df.to_parquet(file_path)

    artifacts = []
    
    # TF-IDF
    tfidf_result = None
    if extract_tfidf:
        update_progress(85.0, "计算 TF-IDF 关键词...")
        vectorizer = TfidfVectorizer(max_features=top_k)
        corpus = df["tokens"].tolist()
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            word_scores = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
            tfidf_result = [{"word": w, "score": float(s)} for w, s in word_scores[:top_k]]
        except ValueError:
            # Empty vocabulary
            pass

    # WordCloud
    wordcloud_artifact = None
    if generate_wordcloud and tfidf_result:
        update_progress(90.0, "生成词云图...")
        text_for_cloud = " ".join([w for w, s in tfidf_result])
        if text_for_cloud:
            # 必须指定中文字体，否则乱码
            font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc" # 需要确保系统有中文字体
            if not os.path.exists(font_path):
                # fallback 
                font_path = None
            
            wc = WordCloud(
                font_path=font_path,
                width=800, 
                height=600, 
                background_color="white",
                max_words=100
            ).generate_from_frequencies({w: s for w, s in tfidf_result})
            
            artifacts_dir = f"storage/projects/{project_id}/artifacts/charts"
            os.makedirs(artifacts_dir, exist_ok=True)
            
            wc_id = str(uuid.uuid4())
            wc_path = os.path.join(artifacts_dir, f"wordcloud_{wc_id}.png")
            wc.to_file(wc_path)
            
            artifacts.append({
                "name": f"词云图_{wc_id}",
                "type": "png",
                "file_path": wc_path,
                "size": os.path.getsize(wc_path)
            })
            wordcloud_artifact = wc_path

    update_progress(100.0, "情感分析完成")
    return {
        "message": "情感分析完成",
        "artifacts": artifacts,
        "tfidf": tfidf_result
    }

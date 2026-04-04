import os
import pandas as pd
import numpy as np
import jieba
from snownlp import SnowNLP
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import pyLDAvis
import pyLDAvis.lda_model
from typing import Dict, Any, Callable
import uuid
import json
from openai import OpenAI

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
    
    # LDA settings
    run_lda = config.get("run_lda", False)
    lda_n_topics = config.get("lda_n_topics", 5)
    
    # DeepSeek settings
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "https://api.deepseek.com/v1")

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
    
    for i, text in enumerate(df[text_column]):
        if i % max(1, total_rows // 10) == 0:
            update_progress(20.0 + (10.0 * i / total_rows), f"分词进度 {i}/{total_rows}")
        
        words = jieba.lcut(text)
        filtered_words = [w for w in words if w.strip() and w not in stopwords]
        tokens_list.append(filtered_words)

    df["tokens"] = [" ".join(words) for words in tokens_list]
    corpus = df["tokens"].tolist()

    # 情感打分
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
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个情感分析助手。请对用户的文本进行情感打分，返回一个0到1之间的小数，表示情感倾向（0表示极度负面，1表示极度正面，0.5表示中性）。只返回数字，不要返回其他任何内容。"},
                        {"role": "user", "content": text[:1000]} # Limit length to save tokens
                    ],
                    temperature=0.0
                )
                score_str = response.choices[0].message.content.strip()
                score = float(score_str)
                score = max(0.0, min(1.0, score))
                sentiment_scores.append(score)
                if score > 0.6:
                    sentiment_labels.append("正")
                elif score < 0.4:
                    sentiment_labels.append("负")
                else:
                    sentiment_labels.append("中")
            except Exception as e:
                # Fallback on error
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
    
    # TF-IDF
    tfidf_result = None
    if extract_tfidf:
        update_progress(65.0, "计算 TF-IDF 关键词...")
        vectorizer = TfidfVectorizer(max_features=top_k)
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            word_scores = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
            tfidf_result = [{"word": w, "score": float(s)} for w, s in word_scores[:top_k]]
        except ValueError:
            pass

    # LDA 主题模型
    lda_result = None
    if run_lda:
        update_progress(70.0, "正在运行 LDA 主题模型分析...")
        try:
            tf_vectorizer = CountVectorizer(max_df=0.95, min_df=2, max_features=1000)
            tf = tf_vectorizer.fit_transform(corpus)
            
            # 困惑度曲线（评估不同主题数的困惑度，实际中为了性能通常只计算几个点或直接训练指定主题数）
            lda_model = LatentDirichletAllocation(
                n_components=lda_n_topics, 
                max_iter=10, 
                learning_method='online', 
                random_state=42
            )
            lda_model.fit(tf)
            
            # 提取每个主题的关键词
            feature_names = tf_vectorizer.get_feature_names_out()
            topics = []
            for topic_idx, topic in enumerate(lda_model.components_):
                top_features_ind = topic.argsort()[:-10 - 1:-1]
                top_features = [feature_names[i] for i in top_features_ind]
                topics.append({"topic": topic_idx, "keywords": top_features})
                
            # 生成 pyLDAvis HTML
            panel = pyLDAvis.lda_model.prepare(lda_model, tf, tf_vectorizer, mds='tsne')
            lda_html_id = str(uuid.uuid4())
            lda_html_path = os.path.join(artifacts_dir, f"lda_vis_{lda_html_id}.html")
            pyLDAvis.save_html(panel, lda_html_path)
            
            artifacts.append({
                "name": f"LDA_可视化_{lda_html_id}",
                "type": "html",
                "file_path": lda_html_path,
                "size": os.path.getsize(lda_html_path)
            })
            
            lda_result = {"topics": topics, "vis_path": lda_html_path}
        except Exception as e:
            pass

    # WordCloud
    if generate_wordcloud and tfidf_result:
        update_progress(90.0, "生成词云图...")
        text_for_cloud = " ".join([item["word"] for item in tfidf_result])
        if text_for_cloud:
            font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
            if not os.path.exists(font_path):
                font_path = None

            # 支持遮罩掩码 (mask) 若 config 提供了 mask 路径
            mask = None
            mask_path = config.get("mask_path")
            if mask_path and os.path.exists(mask_path):
                from PIL import Image
                mask = np.array(Image.open(mask_path))

            wc = WordCloud(
                font_path=font_path,
                width=800,
                height=600,
                background_color="white",
                max_words=100,
                mask=mask,
                contour_width=3 if mask is not None else 0,
                contour_color='steelblue' if mask is not None else None
            ).generate_from_frequencies({item["word"]: item["score"] for item in tfidf_result})
            
            wc_id = str(uuid.uuid4())
            wc_path = os.path.join(artifacts_dir, f"wordcloud_{wc_id}.png")
            wc.to_file(wc_path)
            
            artifacts.append({
                "name": f"词云图_{wc_id}",
                "type": "png",
                "file_path": wc_path,
                "size": os.path.getsize(wc_path)
            })

    update_progress(100.0, "情感分析完成")
    return {
        "message": "情感分析完成",
        "artifacts": artifacts,
        "tfidf": tfidf_result,
        "lda": lda_result
    }

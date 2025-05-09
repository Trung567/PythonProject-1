import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import seaborn as sns
import os

def identify_statistic_columns_for_clustering(df, exclude_cols=None):
    if exclude_cols is None:
        exclude_cols = ['Player', 'Nation', 'Squad', 'Position', 'Team']
    potential_stat_cols = []
    for col in df.columns:
        if col not in exclude_cols:
            try:
                if pd.api.types.is_numeric_dtype(df[col]):
                    if df[col].nunique(dropna=True) > 1:
                        potential_stat_cols.append(col)
            except Exception:
                continue
    return potential_stat_cols

def clean_and_convert_to_numeric(df, stat_cols):
    df_cleaned = df.copy()
    for col in stat_cols:
        if df_cleaned[col].dtype == 'object':
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace('%', '', regex=False)
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        elif not pd.api.types.is_numeric_dtype(df_cleaned[col]):
             df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
    return df_cleaned

def main_exercise_3():
    output_dir_bai3 = "bai3_results"
    if not os.path.exists(output_dir_bai3):
        os.makedirs(output_dir_bai3)
    try:
        df_input = pd.read_csv("results.csv", na_values=["N/a", "NaN", "", " ", "NA"])
    except FileNotFoundError:
        print("Lỗi: File 'results.csv' không tìm thấy.")
        return
    except Exception as e:
        print(f"Lỗi khi đọc file 'results.csv': {e}")
        return
    if df_input.empty:
        print("Lỗi: File 'results.csv' rỗng.")
        return

    player_info_df = df_input[['Player', 'Team' if 'Team' in df_input.columns else 'Squad']].copy()

    stat_cols_for_clustering = identify_statistic_columns_for_clustering(df_input)
    if not stat_cols_for_clustering:
        print("Không xác định được cột thống kê nào phù hợp cho clustering.")
        return
    
    df_stats = df_input[stat_cols_for_clustering].copy()
    df_stats = clean_and_convert_to_numeric(df_stats, stat_cols_for_clustering)
    imputer = SimpleImputer(strategy='mean')
    df_imputed = imputer.fit_transform(df_stats)
    df_processed = pd.DataFrame(df_imputed, columns=df_stats.columns, index=df_stats.index)
    scaler = StandardScaler()
    df_scaled = scaler.fit_transform(df_processed)
    df_scaled = pd.DataFrame(df_scaled, columns=df_processed.columns, index=df_processed.index)

    wcss = []
    k_range = range(2, 11)
    for i in k_range:
        kmeans_elbow = KMeans(n_clusters=i, init='k-means++', n_init='auto', random_state=42)
        kmeans_elbow.fit(df_scaled)
        wcss.append(kmeans_elbow.inertia_)
    
    plt.figure(figsize=(10, 6))
    plt.plot(k_range, wcss, marker='o', linestyle='--')
    plt.title('Phương pháp Elbow để xác định k tối ưu')
    plt.xlabel('Số lượng nhóm (k)')
    plt.ylabel('WCSS (Inertia)')
    plt.xticks(list(k_range))
    elbow_plot_path = os.path.join(output_dir_bai3, "kmeans_elbow_plot.png")
    plt.savefig(elbow_plot_path)
    plt.close()
    print(f"Đã lưu biểu đồ Elbow")

    silhouette_scores = []
    for i in k_range:
        kmeans_silhouette = KMeans(n_clusters=i, init='k-means++', n_init='auto', random_state=42)
        cluster_labels = kmeans_silhouette.fit_predict(df_scaled)
        try:
            silhouette_avg = silhouette_score(df_scaled, cluster_labels)
            silhouette_scores.append(silhouette_avg)
        except ValueError:
            silhouette_scores.append(-1)
            
    plt.figure(figsize=(10, 6))
    plt.plot(k_range, silhouette_scores, marker='o', linestyle='--')
    plt.title('Phân tích Silhouette để xác định k tối ưu')
    plt.xlabel('Số lượng nhóm (k)')
    plt.ylabel('Silhouette Score Trung bình')
    plt.xticks(list(k_range))
    silhouette_plot_path = os.path.join(output_dir_bai3, "kmeans_silhouette_plot.png")
    plt.savefig(silhouette_plot_path)
    plt.close()
    print(f"Đã lưu biểu đồ Silhouette")

    optimal_k_silhouette = -1
    if any(score > -1 for score in silhouette_scores): # Check if there are valid scores
        best_silhouette_score = max(s for s in silhouette_scores if s > -1)
        optimal_k_silhouette = list(k_range)[silhouette_scores.index(best_silhouette_score)]
    else:
        print("Không thể tính toán Silhouette Score hợp lệ cho các giá trị k đã thử.")
        print("Vui lòng chọn k dựa trên biểu đồ Elbow hoặc kiến thức chuyên môn.")

    chosen_k = optimal_k_silhouette if optimal_k_silhouette > 1 else 3 
    kmeans = KMeans(n_clusters=chosen_k, init='k-means++', n_init='auto', random_state=42)
    cluster_labels = kmeans.fit_predict(df_scaled)
    df_results_with_clusters = df_input.loc[df_scaled.index].copy()
    df_results_with_clusters['Cluster'] = cluster_labels
    cluster_analysis_df = df_processed.copy()
    cluster_analysis_df['Cluster'] = cluster_labels
    cluster_summary = cluster_analysis_df.groupby('Cluster')[stat_cols_for_clustering].mean().round(2)
    pca = PCA(n_components=2, random_state=42)
    df_pca = pca.fit_transform(df_scaled)
    df_pca_plot = pd.DataFrame(data=df_pca, columns=['Principal Component 1', 'Principal Component 2'])
    df_pca_plot['Cluster'] = cluster_labels

    plt.figure(figsize=(12, 8))
    sns.scatterplot(
        x="Principal Component 1", y="Principal Component 2",
        hue="Cluster",
        palette=sns.color_palette("hsv", chosen_k),
        data=df_pca_plot,
        legend="full",
        alpha=0.7
    )
    plt.title(f'Biểu đồ phân cụm cầu thủ 2D sử dụng PCA và K-means')
    plt.xlabel('Principal Component 1')
    plt.ylabel('Principal Component 2')
    pca_plot_path = os.path.join(output_dir_bai3, "pca_kmeans_2d_plot.png")
    plt.savefig(pca_plot_path)
    plt.close()
    print(f"Đã lưu biểu đồ PCA 2D")

    print("\n✅ Lưu thành công dữ liệu")
if __name__ == '__main__':
    main_exercise_3()
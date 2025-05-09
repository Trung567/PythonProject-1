import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


def identify_statistic_columns(df, exclude_cols=None):
    if exclude_cols is None:
        exclude_cols = ['Player', 'Nation', 'Team', 'Squad', 'Position']
    potential_stat_cols = []
    for col in df.columns:
        if col not in exclude_cols:
            try:
                numeric_col = pd.to_numeric(df[col].astype(str).str.replace('%', '', regex=False), errors='coerce')
                if numeric_col.notna().sum() > len(df) / 2:
                    potential_stat_cols.append(col)
            except:
                continue
    return potential_stat_cols

def clean_numeric_column(series):
    series_str = series.astype(str).str.replace('%', '', regex=False).str.strip()
    series_str.replace(['', 'N/a', 'NaN', 'nan', 'None'], np.nan, inplace=True)
    return pd.to_numeric(series_str, errors='coerce')

def main_exercise_2():
    
    # --- 0. Đọc dữ liệu từ Bài 1 ---
    
    try:
        df = pd.read_csv("results.csv", na_values=["N/a", "NaN", "", " "])
    except FileNotFoundError:
        print("Lỗi: File 'results.csv' không tìm thấy.")
        return
    except Exception as e:
        print(f"Lỗi khi đọc file 'results.csv': {e}")
        return

    if df.empty:
        print("Lỗi: File 'results.csv' rỗng.")
        return
    team_column_name = 'Team' if 'Team' in df.columns else 'Squad'
    if team_column_name not in df.columns:
        print(f"Lỗi: Không tìm thấy cột đội bóng trong results.csv.")
        return
    stat_cols_to_analyze = identify_statistic_columns(df, exclude_cols=['Player', 'Nation', team_column_name, 'Position'])
    
    if not stat_cols_to_analyze:
        print("Không xác định được cột thống kê nào để phân tích.")
        return
    for col in stat_cols_to_analyze:
        df[col] = clean_numeric_column(df[col])

    if not os.path.exists("bai2_results"):
        os.makedirs("bai2_results")
    if not os.path.exists("bai2_results/histograms"):
        os.makedirs("bai2_results/histograms")

    # --- 1. Top 3 cầu thủ Cao nhất/Thấp nhất cho mỗi chỉ số ---
    
    try:
        with open("bai2_results/top_3.txt", "w", encoding="utf-8") as f_top3:
            for stat in stat_cols_to_analyze:
                df_stat_cleaned = df[['Player', stat]].copy() 
                df_stat_cleaned.dropna(subset=[stat], inplace=True) 

                if df_stat_cleaned.empty:
                    f_top3.write(f"\n--- Chỉ số: {stat} ---\n")
                    f_top3.write("Không có đủ dữ liệu cầu thủ hợp lệ.\n")
                    continue
                df_sorted_highest = df_stat_cleaned.sort_values(by=stat, ascending=False)
                df_sorted_lowest = df_stat_cleaned.sort_values(by=stat, ascending=True)

                f_top3.write(f"\n--- Chỉ số: {stat} ---\n")
                f_top3.write("\nTop 3 Cao nhất:\n")
                for i, row in df_sorted_highest.head(3).iterrows():
                    f_top3.write(f"  {row['Player']}: {row[stat]:.2f}\n")
                
                f_top3.write("Top 3 Thấp nhất:\n")
                for i, row in df_sorted_lowest.head(3).iterrows():
                    f_top3.write(f"  {row['Player']}: {row[stat]:.2f}\n")
        print("Hoàn thành: top_3.txt đã được tạo.")
    except Exception as e:
        print(f"Lỗi khi tạo file top_3.txt: {e}")

    # --- 2. Median, Mean, Standard Deviation (lưu vào results2.csv) ---
    
    results2_data = []
    all_players_stats = {"Group": "all"}
    for stat in stat_cols_to_analyze:
        all_players_stats[f"Median of {stat}"] = round (df[stat].median(), 2)
        all_players_stats[f"Mean of {stat}"] = round (df[stat].mean(), 2)
        all_players_stats[f"Std of {stat}"] = round (df[stat].std(), 2)
    results2_data.append(all_players_stats)

    teams = df[team_column_name].unique()
    for team in teams:
        if pd.isna(team): continue
        df_team = df[df[team_column_name] == team]
        team_stats = {"Group": team}
        for stat in stat_cols_to_analyze:
            team_stats[f"Median of {stat}"] = round (df_team[stat].median(), 2)
            team_stats[f"Mean of {stat}"] = round (df_team[stat].mean(), 2)
            team_stats[f"Std of {stat}"] = round (df_team[stat].std(), 2)
        results2_data.append(team_stats)

    df_results2 = pd.DataFrame(results2_data)
    try:
        df_results2.to_csv("bai2_results/results2.csv", index=False, encoding="utf-8-sig")
        print("Hoàn thành: results2.csv đã được tạo.")
    except Exception as e:
        print(f"Lỗi khi tạo file results2.csv: {e}")

    # --- 3. Vẽ Biểu đồ Histogram ---
    
    for stat in stat_cols_to_analyze:
        plt.figure(figsize=(10, 6))
        df[stat].dropna().plot(kind='hist', bins=20, alpha=0.7, label='All Players', density=True)
        plt.title(f"Phân bổ của chỉ số: {stat} (Toàn bộ cầu thủ)")
        plt.xlabel(stat)
        plt.ylabel("Tần suất (chuẩn hóa)")
        plt.legend()
        try:
            plt.savefig(f"bai2_results/histograms/hist_all_players_{stat.replace(':', '').replace('/', '_')}.png")
        except Exception as e:
            print(f"Lỗi khi lưu histogram (chỉ số {stat}): {e}")
        plt.close()
    print("Hoàn thành: Biểu đồ Histogram đã được tạo.")

    # --- 4. Xác định Đội có Điểm số Cao nhất & Phân tích Đội xuất sắc nhất ---
    
    highest_scoring_teams_summary = []
    for stat in stat_cols_to_analyze:
        if df[stat].dropna().empty: continue
        try:
            team_mean_stat = df.groupby(team_column_name)[stat].mean().sort_values(ascending=False)
            if not team_mean_stat.empty:
                top_team_for_stat = team_mean_stat.index[0]
                top_score_for_stat = team_mean_stat.iloc[0]
                highest_scoring_teams_summary.append(f"Chỉ số '{stat}': Đội cao nhất là {top_team_for_stat} (Trung bình: {top_score_for_stat:.2f})")
        except Exception as e:
            highest_scoring_teams_summary.append(f"Chỉ số '{stat}': Lỗi khi tính toán ({e})")

    try:
        with open("bai2_results/top_3.txt", "a", encoding="utf-8") as f_top3:
            f_top3.write("\n\n\n--- TÓM TẮT ĐỘI CÓ ĐIỂM SỐ TRUNG BÌNH CAO NHẤT CHO MỖI CHỈ SỐ ---\n\n")
            for summary_line in highest_scoring_teams_summary:
                f_top3.write(summary_line + "\n")
    except Exception as e:
        print(f"Lỗi khi ghi tóm tắt đội điểm cao nhất: {e}")  
        
    print("\n✅ Lưu thành công dữ liệu")

if __name__ == '__main__':
    main_exercise_2()
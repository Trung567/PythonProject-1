from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup, Comment
import pandas as pd
import time
import re

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36'

URL_CONFIG = {
    "standard": {"url": "https://fbref.com/en/comps/9/stats/Premier-League-Stats", "table_id": "stats_standard"},
    "keepers": {"url": "https://fbref.com/en/comps/9/keepers/Premier-League-Stats", "table_id": "stats_keepers"},
    "shooting": {"url": "https://fbref.com/en/comps/9/shooting/Premier-League-Stats", "table_id": "stats_shooting"},
    "passing": {"url": "https://fbref.com/en/comps/9/passing/Premier-League-Stats", "table_id": "stats_passing"},
    "passing_types": {"url": "https://fbref.com/en/comps/9/passing_types/Premier-League-Stats", "table_id": "stats_passing_types"},
    "gca": {"url": "https://fbref.com/en/comps/9/gca/Premier-League-Stats", "table_id": "stats_gca"},
    "defense": {"url": "https://fbref.com/en/comps/9/defense/Premier-League-Stats", "table_id": "stats_defense"},
    "possession": {"url": "https://fbref.com/en/comps/9/possession/Premier-League-Stats", "table_id": "stats_possession"},
    "misc": {"url": "https://fbref.com/en/comps/9/misc/Premier-League-Stats", "table_id": "stats_misc"},
}

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-agent={USER_AGENT}')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception as e:
        print(f"Lỗi khi khởi tạo ChromeDriver với webdriver_manager: {e}") # Giữ lại lỗi nghiêm trọng
        raise
    return driver

def get_page_source_with_selenium(url, driver, table_id_hint):
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"div#div_{table_id_hint} table, table#{table_id_hint}"))
        )
    except Exception as e:
        pass
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)
    return driver.page_source

def extract_table_from_html_fbref(html_content, table_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    table_html = None
    comment = soup.find(string=lambda text: isinstance(text, Comment) and f'id="{table_id}"' in text)
    if comment:
        table_html = BeautifulSoup(comment.string, 'html.parser')
    else:
        table_html = soup
    table = table_html.find("table", {"id": table_id})
    if not table:
        return pd.DataFrame()
    data_rows = []
    for row in table.find("tbody").find_all("tr"):
        if row.has_attr('class') and ('thead' in row['class'] or \
                                      any(cls.startswith('spacer_') for cls in row['class'])):
            continue
        if not row.find_all(['th', 'td'], recursive=False):
            continue
        player_row_data = {}
        all_cells_in_row = row.find_all(['th', 'td'])
        for cell in all_cells_in_row:
            stat_name = cell.get('data-stat', None)
            if stat_name:
                stat_value = cell.get_text(strip=True)
                player_row_data[stat_name] = stat_value
        if "player" in player_row_data and player_row_data["player"]:
            data_rows.append(player_row_data)
    df = pd.DataFrame(data_rows)
    return df

FBREF_TO_CSV_COLUMN_MAP = {
    'player': 'Player', 'nationality': 'Nation', 'team': 'Squad', 'position': 'Position',
    'age': 'Age', 'minutes': 'Minutes', 'games': 'Matches played', 'games_starts': 'Starts',
    'goals': 'Goals', 'assists': 'Assists', 'cards_yellow': 'Yellow cards', 'cards_red': 'Red cards',
    'xg': 'Expected: xG', 'xg_assist': 'Expected: xAG',
    'progressive_carries': 'Progression: PrgC', 'progressive_passes': 'Progression: PrgP', 'progressive_passes_received': 'Progression: PrgR',
    'goals_per90': 'Per 90: Gls', 'assists_per90': 'Per 90: Ast', 'xg_per90': 'Per 90: xG',
    'gk_xg_against_per90': 'Per 90: xGA',
    'gk_goals_against_per90': 'Performance: GA90', 'gk_save_pct': 'Performance: Save%', 'gk_clean_sheets_pct': 'Performance: CS%', 'gk_pens_save_pct': 'Penalty Kicks: Save%',
    'shots_on_target_pct': 'Standard: SoT%', 'shots_on_target_per90': 'Standard: SoT/90', 'goals_per_shot': 'Standard: G/Sh', 'average_shot_distance': 'Standard: Dist',
    'passes_completed': 'Total: Cmp', 'passes_pct': 'Total: Cmp%', 'passes_progressive_distance': 'Total: TotDist',
    'passes_pct_short': 'Short: Cmp%', 'passes_pct_medium': 'Medium: Cmp%', 'passes_pct_long': 'Long: Cmp%',
    'assisted_shots': 'Expected: KP', 'passes_into_final_third': 'Expected: 1/3', 'passes_into_penalty_area': 'Expected: PPA', 'crosses_into_penalty_area': 'Expected: CrsPA',
    'sca': 'SCA', 'sca_per90': 'SCA90', 'gca': 'GCA', 'gca_per90': 'GCA90',
    'tackles': 'Tackles: Tkl', 'tackles_won': 'Tackles: TklW',
    'challenges_attempted': 'Challenges: Att', 'challenges_lost': 'Challenges: Lost',
    'blocks': 'Blocks: Blocks', 'blocked_shots': 'Blocks: Sh', 'blocked_passes': 'Blocks: Pass', 'interceptions': 'Blocks: Int',
    'touches': 'Touches: Touches', 'touches_def_pen_area': 'Touches: Def Pen', 'touches_def_3rd': 'Touches: Def 3rd',
    'touches_mid_3rd': 'Touches: Mid 3rd', 'touches_att_3rd': 'Touches Att 3rd', 'touches_att_pen_area': 'Touches Att Pen',
    'take_ons_attempted': 'TakeOns: Att', 'take_ons_successful_pct': 'TakeOns: Succ%', 'take_ons_tackled_pct': 'TakeOns: Tkld%',
    'carries': 'Carries: Carries', 'carries_progressive_distance': 'Carries: PrgDist',
    'carries_into_final_third': 'Carries: 1/3', 'carries_into_penalty_area': 'Carries: CPA',
    'carries_miscontrols': 'Carries: Mis', 'carries_dispossessed': 'Carries: Dis',
    'passes_received': 'Receiving: Rec', 'fouls': 'Performance: Fls', 'fouled': 'Performance: Fld', 'offsides': 'Performance: Off', 'crosses': 'Performance: Crs', 'ball_recoveries': 'Performance: Recov',
    'aerials_won': 'Aerials: Won', 'aerials_lost': 'Aerials: Lost', 'aerials_won_pct': 'Aerials: Won%'
}

if __name__ == "__main__":
    driver = None
    all_dataframes = {}
    try:
        driver = get_driver()
        for stat_category, config in URL_CONFIG.items():
            url = config["url"]
            table_id = config["table_id"]
            html_source = get_page_source_with_selenium(url, driver, table_id)
            df_table = extract_table_from_html_fbref(html_source, table_id)
            if not df_table.empty:
                all_dataframes[stat_category] = df_table
            time.sleep(1)
    finally:
        if driver:
            driver.quit()
    if not all_dataframes:
        print("Không trích xuất được dữ liệu nào. Kết thúc chương trình.") 
        exit()
    final_df = all_dataframes.get("standard", pd.DataFrame()).copy()
    if final_df.empty:
        print("Bảng 'standard' không có dữ liệu hoặc không được trích xuất, không thể tiếp tục.") 
        exit()
    if 'player' not in final_df.columns:
        print("Cột 'player' (tên cầu thủ gốc) không tồn tại trong bảng 'standard'. Kiểm tra lại quá trình trích xuất.")
        exit()
    
    identity_cols_from_standard = ['nationality', 'position', 'team', 'age', 'games', 'games_starts', 'minutes']
    for stat_category, df_to_merge in all_dataframes.items():
        if stat_category == "standard":
            continue
        if df_to_merge.empty:
            continue
        if 'player' not in df_to_merge.columns:
            continue  
        cols_to_bring_from_secondary_table = ['player']
        for col in df_to_merge.columns:
            if col != 'player' and col not in identity_cols_from_standard:
                cols_to_bring_from_secondary_table.append(col)
        seen_merge_cols = set()
        unique_cols_to_bring = [x for x in cols_to_bring_from_secondary_table if not (x in seen_merge_cols or seen_merge_cols.add(x))]
        if not unique_cols_to_bring or 'player' not in unique_cols_to_bring :
             continue
        df_to_merge_subset = df_to_merge[unique_cols_to_bring].copy()
        final_df = pd.merge(final_df, df_to_merge_subset, on="player", how="left", suffixes=('', f'_{stat_category}_dup'))
    
    raw_minutes_col = 'minutes'
    if raw_minutes_col in final_df.columns and 'player' in final_df.columns:
        final_df['temp_minutes_numeric'] = final_df[raw_minutes_col].astype(str).str.replace(',', '', regex=False)
        final_df['temp_minutes_numeric'] = pd.to_numeric(final_df['temp_minutes_numeric'], errors='coerce')
        final_df.sort_values(['player', 'temp_minutes_numeric'], ascending=[True, False], inplace=True)
        final_df.drop_duplicates(subset=['player'], keep='first', inplace=True)
        final_df.drop(columns=['temp_minutes_numeric'], inplace=True)
    elif 'player' in final_df.columns:
        final_df.drop_duplicates(subset=['player'], keep='first', inplace=True)  
    
    cols_to_rename = {fbref_col: csv_col for fbref_col, csv_col in FBREF_TO_CSV_COLUMN_MAP.items() if fbref_col in final_df.columns}
    final_df.rename(columns=cols_to_rename, inplace=True)
    if 'Nation' in final_df.columns:
        def extract_nation_code(nation_text):
            if isinstance(nation_text, str):
                match = re.search(r'([A-Z]+)$', nation_text)
                if match: return match.group(1)
                if len(nation_text) == 3 and nation_text.isupper(): return nation_text
            return nation_text 
        final_df['Nation'] = final_df['Nation'].apply(extract_nation_code)

    if 'Age' in final_df.columns:
        final_df['Age'] = final_df['Age'].astype(str).apply(
            lambda x: x.split('-')[0] if isinstance(x, str) and '-' in x else x
        )
    if 'Minutes' in final_df.columns:
        final_df['Minutes_temp_filter'] = final_df['Minutes'].astype(str).str.replace(',', '', regex=False)
        final_df['Minutes_temp_filter'] = pd.to_numeric(final_df['Minutes_temp_filter'], errors='coerce')
        final_df.dropna(subset=['Minutes_temp_filter'], inplace=True)
        final_df = final_df[final_df['Minutes_temp_filter'] > 90].copy()
        final_df.drop(columns=['Minutes_temp_filter'], inplace=True)
    if 'Player' in final_df.columns and not final_df.empty:
        try:
            final_df['FirstNameTemp'] = final_df['Player'].astype(str).apply(
                lambda x: x.split(' ')[0] if x and ' ' in x else (x if x else "N/A_Player")
            )
            final_df.sort_values(by='FirstNameTemp', ascending=True, inplace=True)
            final_df.drop(columns=['FirstNameTemp'], inplace=True)
        except Exception as e:
            pass
        
    output_column_order_from_map = ['Player'] + [col for col in FBREF_TO_CSV_COLUMN_MAP.values() if col != 'Player']
    seen_cols_output = set()
    final_ordered_columns = []
    for col in output_column_order_from_map:
        if col not in seen_cols_output:
            final_ordered_columns.append(col)
            seen_cols_output.add(col)
            
    results_df_cols_dict = {}
    df_index = final_df.index if not final_df.empty else None
    for col_name in final_ordered_columns:
        if col_name in final_df.columns:
            results_df_cols_dict[col_name] = final_df[col_name]
        else:
            results_df_cols_dict[col_name] = pd.Series(["N/a"] * len(final_df), name=col_name, index=df_index) if not final_df.empty else "N/a"
            
    if not final_df.empty or any(isinstance(v, pd.Series) for v in results_df_cols_dict.values()):
        results_df = pd.DataFrame(results_df_cols_dict)
        existing_ordered_columns = [col for col in final_ordered_columns if col in results_df.columns]
        if existing_ordered_columns:
             results_df = results_df[existing_ordered_columns]
    else:
        results_df = pd.DataFrame(columns=final_ordered_columns)
        if all(isinstance(v, str) and v == "N/a" for v in results_df_cols_dict.values()) and results_df_cols_dict:
             temp_data = {col: ["N/a"] for col in final_ordered_columns}
             results_df = pd.DataFrame(temp_data)

    results_df.fillna("N/a", inplace=True)
    for col in results_df.columns:
        results_df[col] = results_df[col].apply(lambda x: "N/a" if str(x).strip() == "" else x)
    try:
        results_df.to_csv("results.csv", index=False, encoding='utf-8-sig')
        print("✅ Lưu thành công dữ liệu")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file: {e}")

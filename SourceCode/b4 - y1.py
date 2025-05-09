from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36'
TRANSFER_BASE_URL = "https://www.footballtransfers.com/en/players/uk-premier-league"

URLS_TO_SCRAPE = [
    "https://www.footballtransfers.com/en/players/uk-premier-league"
] + [f"https://www.footballtransfers.com/en/players/uk-premier-league/{i}" for i in range(2, 23)]


def get_driver():
    chrome_options = Options()
    chrome_options.add_argument(f'user-agent={USER_AGENT}')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = Service(ChromeDriverManager().install(), service_args=['--log-level=OFF'])
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception as e:
        print(f"Lỗi khi khởi tạo ChromeDriver với webdriver_manager: {e}")
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e_fallback:
            raise
    return driver

def get_page_source_with_selenium_and_wait(driver, url, wait_selector_css):
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector_css))
        )
    except Exception as e:
        print(f"⚠️ Timeout hoặc không tìm thấy element. Lỗi: {e}")
        return None 
    return driver.page_source

def extract_data_using_confirmed_selectors(html_content, url_for_logging=""):
    soup = BeautifulSoup(html_content, 'html.parser')
    players_data = []

    table_class_confirmed = 'table table-hover no-cursor table-striped leaguetable mvp-table similar-players-table mb-0'
    table = soup.find('table', class_=table_class_confirmed)

    if not table:
        print(f"  Cảnh báo: Không tìm thấy bảng với class '{table_class_confirmed}' trên trang được phân tích (URL: {url_for_logging}).")
        return players_data 

    tbody = table.find('tbody')
    if not tbody:
        print(f"  Cảnh báo: Không tìm thấy tbody trong bảng trên trang (URL: {url_for_logging}).")
        return players_data

    rows = tbody.find_all('tr')
    print(f"  Phân tích {len(rows)} hàng từ bảng (URL: {url_for_logging}).")

    for i, row_html in enumerate(rows):
        try:
            skill_div = row_html.find('div', class_='table-skill__skill')
            pot_div = row_html.find('div', class_='table-skill__pot')
            skill_text = skill_div.text.strip() if skill_div and skill_div.text else None
            pot_text = pot_div.text.strip() if pot_div and pot_div.text else None
            
            skill_pot_value = "N/A" 
            if skill_text and pot_text:
                try:
                    skill_val = float(skill_text)
                    pot_val = float(pot_text)
                    skill_pot_value = f"{skill_val}/{pot_val}"
                except ValueError:
                    pass 

            player_span = row_html.find('span', class_='d-none')
            player_name_val = player_span.text.strip() if player_span and player_span.text else None
            
            team_span = row_html.find('span', class_='td-team__teamname')
            team_name_val = team_span.text.strip() if team_span and team_span.text else None
            
            etv_span = row_html.find('span', class_='player-tag')
            etv_value_val = etv_span.text.strip() if etv_span and etv_span.text else None
            
            if player_name_val: 
                players_data.append({
                    "Player": player_name_val,
                    "Team": team_name_val,
                    "ETV": etv_value_val,
                    "Skill/Pot": skill_pot_value
                })
        except Exception as e:
            print(f"    Lỗi khi xử lý hàng {i+1} (URL: {url_for_logging}): {e}")
            continue
            
    return players_data

def normalize_player_name(name):
    if pd.isna(name) or name is None:
        return ""
    return str(name).lower().strip()

if __name__ == "__main__":
    try:
        df_results1 = pd.read_csv("results.csv", na_filter=False)
    except FileNotFoundError:
        print("❌ Lỗi: File 'results.csv' không tìm thấy. Hãy đảm bảo bạn đã chạy Bài 1 thành công.")
        exit()
    except Exception as e:
        print(f"❌ Lỗi khi đọc 'results.csv': {e}")
        exit()

    if 'Minutes' not in df_results1.columns or 'Player' not in df_results1.columns:
        print("❌ Lỗi: File 'results.csv' phải có cột 'Minutes' và 'Player'.")
        exit()

    df_results1['Minutes_Numeric'] = df_results1['Minutes'].astype(str).str.replace(',', '', regex=False)
    df_results1['Minutes_Numeric'] = df_results1['Minutes_Numeric'].replace(['N/a', ''], pd.NA) 
    df_results1['Minutes_Numeric'] = pd.to_numeric(df_results1['Minutes_Numeric'], errors='coerce')
    df_results1.dropna(subset=['Minutes_Numeric'], inplace=True)

    players_over_900_min_df = df_results1[df_results1['Minutes_Numeric'] > 900].copy() 
    
    if players_over_900_min_df.empty:
        print("Thông báo: Không tìm thấy cầu thủ nào thi đấu trên 900 phút trong 'results.csv'. Kết thúc.")
        exit()

    players_over_900_min_df['Player_Normalized_Results'] = players_over_900_min_df['Player'].apply(normalize_player_name)
    set_players_over_900_min_normalized = set(players_over_900_min_df['Player_Normalized_Results'])
    
    print(f"Thông tin: Đã xác định {len(set_players_over_900_min_normalized)} cầu thủ thi đấu > 900 phút từ results.csv.")

    active_driver = None
    all_scraped_data_dfs = []
    wait_for_table_selector = "table.mvp-table" 

    try:
        active_driver = get_driver()
        print(f"\nThông tin: Bắt đầu cào dữ liệu từ {len(URLS_TO_SCRAPE)} trang trên footballtransfers.com...")
        
        for page_idx, current_page_url in enumerate(URLS_TO_SCRAPE, 1):
            html_source = get_page_source_with_selenium_and_wait(active_driver, current_page_url, wait_for_table_selector)
            
            if html_source:
                df_page_transfer_data = extract_data_using_confirmed_selectors(html_source, current_page_url)
                if df_page_transfer_data: 
                    all_scraped_data_dfs.extend(df_page_transfer_data) 
                    print(f"  Trang {page_idx}: Trích xuất được {len(df_page_transfer_data)} mục.")
                else:
                    print(f"  Trang {page_idx}: Không trích xuất được dữ liệu nào từ HTML.")
            else:
                print(f"  Trang {page_idx}: Không lấy được HTML source.")
            time.sleep(1) 

    except Exception as e:
        print(f"LỖI nghiêm trọng đã xảy ra trong quá trình cào dữ liệu: {e}")
    finally:
        if active_driver:
            active_driver.quit()

    if not all_scraped_data_dfs:
        print("Thông báo: Không thu thập được dữ liệu nào từ footballtransfers.com. Kết thúc.")
        exit()

    df_all_transfers_raw = pd.DataFrame(all_scraped_data_dfs)
    
    if df_all_transfers_raw.empty: 
        print("Thông báo: DataFrame thô rỗng sau khi thu thập. Kết thúc.")
        exit()

    df_all_transfers_raw.drop_duplicates(subset=['Player'], keep='first', inplace=True)

    if df_all_transfers_raw.empty:
        print("Thông báo: Không có dữ liệu thô nào sau khi xử lý trùng lặp. Kết thúc.")
        exit()

    df_all_transfers_raw['Player_Normalized_FT'] = df_all_transfers_raw['Player'].apply(normalize_player_name)
    
    df_final_filtered_data = df_all_transfers_raw[
        df_all_transfers_raw['Player_Normalized_FT'].isin(set_players_over_900_min_normalized)
    ].copy() 

    output_csv_file = "player_transfer_values.csv"

    if df_final_filtered_data.empty:
        print(f"CẢNH BÁO: Không tìm thấy thông tin chuyển nhượng cho các cầu thủ đã lọc (>900 phút). File '{output_csv_file}' sẽ không được tạo hoặc sẽ rỗng.")
    else:
        print(f"Thông tin: Đã lọc được {len(df_final_filtered_data)} mục cho các cầu thủ thi đấu > 900 phút.")

        player_name_map_df = players_over_900_min_df[['Player', 'Player_Normalized_Results']].drop_duplicates(subset=['Player_Normalized_Results'])
        
        df_merged_data = pd.merge(
            df_final_filtered_data,
            player_name_map_df,
            left_on='Player_Normalized_FT',
            right_on='Player_Normalized_Results',
            how='left',
            suffixes=('_FT', '_Results')
        )
        
        df_merged_data['Player'] = df_merged_data['Player_Results'].fillna(df_merged_data['Player_FT'])

        columns_to_save_in_csv = ['Player', 'Team', 'ETV', 'Skill/Pot']
        
        df_to_save = df_merged_data[columns_to_save_in_csv].copy()
        
        if not df_to_save.empty:
            try:
                df_to_save.to_csv(output_csv_file, index=False, encoding='utf-8-sig')
                print(f"✅ Đã lưu thành công dữ liệu.")
            except Exception as e:
                print(f"❌ Lỗi khi lưu file: {e}")
        else:
            print(f"Thông báo: DataFrame df_to_save rỗng, không có dữ liệu để lưu.")
    
    if df_final_filtered_data.empty: 
         print(f"\nLưu ý cuối cùng: Vì không có dữ liệu nào được lọc cho cầu thủ > 900 phút, file '{output_csv_file}' có thể không được tạo hoặc sẽ rỗng.")



import flet as ft
import requests
import sqlite3
import os
from datetime import datetime

class WeatherApp(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.expand = True
        
        self.db_path = "weather_app.db"
        self.area_url = "http://www.jma.go.jp/bosai/common/const/area.json"
        self.forecast_base_url = "https://www.jma.go.jp/bosai/forecast/data/forecast/"

        self.init_database()

        self.region_list = ft.ListView(expand=True, spacing=2)
        self.weather_grid = ft.GridView(
            expand=True,
            runs_count=5,
            max_extent=200,
            child_aspect_ratio=0.8,
            spacing=10,
            run_spacing=10,
        )
        self.header_text = ft.Text("地域を選択してください", size=24, weight="bold")

        self.content = ft.Row(
            controls=[
                ft.Container(
                    width=300,
                    bgcolor=ft.Colors.BLUE_GREY_50,
                    content=ft.Column([
                        ft.Container(ft.Text("地域選択", size=20, weight="bold"), padding=10),
                        self.region_list
                    ], expand=True)
                ),
                ft.VerticalDivider(width=1),
                ft.Column(
                    expand=True,
                    controls=[
                        ft.Container(content=self.header_text, padding=20),
                        ft.Container(content=self.weather_grid, expand=True, padding=20)
                    ]
                )                
            ],
            expand=True,
        )

    def init_database(self):
        """データベースとテーブルを作成する"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS areas (
                code TEXT PRIMARY KEY,
                name TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area_code TEXT,
                forecast_date TEXT,
                weather_code TEXT,
                weather_text TEXT,
                fetched_at TIMESTAMP,
                FOREIGN KEY (area_code) REFERENCES areas (code)
            )
        """)
        conn.commit()
        conn.close()

    def did_mount(self):
        self.load_areas()

    def load_areas(self):
        """DBからエリア情報を読み込む。空ならAPIから取得してDBに保存する"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT code, name FROM areas")
        rows = cursor.fetchall()

        if not rows:
            self.header_text.value = "エリア情報を更新中..."
            self.page.update()
            self.fetch_areas_from_api()
        else:
            self.build_area_menu(rows)

    def fetch_areas_from_api(self):
        try:
            response = requests.get(self.area_url)
            data = response.json()
            offices = data.get("offices", {})
            
            conn = sqlite3.connect(self.db_path)
            for code, info in offices.items():
                conn.execute("INSERT OR REPLACE INTO areas (code, name) VALUES (?, ?)", 
                             (code, info["name"]))
            conn.commit()
            conn.close()
            
            self.load_areas() 
        except Exception as e:
            print(f"API Error: {e}")

    def build_area_menu(self, area_rows):
        """エリア情報を元にサイドメニューを構築"""
        self.region_list.controls.clear()
        for code, name in area_rows:
            self.region_list.controls.append(
                ft.ListTile(
                    title=ft.Text(name),
                    on_click=self.area_clicked,
                    data={"code": code, "name": name}
                )
            )
        self.header_text.value = "地域を選択してください"
        self.page.update()

    def area_clicked(self, e):
        area_code = e.control.data["code"]
        area_name = e.control.data["name"]
        self.header_text.value = f"{area_name}の天気予報"
        self.update_forecast(area_code)

    def update_forecast(self, area_code):
        """APIから予報を取得しDBに保存した後、DBから最新を表示する"""
        url = f"{self.forecast_base_url}{area_code}.json"
        try:
            response = requests.get(url)
            data = response.json()
            time_series = data[0]["timeSeries"][0]
            time_defines = time_series["timeDefines"]
            weather_area = time_series["areas"][0]
            weather_codes = weather_area["weatherCodes"]
            weathers = weather_area.get("weathers", [])

            conn = sqlite3.connect(self.db_path)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for i, date_str in enumerate(time_defines):
                date_val = date_str.split("T")[0]
                weather_text = weathers[i] if i < len(weathers) else "不明"
                weather_code = weather_codes[i]
                
                conn.execute("""
                    INSERT INTO forecasts (area_code, forecast_date, weather_code, weather_text, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (area_code, date_val, weather_code, weather_text, now))
            
            conn.commit()
            
            self.display_forecast_from_db(area_code)
            conn.close()

        except Exception as e:
            print(f"Error updating forecast: {e}")

    def display_forecast_from_db(self, area_code):
        """DBに格納されている最新の予報データを表示する"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT forecast_date, weather_code, weather_text 
            FROM forecasts 
            WHERE area_code = ? 
            ORDER BY fetched_at DESC, forecast_date ASC 
            LIMIT 3
        """, (area_code,))
        
        rows = cursor.fetchall()
        conn.close()

        self.weather_grid.controls.clear()
        for date_val, w_code, w_text in rows:
            icon_url = f"https://www.jma.go.jp/bosai/forecast/img/{w_code}.png"
            self.weather_grid.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(date_val, weight="bold"),
                        ft.Image(src=icon_url, width=50, height=50),
                        ft.Text(w_text, size=12, text_align="center"),
                    ], alignment="center", horizontal_alignment="center"),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    border_radius=10,
                )
            )
        self.page.update()

def main(page: ft.Page):
    page.title = "天気予報アプリ (DB版)"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0 
    app = WeatherApp(page)
    page.add(app)

ft.app(target=main)
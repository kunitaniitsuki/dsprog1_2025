import flet as ft
import requests

class WeatherApp(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.expand = True
        
        self.area_url = "http://www.jma.go.jp/bosai/common/const/area.json"
        self.forecast_base_url = "https://www.jma.go.jp/bosai/forecast/data/forecast/"

        self.areas = {}

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
 
    def did_mount(self):
        self.fetch_areas()

    def fetch_areas(self):
        try:
            response = requests.get(self.area_url)
            data = response.json()
            offices = data.get("offices", {})
            centers = data.get("centers", {})

            self.region_list.controls.clear()

            for center_code, center_info in centers.items():
                center_name = center_info["name"]
                office_tiles = []

                for office_code in center_info.get("children", []):
                    if office_code in offices:
                        office_name = offices[office_code]["name"]
                        self.areas[office_code] = office_name
                        office_tiles.append(
                            ft.ListTile(
                                title=ft.Text(office_name),
                                on_click=self.area_clicked,
                                data=office_code
                            )
                        )

                expansion_tile = ft.ExpansionTile(
                    title=ft.Text(center_name),
                    controls=office_tiles,
                )
                self.region_list.controls.append(expansion_tile)

            self.page.update()
        
        except Exception as e:
            print(f"Error fetching areas: {e}")
            self.header_text.value = "地域リストの取得に失敗しました"
            self.page.update()

    def area_clicked(self, e):
        code = e.control.data
        area_name = self.areas[code]
        self.header_text.value = f"{area_name}の天気予報"
        self.fetch_forecast(code)

    def fetch_forecast(self, area_code):
        url = f"{self.forecast_base_url}{area_code}.json"
        try:
            response = requests.get(url)
            data = response.json()
            time_series = data[0]["timeSeries"][0]
            time_defines = time_series["timeDefines"]
            weather_area = time_series["areas"][0]
            weather_codes = weather_area["weatherCodes"]
            weathers = weather_area.get("weathers", [])

            self.weather_grid.controls.clear()
            for i, date_str in enumerate(time_defines):
                date_val = date_str.split("T")[0]
                weather_text = weathers[i] if i < len(weathers) else "不明"
                weather_code = weather_codes[i]
                icon_url = f"https://www.jma.go.jp/bosai/forecast/img/{weather_code}.png"

                self.weather_grid.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(date_val, weight="bold"),
                            ft.Image(src=icon_url, width=50, height=50),
                            ft.Text(weather_text, size=12, text_align="center"),
                        ], alignment="center", horizontal_alignment="center"),
                        shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.BLACK12)
                    )
                )
            self.page.update()
        except Exception as e:
            print(f"Error fetching forecast: {e}")

def main(page: ft.Page):
    page.title = "天気予報アプリ"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0 
    app = WeatherApp(page)
    page.add(app)

ft.app(target=main)
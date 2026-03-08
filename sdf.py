import flet as ft
from pathlib import Path
def get_absolute_path(file_name: str) -> str:
    path_object = Path(file_name)
    return str(path_object.resolve())


def main(page: ft.Page):
    async def handle_pick_files(e: ft.Event[ft.Button]):
        files = await ft.FilePicker().pick_files(allow_multiple=True)
        selected_files.value = (
            ", ".join(map(lambda f: f.name, files)) if files else "Cancelled!"
        )
        print(selected_files.value)
        full_path = get_absolute_path("")
        abs_path = f"{full_path}\GeometryDash\{selected_files.value}"
        print(full_path)
        print(abs_path)

        

    
    page.add(
        ft.Row(
            controls=[
                ft.Button(
                    content="Pick files",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=handle_pick_files,
                ),
                selected_files := ft.Text(),
    
            ]
        ),
    
    
    )


ft.run(main)
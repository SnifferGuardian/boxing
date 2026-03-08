from pathlib import Path
file = "data.txt"
def get_absolute_path(file_name: str) -> str:
    path_object = Path(file_name)
    return str(path_object.resolve())

full_path = get_absolute_path("")
abs_path=f"{full_path}\GeometryDash\{selected_files}"
print(f"The absolute path is: {abs_path}")
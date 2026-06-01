import os
import json
import mimetypes
from io import BytesIO
import requests  # pip install requests
from google.oauth2.credentials import Credentials  # Новый импорт для пользовательских токенов
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

def sync_raw_urls_to_drive():
    # 1. Загружаем секретный JSON из переменных окружения GitHub
    creds_raw = os.environ.get("GDRIVE_CREDENTIALS")
    if not creds_raw:
        print("Ошибка: Переменная окружения GDRIVE_CREDENTIALS не найдена.")
        return

    try:
        creds_data = json.loads(creds_raw)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        return

    # 2. Список ваших прямых ссылок на raw-файлы (замените на ваши реальные ссылки)
    URLS = [
        "https://raw.githubusercontent.com/capitainblack/freetm3/refs/heads/main/configs/sub_1.txt",
        "https://raw.githubusercontent.com/capitainblack/freetm3/refs/heads/main/configs/sub_2.txt",
    ]

    # 3. Авторизуемся в Google API от имени вашего пользователя
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    drive_service = build('drive', 'v3', credentials=creds)

    # Точный ID вашей папки на Google Диске
    FOLDER_ID = "1RbHcpoEWUSs8T5QBGSqpOeYjJWJ7_g1h"  

    # 4. Получаем список существующих файлов на Диске
    print("Запрос списка существующих файлов с Google Drive...")
    query = f"'{FOLDER_ID}' in parents and trashed = false"
    try:
        results = drive_service.files().list(q=query, fields="files(id, name)", spaces="drive").execute()
        drive_files_dict = {f['name']: f['id'] for f in results.get('files', [])}
    except Exception as e:
        print(f"Не удалось получить список файлов с Google Drive: {e}")
        return

    # 5. Синхронизируем файлы по ссылкам
    for url in URLS:
        filename = url.split("/")[-1]
        if "?" in filename:
            filename = filename.split("?")[0]

        print(f"\nСкачивание файла: {filename}...")
        
        try:
            file_response = requests.get(url)
            if file_response.status_code != 200:
                print(f"-> Ошибка скачивания {filename}: Статус {file_response.status_code}")
                continue
            file_data = file_response.content
        except Exception as e:
            print(f"-> Не удалось подключиться к URL {url}: {e}")
            continue

        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = 'application/octet-stream'

        fh = BytesIO(file_data)
        media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)

        try:
            if filename in drive_files_dict:
                # Если файл уже есть -> Обновляем (перезаписываем)
                file_id = drive_files_dict[filename]
                print(f"-> Файл найден на Диске (ID: {file_id}). Перезаписываем...")
                drive_service.files().update(fileId=file_id, media_body=media).execute()
                print("-> Успешно обновлено.")
            else:
                # Если файла нет -> Создаем
                print("-> Файл отсутствует на Диске. Создаем...")
                file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
                new_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                print(f"-> Успешно создано (ID: {new_file.get('id')}).")
        except Exception as e:
            print(f"Ошибка взаимодействия с Google Drive для {filename}: {e}")

if __name__ == "__main__":
    sync_raw_urls_to_drive()

import os
import json
import mimetypes
from io import BytesIO
import requests  # pip install requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

def sync_raw_urls_to_drive():
    # 1. Загружаем секретный JSON из переменных окружения
    creds_raw = os.environ.get("GDRIVE_CREDENTIALS")
    if not creds_raw:
        print("Ошибка: Переменная окружения GDRIVE_CREDENTIALS не найдена.")
        return

    try:
        creds_json = json.loads(creds_raw)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        return

    # 2. Список ваших прямых ссылок на raw-файлы
    # Вы можете вставить их прямо сюда или считывать из файла/переменной окружения
    URLS = [
        "https://raw.githubusercontent.com/capitainblack/freetm3/refs/heads/main/configs/sub_1.txt",
        "https://raw.githubusercontent.com/capitainblack/freetm3/refs/heads/main/configs/sub_2.txt",
        # Добавьте сюда остальные ваши ссылки
    ]

    # 3. Авторизуемся в Google API
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)

    FOLDER_ID = "1RbHcpoEWUSs8T5QBGSqpOeYjJWJ7_g1h"  # Замените на реальный ID папки в Google Drive

    # 4. Получаем список файлов из Google Drive, чтобы знать, что обновлять, а что создавать
    print("Запрос списка существующих файлов с Google Drive...")
    query = f"'{FOLDER_ID}' in parents and trashed = false"
    try:
        results = drive_service.files().list(q=query, fields="files(id, name)", spaces="drive").execute()
        drive_files_dict = {f['name']: f['id'] for f in results.get('files', [])}
    except Exception as e:
        print(f"Не удалось получить список файлов с Google Drive: {e}")
        return

    # 5. Цикл по прямым ссылкам
    for url in URLS:
        # Извлекаем имя файла из конца URL (например, из ".../file1.txt" получим "file1.txt")
        filename = url.split("/")[-1]
        
        # Очищаем имя от возможных GET-параметров (например, токенов приватных репозиториев ?token=...)
        if "?" in filename:
            filename = filename.split("?")[0]

        print(f"\nСкачивание файла: {filename}...")
        
        try:
            # Скачиваем файл в оперативную память
            file_response = requests.get(url)
            if file_response.status_code != 200:
                print(f"-> Ошибка скачивания {filename}: Статус {file_response.status_code}")
                continue
            
            file_data = file_response.content
        except Exception as e:
            print(f"-> Не удалось подключиться к URL {url}: {e}")
            continue

        # Определяем MIME-тип
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # Оборачиваем байты из памяти в поток для отправки в Google API
        fh = BytesIO(file_data)
        media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)

        try:
            if filename in drive_files_dict:
                # Если файл с таким именем уже есть на Диске -> Обновляем
                file_id = drive_files_dict[filename]
                print(f"-> Файл найден на Диске (ID: {file_id}). Перезаписываем...")
                drive_service.files().update(fileId=file_id, media_body=media).execute()
                print("-> Успешно обновлено.")
            else:
                # Если файла нет -> Создаем новый
                print("-> Файл отсутствует на Диске. Создаем...")
                file_metadata = {
                    'name': filename,
                    'parents': [FOLDER_ID]
                }
                new_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                print(f"-> Успешно создано (ID: {new_file.get('id')}).")
        except Exception as e:
            print(f"Ошибка взаимодействия с Google Drive для {filename}: {e}")

if __name__ == "__main__":
    sync_raw_urls_to_drive()

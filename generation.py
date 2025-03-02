from key import API_KEY , SECRET_API_KEY 

import os
import time
import json
import base64
from io import BytesIO
from PIL import Image
import requests



class Text2ImageAPI:
    def __init__(self, url, api_key, secret_key):
        self.URL = url
        self.AUTH_HEADERS = {
            "X-Key": f"Key {api_key}",
            "X-Secret": f"Secret {secret_key}",
        }
        self.session = requests.Session()

    def get_model(self):
        """Получает список доступных моделей и возвращает id первой модели."""
        endpoint = f"{self.URL}key/api/v1/models"
        response = self.session.get(endpoint, headers=self.AUTH_HEADERS)
        response.raise_for_status()
        models = response.json()
        if not models:
            raise Exception("Нет доступных моделей.")
        return models[0]["id"]

    def generate(
        self,
        positive_request,
        style,
        model,
        negative_request=None,
        images=1,
        size=(1024, 1024),
    ):
        """Отправляет запрос на генерацию изображения."""
        params = {
            "type": "GENERATE",
            "numImages": images,
            "width": size[0],
            "height": size[1],
            "style": style,
            "generateParams": {"query": positive_request},
        }
        if negative_request:
            params["negativePromptUnclip"] = negative_request

        data = {
            "model_id": (None, model),
            "params": (None, json.dumps(params), "application/json"),
        }
        endpoint = f"{self.URL}key/api/v1/text2image/run"
        response = self.session.post(endpoint, headers=self.AUTH_HEADERS, files=data)
        response.raise_for_status()
        resp_json = response.json()
        if "uuid" not in resp_json:
            raise Exception("Ошибка генерации: отсутствует uuid в ответе.")
        return resp_json["uuid"]

    def check_generation(self, request_id, attempts=10, delay=10, save_path="img"):
        """
        Проверяет статус задания генерации.
        Если статус 'DONE', декодирует Base64-изображения и сохраняет их.
        """
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        endpoint = f"{self.URL}key/api/v1/text2image/status/{request_id}"
        for attempt in range(attempts):
            response = self.session.get(endpoint, headers=self.AUTH_HEADERS)
            response.raise_for_status()
            data = response.json()
            status = data.get("status")
            if status == "DONE":
                images_b64 = data.get("images", [])
                if not images_b64:
                    raise Exception("В ответе отсутствуют изображения.")
                image_paths = []
                for index, img_base64 in enumerate(images_b64):
                    image = self.base64_to_image(img_base64)
                    path = self.save_image(image, index, save_path)
                    image_paths.append(path)
                return image_paths
            elif status == "FAIL":
                raise Exception(
                    f"Генерация завершилась с ошибкой: {data.get('errorDescription')}"
                )
            time.sleep(delay)
        raise Exception("Превышено время ожидания генерации изображения.")

    @staticmethod
    def base64_to_image(base64_string):
        """Преобразует строку Base64 в объект PIL.Image."""
        if "," in base64_string:
            base64_string = base64_string.split(",", 1)[1]
        image_data = base64.b64decode(base64_string)
        return Image.open(BytesIO(image_data))

    @staticmethod
    def save_image(image, index, save_path):
        """Сохраняет изображение в указанную директорию и возвращает путь к файлу."""
        filename = f"{index + 1}.png"
        path = os.path.join(save_path, filename)
        image.save(path, "PNG")
        return path


if __name__ == "__main__":
    try:
        api = Text2ImageAPI("https://api-key.fusionbrain.ai/", API_KEY, SECRET_API_KEY)
        model_id = api.get_model()
        uuid = api.generate(positive_request="клавиатура", style="ANIME", model=model_id)
        image_paths = api.check_generation(uuid)
        print("Изображения сохранены:", image_paths)
    except Exception as e:
        print("Ошибка:", e)
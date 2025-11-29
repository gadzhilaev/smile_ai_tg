# API Документация для мобильного приложения

## Базовый URL
```
http://your-server-ip:5000
```

## Endpoints

### 1. Отправка сообщения в поддержку

**POST** `/send_message`

Отправляет сообщение от пользователя в группу поддержки Telegram.

#### Поддержка двух форматов:

##### Вариант 1: Multipart/form-data (с фото)
```
Content-Type: multipart/form-data
```

**Поля:**
- `user_id` (string, обязательно) - ID пользователя
- `message` (string, обязательно) - Текст сообщения
- `user_name` (string, опционально) - Имя пользователя
- `photo` (file, опционально) - Файл изображения (png, jpg, jpeg, gif, webp, макс. 10MB)

**Пример (Android - Retrofit):**
```kotlin
@Multipart
@POST("send_message")
suspend fun sendMessage(
    @Part("user_id") userId: RequestBody,
    @Part("message") message: RequestBody,
    @Part("user_name") userName: RequestBody?,
    @Part photo: MultipartBody.Part?
): Response<SendMessageResponse>
```

**Пример (iOS - URLSession):**
```swift
func sendMessage(userId: String, message: String, userName: String?, photo: UIImage?) {
    let url = URL(string: "\(baseURL)/send_message")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    var body = Data()
    
    // user_id
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"user_id\"\r\n\r\n".data(using: .utf8)!)
    body.append(userId.data(using: .utf8)!)
    body.append("\r\n".data(using: .utf8)!)
    
    // message
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"message\"\r\n\r\n".data(using: .utf8)!)
    body.append(message.data(using: .utf8)!)
    body.append("\r\n".data(using: .utf8)!)
    
    // photo (если есть)
    if let photo = photo, let imageData = photo.jpegData(compressionQuality: 0.8) {
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"photo\"; filename=\"photo.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)
    }
    
    body.append("--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = body
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        // Обработка ответа
    }.resume()
}
```

##### Вариант 2: JSON (без фото или с URL фото)
```
Content-Type: application/json
```

**Body:**
```json
{
    "user_id": "123456789",
    "message": "Текст сообщения",
    "user_name": "Имя пользователя",
    "photo_url": "https://example.com/photo.jpg"  // опционально
}
```

**Ответ (успех):**
```json
{
    "success": true,
    "message_id": 12345,
    "photo_url": "/uploads/uuid_filename.jpg"  // если фото было загружено
}
```

**Ответ (ошибка):**
```json
{
    "error": "Описание ошибки"
}
```

---

### 2. Регистрация устройства для push уведомлений

**POST** `/register_device`

Регистрирует токен устройства для получения push уведомлений.

**Content-Type:** `application/json`

**Body:**
```json
{
    "user_id": "123456789",
    "platform": "android",  // или "ios"
    "fcm_token": "dGhpcyBpcyBhIGZha2UgdG9rZW4...",  // для Android
    "apns_token": "dGhpcyBpcyBhIGZha2UgdG9rZW4...",  // для iOS
    "device_id": "device_unique_id"  // опционально
}
```

**Пример (Android - Firebase):**
```kotlin
// Получаем FCM токен
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (task.isSuccessful) {
        val token = task.result
        
        // Отправляем на сервер
        api.registerDevice(
            RegisterDeviceRequest(
                user_id = userId,
                platform = "android",
                fcm_token = token,
                device_id = getDeviceId()
            )
        )
    }
}
```

**Пример (iOS - APNs):**
```swift
// В AppDelegate
func application(_ application: UIApplication, 
                didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
    
    // Отправляем на сервер
    registerDevice(userId: userId, apnsToken: token)
}

func registerDevice(userId: String, apnsToken: String) {
    let url = URL(string: "\(baseURL)/register_device")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body: [String: Any] = [
        "user_id": userId,
        "platform": "ios",
        "apns_token": apnsToken,
        "device_id": UIDevice.current.identifierForVendor?.uuidString ?? ""
    ]
    
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        // Обработка ответа
    }.resume()
}
```

**Ответ (успех):**
```json
{
    "success": true
}
```

---

### 3. Получение истории переписки

**GET** `/message_history/<user_id>`

Получает историю переписки пользователя с поддержкой.

**Query параметры:**
- `limit` (int, опционально) - Количество сообщений (по умолчанию 50)

**Пример:**
```
GET /message_history/123456789?limit=100
```

**Ответ:**
```json
{
    "success": true,
    "messages": [
        {
            "id": 1,
            "message_text": "Привет, нужна помощь",
            "photo_url": "/uploads/photo1.jpg",
            "direction": "user",
            "telegram_message_id": 12345,
            "created_at": "2024-01-15 10:30:00"
        },
        {
            "id": 2,
            "message_text": "Здравствуйте! Чем могу помочь?",
            "photo_url": null,
            "direction": "support",
            "telegram_message_id": 12346,
            "created_at": "2024-01-15 10:35:00"
        }
    ]
}
```

**Направления сообщений:**
- `user` - сообщение от пользователя
- `support` - ответ от поддержки

---

### 4. Проверка работоспособности

**GET** `/health`

Проверяет, работает ли сервер.

**Ответ:**
```json
{
    "status": "ok"
}
```

---

## Push уведомления

### Формат данных в push уведомлении

Когда в группе Telegram делают reply на сообщение пользователя, на устройство приходит push уведомление со следующими данными:

**Android (FCM):**
```json
{
    "type": "support_reply",
    "user_id": "123456789",
    "message": "Текст ответа от поддержки"
}
```

**iOS (APNs):**
```json
{
    "aps": {
        "alert": {
            "title": "Ответ от поддержки",
            "body": "Текст ответа от поддержки"
        },
        "sound": "default",
        "badge": 1
    },
    "type": "support_reply",
    "user_id": "123456789",
    "message": "Текст ответа от поддержки"
}
```

### Обработка push уведомления

**Android (Firebase Messaging Service):**
```kotlin
class MyFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        val data = remoteMessage.data
        
        if (data["type"] == "support_reply") {
            val userId = data["user_id"]
            val message = data["message"]
            
            // Показываем уведомление
            showNotification("Ответ от поддержки", message)
            
            // Открываем чат с поддержкой при нажатии
            val intent = Intent(this, SupportChatActivity::class.java).apply {
                putExtra("user_id", userId)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            
            val pendingIntent = PendingIntent.getActivity(
                this, 0, intent, PendingIntent.FLAG_IMMUTABLE
            )
            
            // Создаем уведомление
            val notification = NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("Ответ от поддержки")
                .setContentText(message)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentIntent(pendingIntent)
                .setAutoCancel(true)
                .build()
            
            NotificationManagerCompat.from(this).notify(notificationId, notification)
        }
    }
}
```

**iOS (AppDelegate):**
```swift
func userNotificationCenter(_ center: UNUserNotificationCenter,
                            didReceive response: UNNotificationResponse,
                            withCompletionHandler completionHandler: @escaping () -> Void) {
    let userInfo = response.notification.request.content.userInfo
    
    if let type = userInfo["type"] as? String, type == "support_reply" {
        let userId = userInfo["user_id"] as? String
        
        // Открываем экран чата с поддержкой
        DispatchQueue.main.async {
            let storyboard = UIStoryboard(name: "Main", bundle: nil)
            if let chatVC = storyboard.instantiateViewController(withIdentifier: "SupportChatViewController") as? SupportChatViewController {
                chatVC.userId = userId
                // Показываем экран
                if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
                   let window = windowScene.windows.first {
                    window.rootViewController?.present(chatVC, animated: true)
                }
            }
        }
    }
    
    completionHandler()
}
```

---

## Рекомендации по реализации

### 1. Хранение user_id
- Используйте уникальный ID пользователя (UUID, ID из вашей БД)
- Сохраняйте его локально после регистрации/входа

### 2. Загрузка фото
- Сжимайте изображения перед отправкой (рекомендуется до 1-2MB)
- Показывайте прогресс загрузки
- Обрабатывайте ошибки сети

### 3. История переписок
- Кэшируйте историю локально
- Обновляйте при открытии чата
- Используйте pull-to-refresh для обновления

### 4. Push уведомления
- Регистрируйте токен при первом запуске и после входа
- Обновляйте токен при его изменении
- Обрабатывайте случаи, когда пользователь не дал разрешение на уведомления

### 5. Обработка ошибок
- Показывайте понятные сообщения об ошибках
- Реализуйте retry механизм для сетевых запросов
- Логируйте ошибки для отладки

---

## Пример полного потока работы

1. **Пользователь открывает чат поддержки**
   - Загружается история переписок (`GET /message_history/<user_id>`)

2. **Пользователь отправляет сообщение**
   - Отправляется запрос (`POST /send_message`) с текстом и/или фото
   - Сообщение появляется в истории

3. **Поддержка отвечает в Telegram группе**
   - Приходит push уведомление на устройство
   - При нажатии открывается чат поддержки
   - История обновляется автоматически

4. **Пользователь видит ответ**
   - Ответ отображается в истории переписки


# Руководство по интеграции для Flutter приложения

Это руководство поможет вам интегрировать поддержку через Telegram бота в ваше Flutter приложение.

## Содержание

1. [Настройка Firebase](#настройка-firebase)
2. [Установка зависимостей](#установка-зависимостей)
3. [Настройка Firebase в приложении](#настройка-firebase-в-приложении)
4. [Создание сервиса поддержки](#создание-сервиса-поддержки)
5. [Экран чата с поддержкой](#экран-чата-с-поддержкой)
6. [Обработка push уведомлений](#обработка-push-уведомлений)
7. [Пример использования](#пример-использования)

## Настройка Firebase

### 1. Создание проекта Firebase

1. Перейдите на [Firebase Console](https://console.firebase.google.com/)
2. Создайте новый проект или выберите существующий
3. Добавьте Android приложение:
   - Нажмите "Add app" → Android
   - Введите Package name вашего приложения
   - Скачайте `google-services.json` и поместите в `android/app/`
4. Добавьте iOS приложение:
   - Нажмите "Add app" → iOS
   - Введите Bundle ID вашего приложения
   - Скачайте `GoogleService-Info.plist` и поместите в `ios/Runner/`
5. Включите Cloud Messaging:
   - В настройках проекта перейдите в Cloud Messaging
   - Скопируйте **Server key** и добавьте в `.env` файл сервера как `FCM_SERVER_KEY`

### 2. Настройка Android

В файле `android/app/build.gradle`:

```gradle
dependencies {
    // ... другие зависимости
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-messaging'
}
```

В файле `android/build.gradle`:

```gradle
buildscript {
    dependencies {
        // ... другие зависимости
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

В файле `android/app/build.gradle` (в конце файла):

```gradle
apply plugin: 'com.google.gms.google-services'
```

### 3. Настройка iOS

В файле `ios/Podfile`:

```ruby
platform :ios, '12.0'

target 'Runner' do
  use_frameworks!
  use_modular_headers!

  # ... другие настройки
  
  pod 'Firebase/Messaging'
end
```

Затем выполните:
```bash
cd ios
pod install
cd ..
```

В `ios/Runner/Info.plist` добавьте разрешения:

```xml
<key>UIBackgroundModes</key>
<array>
    <string>remote-notification</string>
</array>
```

## Установка зависимостей

Добавьте в `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # HTTP запросы
  http: ^1.1.0
  
  # Firebase
  firebase_core: ^2.24.2
  firebase_messaging: ^14.7.9
  
  # Для работы с изображениями
  image_picker: ^1.0.5
  image: ^4.1.3
  
  # Для работы с файлами
  path_provider: ^2.1.1
  
  # Для навигации
  go_router: ^6.1.2  # или другой роутер
```

Затем выполните:
```bash
flutter pub get
```

## Настройка Firebase в приложении

Создайте файл `lib/firebase_options.dart` (если его нет):

```bash
flutterfire configure
```

Или создайте вручную, используя данные из Firebase Console.

В `lib/main.dart`:

```dart
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  
  runApp(MyApp());
}
```

## Создание сервиса поддержки

Создайте файл `lib/services/support_service.dart`:

```dart
import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:path/path.dart' as path;

class SupportService {
  // Замените на URL вашего сервера
  static const String baseUrl = 'http://your-server-ip:5000';
  
  // Отправка сообщения с возможностью прикрепления фото
  static Future<Map<String, dynamic>> sendMessage({
    required String userId,
    String? userName,
    required String message,
    File? photo,
  }) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/send_message'),
      );
      
      // Добавляем текстовые данные
      request.fields['user_id'] = userId;
      if (userName != null) {
        request.fields['user_name'] = userName;
      }
      request.fields['message'] = message;
      
      // Добавляем фото если есть
      if (photo != null) {
        var photoStream = http.ByteStream(photo.openRead());
        var photoLength = await photo.length();
        var multipartFile = http.MultipartFile(
          'photo',
          photoStream,
          photoLength,
          filename: path.basename(photo.path),
        );
        request.files.add(multipartFile);
      }
      
      var response = await request.send();
      var responseBody = await response.stream.bytesToString();
      
      if (response.statusCode == 200) {
        return json.decode(responseBody);
      } else {
        throw Exception('Ошибка отправки: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Ошибка при отправке сообщения: $e');
    }
  }
  
  // Получение истории переписки
  static Future<List<Map<String, dynamic>>> getMessageHistory(
    String userId, {
    int limit = 50,
  }) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/message_history/$userId?limit=$limit'),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return List<Map<String, dynamic>>.from(data['messages']);
      } else {
        throw Exception('Ошибка получения истории: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Ошибка при получении истории: $e');
    }
  }
  
  // Регистрация токена устройства для push уведомлений
  static Future<void> registerDevice({
    required String userId,
    required String fcmToken,
    required String platform,
    String? deviceId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/register_device'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'user_id': userId,
          'fcm_token': fcmToken,
          'platform': platform,
          'device_id': deviceId,
        }),
      );
      
      if (response.statusCode != 200) {
        throw Exception('Ошибка регистрации устройства: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Ошибка при регистрации устройства: $e');
    }
  }
}
```

## Экран чата с поддержкой

Создайте файл `lib/screens/support_chat_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import '../services/support_service.dart';
import '../services/fcm_service.dart';

class SupportChatScreen extends StatefulWidget {
  final String userId;
  final String? userName;
  
  const SupportChatScreen({
    Key? key,
    required this.userId,
    this.userName,
  }) : super(key: key);
  
  @override
  State<SupportChatScreen> createState() => _SupportChatScreenState();
}

class _SupportChatScreenState extends State<SupportChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  List<Map<String, dynamic>> _messages = [];
  bool _isLoading = false;
  File? _selectedImage;
  final ImagePicker _picker = ImagePicker();
  
  @override
  void initState() {
    super.initState();
    _loadMessageHistory();
  }
  
  Future<void> _loadMessageHistory() async {
    setState(() => _isLoading = true);
    try {
      final history = await SupportService.getMessageHistory(widget.userId);
      setState(() {
        _messages = history;
        _isLoading = false;
      });
      _scrollToBottom();
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка загрузки истории: $e')),
      );
    }
  }
  
  Future<void> _sendMessage() async {
    final message = _messageController.text.trim();
    if (message.isEmpty && _selectedImage == null) return;
    
    setState(() => _isLoading = true);
    
    try {
      await SupportService.sendMessage(
        userId: widget.userId,
        userName: widget.userName,
        message: message,
        photo: _selectedImage,
      );
      
      _messageController.clear();
      setState(() {
        _selectedImage = null;
        _isLoading = false;
      });
      
      // Добавляем сообщение в список
      setState(() {
        _messages.add({
          'message': message,
          'photo_url': _selectedImage?.path,
          'direction': 'user',
          'created_at': DateTime.now().toIso8601String(),
        });
      });
      
      _scrollToBottom();
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка отправки: $e')),
      );
    }
  }
  
  Future<void> _pickImage() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );
      
      if (image != null) {
        setState(() {
          _selectedImage = File(image.path);
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка выбора изображения: $e')),
      );
    }
  }
  
  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Поддержка'),
      ),
      body: Column(
        children: [
          Expanded(
            child: _isLoading && _messages.isEmpty
                ? Center(child: CircularProgressIndicator())
                : ListView.builder(
                    controller: _scrollController,
                    padding: EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final message = _messages[index];
                      final isUser = message['direction'] == 'user';
                      
                      return Align(
                        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: EdgeInsets.only(bottom: 12),
                          padding: EdgeInsets.all(12),
                          constraints: BoxConstraints(
                            maxWidth: MediaQuery.of(context).size.width * 0.75,
                          ),
                          decoration: BoxDecoration(
                            color: isUser ? Colors.blue : Colors.grey[300],
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (message['photo_url'] != null)
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(8),
                                  child: Image.file(
                                    File(message['photo_url']),
                                    width: 200,
                                    height: 200,
                                    fit: BoxFit.cover,
                                  ),
                                ),
                              if (message['message'] != null && message['message'].isNotEmpty)
                                Text(
                                  message['message'],
                                  style: TextStyle(
                                    color: isUser ? Colors.white : Colors.black87,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          if (_selectedImage != null)
            Container(
              height: 100,
              margin: EdgeInsets.symmetric(horizontal: 16),
              child: Stack(
                children: [
                  Image.file(_selectedImage!, fit: BoxFit.cover),
                  Positioned(
                    top: 4,
                    right: 4,
                    child: IconButton(
                      icon: Icon(Icons.close, color: Colors.white),
                      onPressed: () => setState(() => _selectedImage = null),
                    ),
                  ),
                ],
              ),
            ),
          Container(
            padding: EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black12,
                  blurRadius: 4,
                  offset: Offset(0, -2),
                ),
              ],
            ),
            child: Row(
              children: [
                IconButton(
                  icon: Icon(Icons.photo_library),
                  onPressed: _pickImage,
                ),
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: 'Введите сообщение...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                      ),
                      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    ),
                    maxLines: null,
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.send),
                  onPressed: _isLoading ? null : _sendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}
```

## Обработка push уведомлений

Создайте файл `lib/services/fcm_service.dart`:

```dart
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'support_service.dart';
import 'dart:io';

class FCMService {
  static final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  static String? _fcmToken;
  
  // Инициализация FCM
  static Future<void> initialize(String userId) async {
    // Запрашиваем разрешение на уведомления
    NotificationSettings settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    
    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      // Получаем токен
      _fcmToken = await _messaging.getToken();
      
      if (_fcmToken != null) {
        // Регистрируем токен на сервере
        await SupportService.registerDevice(
          userId: userId,
          fcmToken: _fcmToken!,
          platform: Platform.isAndroid ? 'android' : 'ios',
        );
      }
      
      // Обработка уведомлений когда приложение открыто
      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);
      
      // Обработка уведомлений когда приложение в фоне
      FirebaseMessaging.onMessageOpenedApp.listen(_handleBackgroundMessage);
      
      // Обработка уведомления которое открыло приложение
      RemoteMessage? initialMessage = await _messaging.getInitialMessage();
      if (initialMessage != null) {
        _handleBackgroundMessage(initialMessage);
      }
    }
  }
  
  // Обработка уведомления когда приложение открыто
  static void _handleForegroundMessage(RemoteMessage message) {
    if (message.data['type'] == 'support_reply') {
      // Показываем уведомление или обновляем UI
      debugPrint('Получен ответ от поддержки: ${message.notification?.body}');
    }
  }
  
  // Обработка уведомления когда приложение в фоне или закрыто
  static void _handleBackgroundMessage(RemoteMessage message) {
    if (message.data['type'] == 'support_reply') {
      final userId = message.data['user_id'];
      // Навигация к экрану чата с поддержкой
      // Используйте ваш роутер для навигации
      debugPrint('Открываем чат для пользователя: $userId');
    }
  }
  
  // Получить текущий токен
  static String? getToken() => _fcmToken;
}
```

В `lib/main.dart` добавьте обработчик фоновых сообщений:

```dart
// Топ-уровневая функция для обработки фоновых сообщений
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  // Обработка фонового сообщения
  print('Фоновое сообщение: ${message.messageId}');
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  
  // Регистрируем обработчик фоновых сообщений
  FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
  
  runApp(MyApp());
}
```

## Пример использования

В вашем главном экране или при инициализации приложения:

```dart
import 'package:flutter/material.dart';
import 'services/fcm_service.dart';
import 'screens/support_chat_screen.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String userId = 'user_123'; // Получите из вашей системы аутентификации
  
  @override
  void initState() {
    super.initState();
    // Инициализируем FCM при запуске приложения
    FCMService.initialize(userId);
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Главная')),
      body: Center(
        child: ElevatedButton(
          onPressed: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => SupportChatScreen(
                  userId: userId,
                  userName: 'Имя пользователя',
                ),
              ),
            );
          },
          child: Text('Открыть поддержку'),
        ),
      ),
    );
  }
}
```

## Важные замечания

1. **URL сервера**: Замените `http://your-server-ip:5000` на реальный адрес вашего сервера
2. **Безопасность**: В продакшене используйте HTTPS
3. **Обработка ошибок**: Добавьте обработку всех возможных ошибок
4. **Навигация**: Адаптируйте код навигации под ваш роутер
5. **Аутентификация**: Интегрируйте с вашей системой аутентификации для получения `userId`

## Тестирование

1. Запустите сервер: `python server.py`
2. Убедитесь, что Firebase настроен правильно
3. Запустите приложение и отправьте тестовое сообщение
4. Проверьте, что сообщение появилось в Telegram группе
5. Ответьте на сообщение в группе (reply)
6. Проверьте, что push уведомление пришло на устройство


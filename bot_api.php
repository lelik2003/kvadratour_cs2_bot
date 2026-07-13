<?php
// api/bot/bot_api.php - Полный API для бота
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Включаем отображение ошибок для отладки
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// ============================================
// КОНФИГУРАЦИЯ
// ============================================

// ТОТ ЖЕ КЛЮЧ, ЧТО И В .env БОТА!
define('BOT_API_KEY', '7f8a9b2c3d4e5f6g7h8i9j0k1l2m3n4o');

// ============================================
// ПОДКЛЮЧЕНИЕ К БД
// ============================================

try {
    $pdo = new PDO(
        'mysql:host=sql107.infinityfree.com;dbname=if0_41929018_lelik;charset=utf8mb4',
        'if0_41929018',
        'MAtnRnd5Fa'  // ЗАМЕНИ НА РЕАЛЬНЫЙ ПАРОЛЬ!
    );
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    echo json_encode(['error' => 'Database connection failed: ' . $e->getMessage()]);
    exit();
}

// ============================================
// ФУНКЦИИ
// ============================================

function botResponse($data, $status = 200) {
    http_response_code($status);
    echo json_encode($data);
    exit();
}

function botError($message, $status = 400) {
    http_response_code($status);
    echo json_encode(['error' => $message]);
    exit();
}

function getUserByTelegram($telegram_id) {
    global $pdo;
    $stmt = $pdo->prepare('
        SELECT u.*, 
               a.id as admin_id,
               a.admin_level,
               a.is_active as admin_is_active
        FROM users u
        LEFT JOIN admin_users a ON u.id = a.user_id AND a.is_active = 1
        WHERE u.telegram_id = ?
    ');
    $stmt->execute([$telegram_id]);
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

function getUserBySteamId($steam_id) {
    global $pdo;
    $stmt = $pdo->prepare('
        SELECT u.*, 
               a.id as admin_id,
               a.admin_level,
               a.is_active as admin_is_active
        FROM users u
        LEFT JOIN admin_users a ON u.id = a.user_id AND a.is_active = 1
        WHERE u.steamid = ?
    ');
    $stmt->execute([$steam_id]);
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

function linkTelegramAccount($telegram_id, $site_user_id) {
    global $pdo;
    try {
        $pdo->beginTransaction();
        
        // Проверяем, существует ли пользователь
        $stmt = $pdo->prepare('SELECT id FROM users WHERE id = ?');
        $stmt->execute([$site_user_id]);
        if (!$stmt->fetch()) {
            return ['success' => false, 'error' => 'User not found'];
        }
        
        // Проверяем, не привязан ли уже Telegram к другому аккаунту
        $stmt = $pdo->prepare('SELECT id FROM users WHERE telegram_id = ? AND id != ?');
        $stmt->execute([$telegram_id, $site_user_id]);
        if ($stmt->fetch()) {
            return ['success' => false, 'error' => 'Telegram already linked to another account'];
        }
        
        // Обновляем telegram_id
        $stmt = $pdo->prepare('UPDATE users SET telegram_id = ? WHERE id = ?');
        $stmt->execute([$telegram_id, $site_user_id]);
        
        $pdo->commit();
        return ['success' => true];
        
    } catch (Exception $e) {
        $pdo->rollBack();
        return ['success' => false, 'error' => $e->getMessage()];
    }
}

function unlinkTelegramAccount($site_user_id) {
    global $pdo;
    try {
        $stmt = $pdo->prepare('UPDATE users SET telegram_id = NULL WHERE id = ?');
        $stmt->execute([$site_user_id]);
        return ['success' => true];
    } catch (Exception $e) {
        return ['success' => false, 'error' => $e->getMessage()];
    }
}

// ============================================
// ОСНОВНАЯ ЛОГИКА
// ============================================

$input = json_decode(file_get_contents('php://input'), true);
$action = $input['action'] ?? $_GET['action'] ?? '';

// Определяем действие по методу
if (empty($action)) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $action = 'auth';
    } elseif ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $action = 'check';
    }
}

// ============================================
// АВТОРИЗАЦИЯ
// ============================================

if ($action === 'auth' || $action === 'login') {
    // Проверяем API ключ
    $api_key = $input['api_key'] ?? '';
    if ($api_key !== BOT_API_KEY) {
        botError('Invalid API key', 403);
    }
    
    $telegram_id = $input['telegram_id'] ?? $_POST['telegram_id'] ?? '';
    $steam_id = $input['steam_id'] ?? $_POST['steam_id'] ?? '';
    
    if (empty($telegram_id) && empty($steam_id)) {
        botError('Missing telegram_id or steam_id', 400);
    }
    
    // Ищем пользователя
    $user = null;
    if (!empty($telegram_id)) {
        $user = getUserByTelegram($telegram_id);
    }
    if (!$user && !empty($steam_id)) {
        $user = getUserBySteamId($steam_id);
    }
    
    if (!$user) {
        botError('User not found. Please link your account first.', 404);
    }
    
    // Если есть telegram_id и пользователь найден по steam_id, связываем
    if (!empty($telegram_id) && empty($user['telegram_id'])) {
        $result = linkTelegramAccount($telegram_id, $user['id']);
        if (!$result['success']) {
            botError($result['error'], 400);
        }
    }
    
    // Создаем токен (упрощенный JWT)
    $token = base64_encode(json_encode([
        'user_id' => $user['id'],
        'steamid' => $user['steamid'],
        'telegram_id' => $telegram_id,
        'exp' => time() + 3600
    ]));
    
    botResponse([
        'success' => true,
        'access_token' => $token,
        'token_type' => 'Bearer',
        'expires_in' => 3600,
        'user' => [
            'id' => $user['id'],
            'steamid' => $user['steamid'],
            'nickname' => $user['nickname'],
            'avatar' => $user['avatar'] ?? '/photo/index/profile.png',
            'is_admin' => !empty($user['admin_id']),
            'admin_level' => (int)($user['admin_level'] ?? 0),
            'balance' => (float)($user['balance'] ?? 0),
            'telegram_id' => $user['telegram_id'] ?? null
        ]
    ]);
}

// ============================================
// ПРОВЕРКА СТАТУСА
// ============================================

if ($action === 'check') {
    $telegram_id = $_GET['telegram_id'] ?? $input['telegram_id'] ?? '';
    
    if (empty($telegram_id)) {
        botError('Missing telegram_id', 400);
    }
    
    $user = getUserByTelegram($telegram_id);
    
    if ($user) {
        botResponse([
            'success' => true,
            'authenticated' => true,
            'user' => [
                'id' => $user['id'],
                'steamid' => $user['steamid'],
                'nickname' => $user['nickname'],
                'avatar' => $user['avatar'] ?? '/photo/index/profile.png',
                'is_admin' => !empty($user['admin_id']),
                'admin_level' => (int)($user['admin_level'] ?? 0),
                'balance' => (float)($user['balance'] ?? 0),
                'telegram_id' => $user['telegram_id'] ?? null
            ]
        ]);
    } else {
        botResponse([
            'success' => true,
            'authenticated' => false
        ]);
    }
}

// ============================================
// ПРИВЯЗКА АККАУНТА
// ============================================

if ($action === 'link') {
    $api_key = $input['api_key'] ?? '';
    if ($api_key !== BOT_API_KEY) {
        botError('Invalid API key', 403);
    }
    
    $telegram_id = $input['telegram_id'] ?? $_POST['telegram_id'] ?? '';
    $site_user_id = $input['site_user_id'] ?? $_POST['site_user_id'] ?? '';
    
    if (empty($telegram_id) || empty($site_user_id)) {
        botError('Missing telegram_id or site_user_id', 400);
    }
    
    $result = linkTelegramAccount($telegram_id, $site_user_id);
    
    if ($result['success']) {
        botResponse([
            'success' => true,
            'message' => 'Telegram linked successfully'
        ]);
    } else {
        botError($result['error'], 400);
    }
}

// ============================================
// ОТВЯЗКА АККАУНТА
// ============================================

if ($action === 'unlink') {
    $api_key = $input['api_key'] ?? '';
    if ($api_key !== BOT_API_KEY) {
        botError('Invalid API key', 403);
    }
    
    $site_user_id = $input['site_user_id'] ?? $_POST['site_user_id'] ?? '';
    
    if (empty($site_user_id)) {
        botError('Missing site_user_id', 400);
    }
    
    $result = unlinkTelegramAccount($site_user_id);
    
    if ($result['success']) {
        botResponse([
            'success' => true,
            'message' => 'Telegram unlinked successfully'
        ]);
    } else {
        botError($result['error'], 400);
    }
}

// ============================================
// ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ
// ============================================

if ($action === 'user') {
    $telegram_id = $_GET['telegram_id'] ?? $input['telegram_id'] ?? '';
    $user_id = $_GET['id'] ?? $input['id'] ?? '';
    
    if (empty($telegram_id) && empty($user_id)) {
        botError('Missing telegram_id or id', 400);
    }
    
    $user = null;
    if (!empty($telegram_id)) {
        $user = getUserByTelegram($telegram_id);
    } elseif (!empty($user_id)) {
        global $pdo;
        $stmt = $pdo->prepare('
            SELECT u.*, 
                   a.id as admin_id,
                   a.admin_level,
                   a.is_active as admin_is_active
            FROM users u
            LEFT JOIN admin_users a ON u.id = a.user_id AND a.is_active = 1
            WHERE u.id = ?
        ');
        $stmt->execute([$user_id]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
    }
    
    if ($user) {
        botResponse([
            'success' => true,
            'user' => [
                'id' => $user['id'],
                'steamid' => $user['steamid'],
                'nickname' => $user['nickname'],
                'avatar' => $user['avatar'] ?? '/photo/index/profile.png',
                'is_admin' => !empty($user['admin_id']),
                'admin_level' => (int)($user['admin_level'] ?? 0),
                'balance' => (float)($user['balance'] ?? 0),
                'telegram_id' => $user['telegram_id'] ?? null
            ]
        ]);
    } else {
        botError('User not found', 404);
    }
}

// ============================================
// НЕИЗВЕСТНОЕ ДЕЙСТВИЕ
// ============================================

botError('Unknown action: ' . $action, 400);
<?php
// ============================================
// api/bot/auth.php - Авторизация бота
// ============================================

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-API-Key');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// ============================================
// ПОДКЛЮЧЕНИЕ
// ============================================

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../config/jwt.php';

// ============================================
// КОНФИГУРАЦИЯ
// ============================================

// Секретный ключ для бота (должен совпадать с тем, что в .env бота)
define('BOT_API_KEY', '7f8a9b2c3d4e5f6g7h8i9j0k1l2m3n4o');

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

function verifyApiKey() {
    $headers = getallheaders();
    $api_key = $headers['X-API-Key'] ?? $headers['x-api-key'] ?? '';
    
    if (empty($api_key)) {
        // Проверяем в POST/GET
        $input = json_decode(file_get_contents('php://input'), true);
        $api_key = $input['api_key'] ?? $_GET['api_key'] ?? '';
    }
    
    if ($api_key !== BOT_API_KEY) {
        botError('Invalid API key', 403);
    }
    
    return true;
}

function getUserBySteamId($steam_id) {
    try {
        $pdo = getDBConnection();
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
    } catch (Exception $e) {
        error_log('getUserBySteamId error: ' . $e->getMessage());
        return null;
    }
}

function getUserByTelegramId($telegram_id) {
    try {
        $pdo = getDBConnection();
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
    } catch (Exception $e) {
        error_log('getUserByTelegramId error: ' . $e->getMessage());
        return null;
    }
}

function linkTelegramAccount($telegram_id, $site_user_id) {
    try {
        $pdo = getDBConnection();
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
        
        // Обновляем telegram_id у пользователя
        $stmt = $pdo->prepare('UPDATE users SET telegram_id = ? WHERE id = ?');
        $stmt->execute([$telegram_id, $site_user_id]);
        
        $pdo->commit();
        return ['success' => true];
        
    } catch (Exception $e) {
        $pdo->rollBack();
        error_log('linkTelegramAccount error: ' . $e->getMessage());
        return ['success' => false, 'error' => $e->getMessage()];
    }
}

function unlinkTelegramAccount($site_user_id) {
    try {
        $pdo = getDBConnection();
        $stmt = $pdo->prepare('UPDATE users SET telegram_id = NULL WHERE id = ?');
        $stmt->execute([$site_user_id]);
        return ['success' => true];
    } catch (Exception $e) {
        error_log('unlinkTelegramAccount error: ' . $e->getMessage());
        return ['success' => false, 'error' => $e->getMessage()];
    }
}

// ============================================
// ОСНОВНАЯ ЛОГИКА
// ============================================

// Получаем действие
$input = json_decode(file_get_contents('php://input'), true);
$action = $_GET['action'] ?? $input['action'] ?? '';

// Если action не указан, проверяем по методу
if (empty($action)) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $action = 'auth';
    } elseif ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $action = 'check';
    }
}

// ============================================
// АВТОРИЗАЦИЯ БОТА (JWT)
// ============================================

if ($action === 'auth' || $action === 'login') {
    // Проверяем API ключ
    verifyApiKey();
    
    $data = $input ?: $_POST;
    $steam_id = $data['steam_id'] ?? '';
    $telegram_id = $data['telegram_id'] ?? '';
    
    // Если есть telegram_id, пытаемся найти пользователя
    if (!empty($telegram_id)) {
        $user = getUserByTelegramId($telegram_id);
        if ($user) {
            // Создаем JWT токен
            $token = JWT::encode([
                'sub' => 'bot',
                'user_id' => $user['id'],
                'steamid' => $user['steamid'],
                'telegram_id' => $telegram_id,
                'role' => 'bot',
                'api_key' => BOT_API_KEY,
                'exp' => time() + 3600
            ]);
            
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
                    'admin_level' => (int)($user['admin_level'] ?? 0)
                ]
            ]);
        }
    }
    
    // Если есть steam_id ищем по нему
    if (!empty($steam_id)) {
        $user = getUserBySteamId($steam_id);
        if ($user) {
            // Обновляем telegram_id если есть
            if (!empty($telegram_id)) {
                $result = linkTelegramAccount($telegram_id, $user['id']);
                if (!$result['success']) {
                    botError($result['error'], 400);
                }
            }
            
            // Создаем JWT токен
            $token = JWT::encode([
                'sub' => 'bot',
                'user_id' => $user['id'],
                'steamid' => $user['steamid'],
                'telegram_id' => $telegram_id,
                'role' => 'bot',
                'api_key' => BOT_API_KEY,
                'exp' => time() + 3600
            ]);
            
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
                    'admin_level' => (int)($user['admin_level'] ?? 0)
                ]
            ]);
        }
    }
    
    // Если пользователь не найден
    botError('User not found', 404);
}

// ============================================
// ПРОВЕРКА СТАТУСА
// ============================================

if ($action === 'check') {
    $telegram_id = $_GET['telegram_id'] ?? $input['telegram_id'] ?? '';
    
    if (empty($telegram_id)) {
        botError('Missing telegram_id', 400);
    }
    
    $user = getUserByTelegramId($telegram_id);
    
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
                'admin_level' => (int)($user['admin_level'] ?? 0)
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
    verifyApiKey();
    
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
    verifyApiKey();
    
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
// НЕИЗВЕСТНОЕ ДЕЙСТВИЕ
// ============================================

botError('Unknown action: ' . $action, 400);
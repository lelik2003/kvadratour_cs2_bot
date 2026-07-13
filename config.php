<?php
// ============================================
// api/bot/config.php - Общий конфиг
// ============================================

require_once __DIR__ . '/../config/database.php';

function botResponse($data) {
    header('Content-Type: application/json');
    echo json_encode($data);
    exit();
}

function botError($message, $code = 400) {
    header('Content-Type: application/json');
    http_response_code($code);
    echo json_encode(['error' => $message]);
    exit();
}

function getUserByTelegram($telegram_id) {
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
        error_log('getUserByTelegram error: ' . $e->getMessage());
        return null;
    }
}
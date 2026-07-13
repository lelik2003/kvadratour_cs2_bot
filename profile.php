<?php
// api/bot/profile.php - Новый файл для бота
require_once 'config.php';

$telegram_id = $_GET['telegram_id'] ?? '';
$token = $_GET['token'] ?? '';

if (!validateBotToken($telegram_id, $token)) {
    botError('Invalid token', 401);
}

$pdo = getDBConnection();
if (!$pdo) {
    botError('Database error', 500);
}

// Используем существующие таблицы, просто выбираем данные
$stmt = $pdo->prepare("
    SELECT 
        u.id,
        u.steam_id,
        u.username,
        u.avatar,
        u.total_points,
        u.matches_played,
        u.matches_won,
        u.is_admin,
        u.created_at,
        (SELECT COUNT(*) FROM team_members tm WHERE tm.user_id = u.id) as teams_count
    FROM users u
    INNER JOIN telegram_users tu ON u.steam_id = tu.steam_id
    WHERE tu.telegram_id = ?
");
$stmt->execute([$telegram_id]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    botError('User not found');
}

// Получаем статистику из существующих таблиц
$stmt = $pdo->prepare("
    SELECT 
        COUNT(CASE WHEN m.winner_id = ? THEN 1 END) as wins,
        AVG(ms.kills) as avg_kills,
        AVG(ms.deaths) as avg_deaths
    FROM match_stats ms
    LEFT JOIN matches m ON ms.match_id = m.id
    WHERE ms.user_id = ?
");
$stmt->execute([$user['id'], $user['id']]);
$stats = $stmt->fetch(PDO::FETCH_ASSOC);

botResponse([
    'profile' => array_merge($user, [
        'avg_kills' => round($stats['avg_kills'] ?? 0, 1),
        'avg_deaths' => round($stats['avg_deaths'] ?? 0, 1),
        'kd_ratio' => $stats['avg_deaths'] > 0 ? round($stats['avg_kills'] / $stats['avg_deaths'], 2) : 0
    ])
]);
<?php
// api/bot/matches.php - Новый файл для бота
require_once 'config.php';

$telegram_id = $_GET['telegram_id'] ?? '';
$token = $_GET['token'] ?? '';
$action = $_GET['action'] ?? 'list';

if (!validateBotToken($telegram_id, $token)) {
    botError('Invalid token', 401);
}

$pdo = getDBConnection();
if (!$pdo) {
    botError('Database error', 500);
}

switch($action) {
    case 'list':
        listMatches($pdo);
        break;
    case 'active':
        activeMatches($pdo);
        break;
    case 'my':
        myMatches($pdo, $telegram_id);
        break;
    default:
        botError('Unknown action');
}

function listMatches($pdo) {
    // Используем существующие таблицы matches и teams
    $stmt = $pdo->prepare("
        SELECT 
            m.*,
            t1.name as team1_name,
            t2.name as team2_name,
            mp.name as map_name
        FROM matches m
        LEFT JOIN teams t1 ON m.team1_id = t1.id
        LEFT JOIN teams t2 ON m.team2_id = t2.id
        LEFT JOIN maps mp ON m.map_id = mp.id
        WHERE m.status IN ('active', 'scheduled')
        ORDER BY m.start_time DESC
        LIMIT 20
    ");
    $stmt->execute();
    $matches = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    botResponse(['matches' => $matches]);
}

function activeMatches($pdo) {
    $stmt = $pdo->prepare("
        SELECT 
            m.*,
            t1.name as team1_name,
            t2.name as team2_name,
            mp.name as map_name
        FROM matches m
        LEFT JOIN teams t1 ON m.team1_id = t1.id
        LEFT JOIN teams t2 ON m.team2_id = t2.id
        LEFT JOIN maps mp ON m.map_id = mp.id
        WHERE m.status = 'active'
        ORDER BY m.start_time ASC
    ");
    $stmt->execute();
    $matches = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    botResponse(['matches' => $matches]);
}

function myMatches($pdo, $telegram_id) {
    $user = getUserByTelegram($telegram_id);
    if (!$user) {
        botError('User not found');
    }
    
    $stmt = $pdo->prepare("
        SELECT 
            m.*,
            t1.name as team1_name,
            t2.name as team2_name,
            mp.name as map_name
        FROM matches m
        LEFT JOIN teams t1 ON m.team1_id = t1.id
        LEFT JOIN teams t2 ON m.team2_id = t2.id
        LEFT JOIN maps mp ON m.map_id = mp.id
        LEFT JOIN team_members tm ON (tm.team_id = m.team1_id OR tm.team_id = m.team2_id)
        WHERE tm.user_id = ?
        ORDER BY m.start_time DESC
        LIMIT 20
    ");
    $stmt->execute([$user['id']]);
    $matches = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    botResponse(['matches' => $matches]);
}
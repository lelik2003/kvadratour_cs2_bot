<?php
// api/bot/admin.php - Админ-панель для бота
require_once 'config.php';

$telegram_id = $_GET['telegram_id'] ?? '';
$token = $_GET['token'] ?? '';
$action = $_GET['action'] ?? '';

if (!validateBotToken($telegram_id, $token)) {
    botError('Invalid token', 401);
}

// Проверяем права админа
$user = getUserByTelegram($telegram_id);
if (!$user || !$user['is_admin']) {
    botError('Access denied. Admin only.', 403);
}

$pdo = getDBConnection();
if (!$pdo) {
    botError('Database error', 500);
}

switch($action) {
    // Управление пользователями
    case 'users_list':
        getUsersList($pdo);
        break;
    case 'user_info':
        getUserInfo($pdo);
        break;
    case 'user_ban':
        banUser($pdo);
        break;
    case 'user_unban':
        unbanUser($pdo);
        break;
    case 'user_make_admin':
        makeAdmin($pdo);
        break;
    case 'user_remove_admin':
        removeAdmin($pdo);
        break;
    
    // Управление матчами
    case 'matches_list':
        getMatchesList($pdo);
        break;
    case 'match_create':
        createMatch($pdo);
        break;
    case 'match_update':
        updateMatch($pdo);
        break;
    case 'match_delete':
        deleteMatch($pdo);
        break;
    case 'match_set_score':
        setMatchScore($pdo);
        break;
    
    // Управление турнирами
    case 'tournaments_list':
        getTournamentsList($pdo);
        break;
    case 'tournament_create':
        createTournament($pdo);
        break;
    case 'tournament_update':
        updateTournament($pdo);
        break;
    case 'tournament_delete':
        deleteTournament($pdo);
        break;
    case 'tournament_start':
        startTournament($pdo);
        break;
    
    // Статистика
    case 'stats':
        getStats($pdo);
        break;
    
    // Баны и модерация
    case 'banned_list':
        getBannedList($pdo);
        break;
    case 'reports_list':
        getReportsList($pdo);
        break;
    case 'report_resolve':
        resolveReport($pdo);
        break;
    
    default:
        botError('Unknown action');
}

// ============ ФУНКЦИИ ============

function getUsersList($pdo) {
    $limit = $_GET['limit'] ?? 20;
    $offset = $_GET['offset'] ?? 0;
    $search = $_GET['search'] ?? '';
    
    $sql = "SELECT id, steam_id, username, is_admin, matches_played, matches_won, total_points, created_at, last_login 
            FROM users";
    $params = [];
    
    if (!empty($search)) {
        $sql .= " WHERE username LIKE ? OR steam_id LIKE ?";
        $params = ["%$search%", "%$search%"];
    }
    
    $sql .= " ORDER BY id DESC LIMIT ? OFFSET ?";
    $params[] = (int)$limit;
    $params[] = (int)$offset;
    
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $users = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    // Подсчет общего количества
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM users");
    $total = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
    
    botResponse([
        'users' => $users,
        'total' => $total,
        'limit' => $limit,
        'offset' => $offset
    ]);
}

function getUserInfo($pdo) {
    $user_id = $_GET['user_id'] ?? 0;
    
    if (!$user_id) {
        botError('User ID required');
    }
    
    $stmt = $pdo->prepare("
        SELECT 
            u.*,
            (SELECT COUNT(*) FROM team_members WHERE user_id = u.id) as teams_count,
            (SELECT COUNT(*) FROM matches WHERE winner_id = u.id) as wins,
            (SELECT COUNT(*) FROM matches WHERE team1_id IN (SELECT team_id FROM team_members WHERE user_id = u.id) 
             OR team2_id IN (SELECT team_id FROM team_members WHERE user_id = u.id)) as matches_total,
            (SELECT COUNT(*) FROM registrations WHERE user_id = u.id) as tournaments_participated
        FROM users u
        WHERE u.id = ?
    ");
    $stmt->execute([$user_id]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$user) {
        botError('User not found');
    }
    
    // Проверка бана
    $stmt = $pdo->prepare("SELECT * FROM banned_users WHERE steam_id = ?");
    $stmt->execute([$user['steam_id']]);
    $ban = $stmt->fetch(PDO::FETCH_ASSOC);
    
    botResponse([
        'user' => $user,
        'is_banned' => (bool)$ban,
        'ban_info' => $ban
    ]);
}

function banUser($pdo) {
    $data = json_decode(file_get_contents('php://input'), true);
    
    $steam_id = $data['steam_id'] ?? '';
    $reason = $data['reason'] ?? 'Нарушение правил';
    $hours = $data['hours'] ?? 0; // 0 = permanent
    
    if (empty($steam_id)) {
        botError('Steam ID required');
    }
    
    // Проверяем, не забанен ли уже
    $stmt = $pdo->prepare("SELECT * FROM banned_users WHERE steam_id = ?");
    $stmt->execute([$steam_id]);
    if ($stmt->fetch()) {
        botError('User is already banned');
    }
    
    $ban_until = $hours > 0 ? date('Y-m-d H:i:s', strtotime("+$hours hours")) : null;
    
    $stmt = $pdo->prepare("
        INSERT INTO banned_users (steam_id, banned_by, ban_date, reason, ban_until) 
        VALUES (?, ?, NOW(), ?, ?)
    ");
    $stmt->execute([$steam_id, $_GET['admin_id'] ?? 1, $reason, $ban_until]);
    
    // Логируем действие
    logAdminAction($pdo, 'ban_user', "Banned user $steam_id. Reason: $reason");
    
    botResponse([
        'message' => 'User banned successfully',
        'ban_until' => $ban_until
    ]);
}

function unbanUser($pdo) {
    $steam_id = $_GET['steam_id'] ?? '';
    
    if (empty($steam_id)) {
        botError('Steam ID required');
    }
    
    $stmt = $pdo->prepare("DELETE FROM banned_users WHERE steam_id = ?");
    $stmt->execute([$steam_id]);
    
    logAdminAction($pdo, 'unban_user', "Unbanned user $steam_id");
    
    botResponse(['message' => 'User unbanned successfully']);
}

function makeAdmin($pdo) {
    $user_id = $_GET['user_id'] ?? 0;
    
    if (!$user_id) {
        botError('User ID required');
    }
    
    $stmt = $pdo->prepare("UPDATE users SET is_admin = 1, admin_level = 9 WHERE id = ?");
    $stmt->execute([$user_id]);
    
    logAdminAction($pdo, 'make_admin', "Made user ID $user_id admin");
    
    botResponse(['message' => 'Admin rights granted']);
}

function removeAdmin($pdo) {
    $user_id = $_GET['user_id'] ?? 0;
    
    if (!$user_id) {
        botError('User ID required');
    }
    
    $stmt = $pdo->prepare("UPDATE users SET is_admin = 0, admin_level = 0 WHERE id = ?");
    $stmt->execute([$user_id]);
    
    logAdminAction($pdo, 'remove_admin', "Removed admin rights from user ID $user_id");
    
    botResponse(['message' => 'Admin rights removed']);
}

function getMatchesList($pdo) {
    $status = $_GET['status'] ?? 'all';
    
    $sql = "SELECT m.*, 
                   t1.name as team1_name, 
                   t2.name as team2_name,
                   mp.name as map_name
            FROM matches m
            LEFT JOIN teams t1 ON m.team1_id = t1.id
            LEFT JOIN teams t2 ON m.team2_id = t2.id
            LEFT JOIN maps mp ON m.map_id = mp.id";
    
    if ($status != 'all') {
        $sql .= " WHERE m.status = ?";
        $params = [$status];
    }
    
    $sql .= " ORDER BY m.start_time DESC LIMIT 50";
    
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params ?? []);
    $matches = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    botResponse(['matches' => $matches]);
}

function createMatch($pdo) {
    $data = json_decode(file_get_contents('php://input'), true);
    
    $team1_id = $data['team1_id'] ?? 0;
    $team2_id = $data['team2_id'] ?? 0;
    $map_id = $data['map_id'] ?? 0;
    $start_time = $data['start_time'] ?? date('Y-m-d H:i:s');
    $status = $data['status'] ?? 'scheduled';
    
    if (!$team1_id || !$team2_id) {
        botError('Team IDs required');
    }
    
    $stmt = $pdo->prepare("
        INSERT INTO matches (team1_id, team2_id, map_id, start_time, status) 
        VALUES (?, ?, ?, ?, ?)
    ");
    $stmt->execute([$team1_id, $team2_id, $map_id, $start_time, $status]);
    
    $match_id = $pdo->lastInsertId();
    
    logAdminAction($pdo, 'create_match', "Created match ID $match_id");
    
    botResponse([
        'message' => 'Match created successfully',
        'match_id' => $match_id
    ]);
}

function updateMatch($pdo) {
    $data = json_decode(file_get_contents('php://input'), true);
    
    $match_id = $data['match_id'] ?? 0;
    if (!$match_id) {
        botError('Match ID required');
    }
    
    $fields = [];
    $params = [];
    
    $allowed = ['team1_id', 'team2_id', 'map_id', 'start_time', 'status', 'score1', 'score2', 'winner_id'];
    foreach ($allowed as $field) {
        if (isset($data[$field])) {
            $fields[] = "$field = ?";
            $params[] = $data[$field];
        }
    }
    
    if (empty($fields)) {
        botError('No fields to update');
    }
    
    $params[] = $match_id;
    $stmt = $pdo->prepare("UPDATE matches SET " . implode(', ', $fields) . " WHERE id = ?");
    $stmt->execute($params);
    
    logAdminAction($pdo, 'update_match', "Updated match ID $match_id");
    
    botResponse(['message' => 'Match updated successfully']);
}

function deleteMatch($pdo) {
    $match_id = $_GET['match_id'] ?? 0;
    
    if (!$match_id) {
        botError('Match ID required');
    }
    
    $stmt = $pdo->prepare("DELETE FROM matches WHERE id = ?");
    $stmt->execute([$match_id]);
    
    logAdminAction($pdo, 'delete_match', "Deleted match ID $match_id");
    
    botResponse(['message' => 'Match deleted successfully']);
}

function setMatchScore($pdo) {
    $data = json_decode(file_get_contents('php://input'), true);
    
    $match_id = $data['match_id'] ?? 0;
    $score1 = $data['score1'] ?? 0;
    $score2 = $data['score2'] ?? 0;
    
    if (!$match_id) {
        botError('Match ID required');
    }
    
    $winner_id = 0;
    if ($score1 > $score2) {
        $stmt = $pdo->prepare("SELECT team1_id FROM matches WHERE id = ?");
        $stmt->execute([$match_id]);
        $winner_id = $stmt->fetch(PDO::FETCH_ASSOC)['team1_id'];
    } elseif ($score2 > $score1) {
        $stmt = $pdo->prepare("SELECT team2_id FROM matches WHERE id = ?");
        $stmt->execute([$match_id]);
        $winner_id = $stmt->fetch(PDO::FETCH_ASSOC)['team2_id'];
    }
    
    $stmt = $pdo->prepare("
        UPDATE matches 
        SET score1 = ?, score2 = ?, winner_id = ?, status = 'finished' 
        WHERE id = ?
    ");
    $stmt->execute([$score1, $score2, $winner_id, $match_id]);
    
    logAdminAction($pdo, 'set_score', "Set score $score1:$score2 for match ID $match_id");
    
    botResponse(['message' => 'Score set successfully']);
}

function getTournamentsList($pdo) {
    $stmt = $pdo->prepare("
        SELECT * FROM tournaments 
        ORDER BY start_time DESC 
        LIMIT 50
    ");
    $stmt->execute();
    $tournaments = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    botResponse(['tournaments' => $tournaments]);
}

function createTournament($pdo) {
    $data = json_decode(file_get_contents('php://input'), true);
    
    $name = $data['name'] ?? '';
    $start_time = $data['start_time'] ?? date('Y-m-d H:i:s');
    $preview = $data['preview'] ?? '';
    $participants = $data['participants'] ?? 0;
    
    if (empty($name)) {
        botError('Tournament name required');
    }
    
    $stmt = $pdo->prepare("
        INSERT INTO tournaments (name, start_time, preview, participants, status) 
        VALUES (?, ?, ?, ?, 'Не начатый')
    ");
    $stmt->execute([$name, $start_time, $preview, $participants]);
    
    $tournament_id = $pdo->lastInsertId();
    
    logAdminAction($pdo, 'create_tournament', "Created tournament ID $tournament_id");
    
    botResponse([
        'message' => 'Tournament created successfully',
        'tournament_id' => $tournament_id
    ]);
}

function updateTournament($pdo) {
    $data = json_decode(file_get_contents('php://input'), true);
    
    $tournament_id = $data['tournament_id'] ?? 0;
    if (!$tournament_id) {
        botError('Tournament ID required');
    }
    
    $fields = [];
    $params = [];
    
    $allowed = ['name', 'start_time', 'status', 'preview', 'participants', 'teams', 'selected_map_id'];
    foreach ($allowed as $field) {
        if (isset($data[$field])) {
            $fields[] = "$field = ?";
            $params[] = $data[$field];
        }
    }
    
    if (empty($fields)) {
        botError('No fields to update');
    }
    
    $params[] = $tournament_id;
    $stmt = $pdo->prepare("UPDATE tournaments SET " . implode(', ', $fields) . " WHERE id = ?");
    $stmt->execute($params);
    
    logAdminAction($pdo, 'update_tournament', "Updated tournament ID $tournament_id");
    
    botResponse(['message' => 'Tournament updated successfully']);
}

function deleteTournament($pdo) {
    $tournament_id = $_GET['tournament_id'] ?? 0;
    
    if (!$tournament_id) {
        botError('Tournament ID required');
    }
    
    $stmt = $pdo->prepare("DELETE FROM tournaments WHERE id = ?");
    $stmt->execute([$tournament_id]);
    
    logAdminAction($pdo, 'delete_tournament', "Deleted tournament ID $tournament_id");
    
    botResponse(['message' => 'Tournament deleted successfully']);
}

function startTournament($pdo) {
    $tournament_id = $_GET['tournament_id'] ?? 0;
    
    if (!$tournament_id) {
        botError('Tournament ID required');
    }
    
    $stmt = $pdo->prepare("UPDATE tournaments SET status = 'В игре' WHERE id = ?");
    $stmt->execute([$tournament_id]);
    
    logAdminAction($pdo, 'start_tournament', "Started tournament ID $tournament_id");
    
    botResponse(['message' => 'Tournament started']);
}

function getStats($pdo) {
    // Общая статистика
    $stats = [];
    
    // Количество пользователей
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM users");
    $stats['total_users'] = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
    
    // Новые за сегодня
    $stmt = $pdo->query("SELECT COUNT(*) as today FROM users WHERE DATE(created_at) = CURDATE()");
    $stats['new_users_today'] = $stmt->fetch(PDO::FETCH_ASSOC)['today'];
    
    // Онлайн (за последние 15 минут)
    $stmt = $pdo->prepare("SELECT COUNT(DISTINCT user_id) as online FROM user_logins WHERE login_time > DATE_SUB(NOW(), INTERVAL 15 MINUTE)");
    $stmt->execute();
    $stats['online_users'] = $stmt->fetch(PDO::FETCH_ASSOC)['online'];
    
    // Матчи
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM matches");
    $stats['total_matches'] = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
    
    $stmt = $pdo->query("SELECT COUNT(*) as active FROM matches WHERE status = 'active'");
    $stats['active_matches'] = $stmt->fetch(PDO::FETCH_ASSOC)['active'];
    
    // Турниры
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM tournaments");
    $stats['total_tournaments'] = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
    
    $stmt = $pdo->query("SELECT COUNT(*) as active FROM tournaments WHERE status = 'В игре'");
    $stats['active_tournaments'] = $stmt->fetch(PDO::FETCH_ASSOC)['active'];
    
    // Команды
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM teams");
    $stats['total_teams'] = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
    
    // Баны
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM banned_users");
    $stats['total_bans'] = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
    
    // Админы
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM users WHERE is_admin = 1");
    $stats['total_admins'] = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
    
    botResponse(['stats' => $stats]);
}

function getBannedList($pdo) {
    $stmt = $pdo->prepare("
        SELECT b.*, u.username 
        FROM banned_users b
        LEFT JOIN users u ON b.steam_id = u.steam_id
        ORDER BY b.ban_date DESC
    ");
    $stmt->execute();
    $bans = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    botResponse(['bans' => $bans]);
}

function getReportsList($pdo) {
    // Если у вас есть таблица репортов
    $stmt = $pdo->prepare("
        SELECT * FROM reports 
        WHERE status = 'pending'
        ORDER BY created_at DESC
        LIMIT 20
    ");
    $stmt->execute();
    $reports = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    botResponse(['reports' => $reports]);
}

function resolveReport($pdo) {
    $data = json_decode(file_get_contents('php://input'), true);
    
    $report_id = $data['report_id'] ?? 0;
    $action = $data['action'] ?? 'dismiss';
    
    if (!$report_id) {
        botError('Report ID required');
    }
    
    $status = $action == 'ban' ? 'banned' : 'resolved';
    
    $stmt = $pdo->prepare("UPDATE reports SET status = ?, resolved_at = NOW() WHERE id = ?");
    $stmt->execute([$status, $report_id]);
    
    logAdminAction($pdo, 'resolve_report', "Resolved report ID $report_id with action $action");
    
    botResponse(['message' => 'Report resolved']);
}

function logAdminAction($pdo, $action, $details) {
    $admin_id = $_GET['admin_id'] ?? 0;
    
    $stmt = $pdo->prepare("
        INSERT INTO admin_logs (admin_id, action, details, ip_address, created_at) 
        VALUES (?, ?, ?, ?, NOW())
    ");
    $stmt->execute([$admin_id, $action, $details, $_SERVER['REMOTE_ADDR'] ?? '']);
}
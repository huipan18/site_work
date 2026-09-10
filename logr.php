<?php
// logger.php - File Content Logger with History & Downloads
session_start();

// Set timezone (adjust as needed)
date_default_timezone_set('UTC');

// Initialize session storage for selections and history
if (!isset($_SESSION['selected_items'])) {
    $_SESSION['selected_items'] = [];
}
if (!isset($_SESSION['log_history'])) {
    $_SESSION['log_history'] = [];
}

$current_dir = isset($_GET['dir']) ? realpath($_GET['dir']) : realpath('.');
$base_dir = realpath('.');

// Security: Ensure we stay within the project directory
if (strpos($current_dir, $base_dir) !== 0) {
    $current_dir = $base_dir;
}

// Handle AJAX requests
if (isset($_POST['action'])) {
    header('Content-Type: application/json');
    
    switch ($_POST['action']) {
        case 'toggle':
            $path = $_POST['path'];
            if (in_array($path, $_SESSION['selected_items'])) {
                $_SESSION['selected_items'] = array_diff($_SESSION['selected_items'], [$path]);
                echo json_encode(['status' => 'removed']);
            } else {
                $_SESSION['selected_items'][] = $path;
                echo json_encode(['status' => 'added']);
            }
            exit;
            
        case 'create_log':
            $selected = $_SESSION['selected_items'];
            if (empty($selected)) {
                echo json_encode(['error' => 'No files or folders selected']);
                exit;
            }
            
            $log_content = generateLog($selected, $base_dir);
            $timestamp = date('Y-m-d_H-i-s');
            $filename = 'log_' . $timestamp . '.txt';
            file_put_contents($filename, $log_content);
            
            // Add to history
            $file_size = filesize($filename);
            array_unshift($_SESSION['log_history'], [
                'filename' => $filename,
                'timestamp' => $timestamp,
                'size' => formatFileSize($file_size),
                'items_count' => count($selected),
                'created' => date('Y-m-d H:i:s')
            ]);
            
            // Keep only last 20 logs in history
            if (count($_SESSION['log_history']) > 20) {
                array_pop($_SESSION['log_history']);
            }
            
            echo json_encode([
                'success' => true, 
                'filename' => $filename,
                'size' => formatFileSize($file_size)
            ]);
            exit;
            
        case 'get_directory':
            echo json_encode(['html' => generateFileList($current_dir, $base_dir)]);
            exit;
            
        case 'get_history':
            echo json_encode(['html' => generateHistoryList()]);
            exit;
            
        case 'delete_log':
            $filename = $_POST['filename'];
            // Security: prevent directory traversal
            $filename = basename($filename);
            if (file_exists($filename) && strpos($filename, 'log_') === 0 && pathinfo($filename, PATHINFO_EXTENSION) == 'txt') {
                unlink($filename);
                // Remove from history
                foreach ($_SESSION['log_history'] as $key => $log) {
                    if ($log['filename'] === $filename) {
                        unset($_SESSION['log_history'][$key]);
                        break;
                    }
                }
                $_SESSION['log_history'] = array_values($_SESSION['log_history']);
                echo json_encode(['success' => true]);
            } else {
                echo json_encode(['error' => 'File not found or access denied']);
            }
            exit;
    }
}

// Handle file downloads
if (isset($_GET['download'])) {
    $filename = basename($_GET['download']);
    if (file_exists($filename) && strpos($filename, 'log_') === 0 && pathinfo($filename, PATHINFO_EXTENSION) == 'txt') {
        header('Content-Type: text/plain');
        header('Content-Disposition: attachment; filename="' . $filename . '"');
        header('Content-Length: ' . filesize($filename));
        header('Cache-Control: no-cache');
        readfile($filename);
        exit;
    } else {
        die('File not found or access denied');
    }
}

function formatFileSize($bytes) {
    if ($bytes >= 1048576) {
        return number_format($bytes / 1048576, 2) . ' MB';
    } elseif ($bytes >= 1024) {
        return number_format($bytes / 1024, 2) . ' KB';
    } else {
        return $bytes . ' bytes';
    }
}

function generateLog($selected_items, $base_dir) {
    $log = "===========================================\n";
    $log .= "CODE LOG\n";
    $log .= "Generated: " . date('Y-m-d H:i:s') . "\n";
    $log .= "Total Items: " . count($selected_items) . "\n";
    $log .= "===========================================\n\n";
    
    // Generate folder structure
    $log .= "📁 FOLDER STRUCTURE:\n";
    $log .= str_repeat("─", 50) . "\n";
    $log .= generateFolderStructure($base_dir, $base_dir, $selected_items);
    $log .= "\n\n";
    
    // Generate file contents
    $log .= "📄 FILE CONTENTS:\n";
    $log .= str_repeat("─", 50) . "\n\n";
    
    foreach ($selected_items as $item) {
        if (is_file($item)) {
            $log .= generateFileContent($item, $base_dir);
        } elseif (is_dir($item)) {
            $log .= generateDirectoryContents($item, $base_dir);
        }
    }
    
    return $log;
}

function generateFolderStructure($dir, $base_dir, $selected_items, $indent = '') {
    $output = '';
    $items = scandir($dir);
    
    foreach ($items as $item) {
        if ($item == '.' || $item == '..' || $item == 'logger.php' || 
            strpos($item, 'log_') === 0 && pathinfo($item, PATHINFO_EXTENSION) == 'txt') {
            continue;
        }
        
        $path = $dir . DIRECTORY_SEPARATOR . $item;
        $relative_path = str_replace($base_dir . DIRECTORY_SEPARATOR, '', $path);
        
        if (is_dir($path)) {
            $is_selected = in_array($path, $selected_items);
            $marker = $is_selected ? "✓" : " ";
            $output .= $indent . "[$marker] 📁 $item/\n";
            $output .= generateFolderStructure($path, $base_dir, $selected_items, $indent . '    ');
        } else {
            $is_selected = in_array($path, $selected_items);
            $marker = $is_selected ? "✓" : " ";
            $output .= $indent . "[$marker] 📄 $item\n";
        }
    }
    
    return $output;
}

function generateFileContent($file_path, $base_dir) {
    $relative = str_replace($base_dir . DIRECTORY_SEPARATOR, '', $file_path);
    $content = file_get_contents($file_path);
    $ext = pathinfo($file_path, PATHINFO_EXTENSION);
    
    $output = str_repeat("=", 80) . "\n";
    $output .= "FILE: $relative\n";
    $output .= str_repeat("=", 80) . "\n";
    $output .= "```$ext\n";
    $output .= $content;
    if (substr($content, -1) !== "\n") {
        $output .= "\n";
    }
    $output .= "```\n\n";
    
    return $output;
}

function generateDirectoryContents($dir, $base_dir) {
    $output = '';
    $files = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($dir, RecursiveDirectoryIterator::SKIP_DOTS)
    );
    
    foreach ($files as $file) {
        if ($file->isFile()) {
            $output .= generateFileContent($file->getPathname(), $base_dir);
        }
    }
    
    return $output;
}

function generateFileList($dir, $base_dir) {
    $html = '';
    $items = scandir($dir);
    
    if ($dir != $base_dir) {
        $parent = dirname($dir);
        $html .= '<div class="item folder-item" data-path="' . htmlspecialchars($parent) . '" data-type="navigate">';
        $html .= '<span class="icon">📂</span>';
        $html .= '<span class="name">.. (parent directory)</span>';
        $html .= '</div>';
    }
    
    $folders = [];
    $files = [];
    
    foreach ($items as $item) {
        if ($item == '.' || $item == '..' || $item == 'logger.php') {
            continue;
        }
        
        $path = $dir . DIRECTORY_SEPARATOR . $item;
        
        if (is_dir($path)) {
            $folders[] = ['name' => $item, 'path' => $path];
        } else {
            if (strpos($item, 'log_') !== 0 || pathinfo($item, PATHINFO_EXTENSION) != 'txt') {
                $files[] = ['name' => $item, 'path' => $path];
            }
        }
    }
    
    // Sort alphabetically
    usort($folders, function($a, $b) { return strcasecmp($a['name'], $b['name']); });
    usort($files, function($a, $b) { return strcasecmp($a['name'], $b['name']); });
    
    // Display folders first
    foreach ($folders as $folder) {
        $is_selected = in_array($folder['path'], $_SESSION['selected_items']);
        $selected_class = $is_selected ? 'selected' : '';
        
        $html .= '<div class="item folder-item ' . $selected_class . '" data-path="' . htmlspecialchars($folder['path']) . '" data-type="folder">';
        $html .= '<span class="icon">📁</span>';
        $html .= '<span class="name">' . htmlspecialchars($folder['name']) . '/</span>';
        $html .= '<span class="select-badge">' . ($is_selected ? '✓ SELECTED' : '') . '</span>';
        $html .= '<span class="action-hint">[Click to open | Alt+Click to select]</span>';
        $html .= '</div>';
    }
    
    // Then display files
    foreach ($files as $file) {
        $is_selected = in_array($file['path'], $_SESSION['selected_items']);
        $selected_class = $is_selected ? 'selected' : '';
        $ext = pathinfo($file['name'], PATHINFO_EXTENSION);
        
        $html .= '<div class="item file-item ' . $selected_class . '" data-path="' . htmlspecialchars($file['path']) . '" data-type="file">';
        $html .= '<span class="icon">📄</span>';
        $html .= '<span class="name">' . htmlspecialchars($file['name']) . '</span>';
        $html .= '<span class="extension">.' . htmlspecialchars($ext) . '</span>';
        $html .= '<span class="select-badge">' . ($is_selected ? '✓ SELECTED' : '') . '</span>';
        $html .= '</div>';
    }
    
    if (empty($folders) && empty($files)) {
        $html .= '<div class="empty-state">📭 This directory is empty</div>';
    }
    
    return $html;
}

function generateHistoryList() {
    if (empty($_SESSION['log_history'])) {
        return '<div class="empty-state">📝 No logs created yet</div>';
    }
    
    $html = '';
    foreach ($_SESSION['log_history'] as $log) {
        $html .= '<div class="history-item">';
        $html .= '<div class="history-info">';
        $html .= '<span class="history-icon">📋</span>';
        $html .= '<div class="history-details">';
        $html .= '<div class="history-filename">' . htmlspecialchars($log['filename']) . '</div>';
        $html .= '<div class="history-meta">';
        $html .= 'Created: ' . $log['created'] . ' | ';
        $html .= 'Size: ' . $log['size'] . ' | ';
        $html .= 'Items: ' . $log['items_count'];
        $html .= '</div>';
        $html .= '</div>';
        $html .= '</div>';
        $html .= '<div class="history-actions">';
        $html .= '<a href="?download=' . urlencode($log['filename']) . '" class="btn btn-download" download>💾 Download</a>';
        $html .= '<button class="btn btn-delete" onclick="deleteLog(\'' . htmlspecialchars($log['filename']) . '\')">🗑️ Delete</button>';
        $html .= '</div>';
        $html .= '</div>';
    }
    
    return $html;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Logger Pro</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 20px;
        }
        
        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr;
            }
        }
        
        .main-panel, .history-panel {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .history-panel {
            max-height: calc(100vh - 40px);
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 25px;
        }
        
        .header h1 {
            font-size: 1.5em;
            margin-bottom: 5px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 0.85em;
        }
        
        .toolbar {
            padding: 15px 25px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .current-path {
            font-family: 'Courier New', monospace;
            background: white;
            padding: 8px 15px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
            flex: 1;
            min-width: 200px;
            font-size: 0.85em;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.85em;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            white-space: nowrap;
        }
        
        .btn-create {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-create:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        
        .btn-clear {
            background: #6c757d;
            color: white;
        }
        
        .btn-clear:hover {
            background: #5a6268;
        }
        
        .btn-download {
            background: #28a745;
            color: white;
            font-size: 0.8em;
            padding: 6px 12px;
        }
        
        .btn-download:hover {
            background: #218838;
            transform: translateY(-1px);
        }
        
        .btn-delete {
            background: #dc3545;
            color: white;
            font-size: 0.8em;
            padding: 6px 12px;
        }
        
        .btn-delete:hover {
            background: #c82333;
        }
        
        .file-list {
            padding: 15px;
            max-height: 60vh;
            overflow-y: auto;
        }
        
        .item {
            display: flex;
            align-items: center;
            padding: 10px 15px;
            margin: 3px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }
        
        .item:hover {
            background: #f8f9fa;
            border-color: #dee2e6;
            transform: translateX(5px);
        }
        
        .item.selected {
            background: linear-gradient(135deg, #e7f3ff 0%, #f0e7ff 100%);
            border-color: #667eea;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
        }
        
        .icon {
            font-size: 1.2em;
            margin-right: 10px;
            width: 25px;
            text-align: center;
        }
        
        .name {
            flex: 1;
            font-weight: 500;
            font-size: 0.9em;
        }
        
        .extension {
            color: #6c757d;
            font-size: 0.8em;
            margin-left: 8px;
            background: #f8f9fa;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }
        
        .select-badge {
            margin-left: 8px;
            color: #667eea;
            font-weight: bold;
            font-size: 0.8em;
            background: rgba(102, 126, 234, 0.1);
            padding: 2px 8px;
            border-radius: 4px;
        }
        
        .action-hint {
            margin-left: 8px;
            color: #adb5bd;
            font-size: 0.75em;
            font-style: italic;
        }
        
        .status-bar {
            padding: 10px 25px;
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #6c757d;
            font-size: 0.85em;
        }
        
        .history-list {
            padding: 15px;
            overflow-y: auto;
            flex: 1;
        }
        
        .history-item {
            padding: 12px;
            margin: 5px 0;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            background: #f8f9fa;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }
        
        .history-info {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            min-width: 0;
        }
        
        .history-icon {
            font-size: 1.5em;
        }
        
        .history-details {
            min-width: 0;
        }
        
        .history-filename {
            font-weight: 600;
            color: #333;
            font-size: 0.85em;
            word-break: break-all;
        }
        
        .history-meta {
            font-size: 0.75em;
            color: #6c757d;
            margin-top: 2px;
        }
        
        .history-actions {
            display: flex;
            gap: 5px;
            flex-shrink: 0;
        }
        
        .empty-state {
            text-align: center;
            padding: 30px;
            color: #adb5bd;
            font-size: 1em;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            z-index: 1000;
            animation: slideIn 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .notification.success {
            background: #28a745;
        }
        
        .notification.error {
            background: #dc3545;
        }
        
        .notification .download-link {
            color: white;
            font-weight: bold;
            text-decoration: underline;
            margin-left: 10px;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .loading-overlay {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .refresh-btn {
            background: #17a2b8;
            color: white;
        }
        
        .refresh-btn:hover {
            background: #138496;
        }
        
        @media (max-width: 768px) {
            .toolbar {
                flex-direction: column;
                align-items: stretch;
            }
            
            .history-actions {
                flex-direction: column;
            }
            
            .header h1 {
                font-size: 1.2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-panel">
            <div class="header">
                <h1>📁 Code Logger Pro</h1>
                <p>Select files & folders • Create logs • Download anytime</p>
            </div>
            
            <div class="toolbar">
                <div class="current-path" id="currentPath">/</div>
                <button class="btn btn-clear" onclick="clearSelection()">🗑️ Clear All</button>
                <button class="btn btn-create" onclick="createLog()">📝 Create Log</button>
            </div>
            
            <div class="file-list" id="fileList">
                <div class="empty-state">Loading...</div>
            </div>
            
            <div class="status-bar">
                <span id="selectionCount">Selected items: <strong>0</strong></span>
                <button class="btn refresh-btn" onclick="refreshAll()">🔄 Refresh</button>
            </div>
        </div>
        
        <div class="history-panel">
            <div class="header">
                <h1>📋 Log History</h1>
                <p>Previously created logs</p>
            </div>
            
            <div class="history-list" id="historyList">
                <div class="empty-state">Loading history...</div>
            </div>
        </div>
    </div>
    
    <script>
        let currentDir = '';
        
        function loadDirectory(dir) {
            const fileList = document.getElementById('fileList');
            fileList.classList.add('loading-overlay');
            currentDir = dir || currentDir;
            
            const formData = new FormData();
            formData.append('action', 'get_directory');
            
            fetch('logger.php?dir=' + encodeURIComponent(currentDir), {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                fileList.innerHTML = data.html;
                document.getElementById('currentPath').textContent = currentDir;
                fileList.classList.remove('loading-overlay');
                attachClickHandlers();
                updateSelectionCount();
            })
            .catch(error => {
                fileList.innerHTML = '<div class="empty-state">❌ Error loading directory</div>';
                fileList.classList.remove('loading-overlay');
            });
        }
        
        function loadHistory() {
            const formData = new FormData();
            formData.append('action', 'get_history');
            
            fetch('logger.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('historyList').innerHTML = data.html;
            })
            .catch(error => {
                document.getElementById('historyList').innerHTML = '<div class="empty-state">❌ Error loading history</div>';
            });
        }
        
        function attachClickHandlers() {
            document.querySelectorAll('.item').forEach(item => {
                item.addEventListener('click', function(e) {
                    const path = this.dataset.path;
                    const type = this.dataset.type;
                    
                    if (type === 'navigate') {
                        loadDirectory(path);
                    } else if (type === 'folder') {
                        if (e.altKey) {
                            toggleItem(path);
                        } else {
                            loadDirectory(path);
                        }
                    } else if (type === 'file') {
                        toggleItem(path);
                    }
                });
            });
        }
        
        function toggleItem(path) {
            const formData = new FormData();
            formData.append('action', 'toggle');
            formData.append('path', path);
            
            fetch('logger.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loadDirectory(currentDir);
            });
        }
        
        function createLog() {
            const createBtn = document.querySelector('.btn-create');
            createBtn.disabled = true;
            createBtn.textContent = 'Creating...';
            
            const formData = new FormData();
            formData.append('action', 'create_log');
            
            fetch('logger.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                createBtn.disabled = false;
                createBtn.textContent = '📝 Create Log';
                
                if (data.success) {
                    showNotification(
                        `✅ Log created: ${data.filename} (${data.size})`, 
                        'success',
                        data.filename
                    );
                    loadHistory();
                } else {
                    showNotification('❌ ' + data.error, 'error');
                }
            })
            .catch(error => {
                createBtn.disabled = false;
                createBtn.textContent = '📝 Create Log';
                showNotification('❌ Error creating log', 'error');
            });
        }
        
        function clearSelection() {
            const selectedItems = document.querySelectorAll('.item.selected');
            selectedItems.forEach(item => {
                toggleItem(item.dataset.path);
            });
        }
        
        function updateSelectionCount() {
            const count = document.querySelectorAll('.item.selected').length;
            document.getElementById('selectionCount').innerHTML = 'Selected items: <strong>' + count + '</strong>';
        }
        
        function deleteLog(filename) {
            if (!confirm('Are you sure you want to delete ' + filename + '?')) {
                return;
            }
            
            const formData = new FormData();
            formData.append('action', 'delete_log');
            formData.append('filename', filename);
            
            fetch('logger.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('🗑️ Log deleted: ' + filename, 'success');
                    loadHistory();
                } else {
                    showNotification('❌ ' + data.error, 'error');
                }
            });
        }
        
        function refreshAll() {
            loadDirectory(currentDir);
            loadHistory();
        }
        
        function showNotification(message, type, filename = null) {
            const notification = document.createElement('div');
            notification.className = 'notification ' + type;
            
            let content = message;
            if (filename && type === 'success') {
                content += ` <a href="?download=${encodeURIComponent(filename)}" class="download-link">⬇️ Download Now</a>`;
            }
            
            notification.innerHTML = content;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideIn 0.3s ease reverse';
                setTimeout(() => notification.remove(), 300);
            }, 5000);
        }
        
        // Initial load
        loadDirectory('.');
        loadHistory();
        
        // Refresh history periodically
        setInterval(loadHistory, 30000);
    </script>
</body>
</html>
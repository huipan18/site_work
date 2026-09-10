<?php
// logger.php - Source Code Logger & Backup Tool

$backupDirName = 'logger_backups';
$backupDir = __DIR__ . '/' . $backupDirName;

// ========================================================
// 1. Handle File Download (GET Request)
// ========================================================
if (isset($_GET['download'])) {
    $file = basename($_GET['download']);
    $path = $backupDir . '/' . $file;
    if (is_file($path)) {
        header('Content-Description: File Transfer');
        header('Content-Type: text/plain');
        header('Content-Disposition: attachment; filename="'.basename($path).'"');
        header('Expires: 0');
        header('Cache-Control: must-revalidate');
        header('Pragma: public');
        header('Content-Length: ' . filesize($path));
        readfile($path);
        exit;
    }
    die("File not found.");
}

// ========================================================
// 2. Helper: Generate Text Tree for the Log file
// ========================================================
function generateTextTree($dir, $prefix = '') {
    global $backupDirName;
    $tree = '';
    $items = scandir($dir);
    // Remove current/parent directory pointers and the backup folder itself
    $items = array_filter($items, function($item) use ($backupDirName) {
        return $item !== '.' && $item !== '..' && $item !== $backupDirName;
    });
    $items = array_values($items); // reindex array
    
    foreach ($items as $index => $item) {
        $path = $dir . '/' . $item;
        $isLast = ($index === count($items) - 1);
        $pointer = $isLast ? '└── ' : '├── ';
        $tree .= $prefix . $pointer . $item . PHP_EOL;
        
        if (is_dir($path)) {
            $extension = $isLast ? '    ' : '│   ';
            $tree .= generateTextTree($path, $prefix . $extension);
        }
    }
    return $tree;
}

// ========================================================
// 3. Handle Backup Generation (AJAX POST)
// ========================================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action']) && $_POST['action'] === 'backup') {
    header('Content-Type: application/json');
    
    $files = isset($_POST['files']) && is_array($_POST['files']) ? $_POST['files'] : [];
    
    // --- Part A: Folder Structure ---
    $logContent = "=================================================\n";
    $logContent .= " DIRECTORY STRUCTURE (Logged on " . date('Y-m-d H:i:s') . ")\n";
    $logContent .= "=================================================\n\n";
    $logContent .= basename(__DIR__) . "\n";
    $logContent .= generateTextTree(__DIR__);
    $logContent .= "\n\n";
    
    // --- Part B: Selected Source Codes ---
    $logContent .= "=================================================\n";
    $logContent .= " SOURCE CODES\n";
    $logContent .= "=================================================\n\n";
    
    foreach($files as $file) {
        // Basic sanitization to prevent directory traversal
        $file = str_replace(['../', '..\\'], '', $file);
        $filePath = __DIR__ . '/' . $file;
        
        // Skip logger.php to prevent logging the logger itself
        if (is_file($filePath) && basename($file) !== 'logger.php') {
            $logContent .= "-------------------------------------------------\n";
            $logContent .= " FILE: " . $file . "\n";
            $logContent .= "-------------------------------------------------\n";
            $logContent .= file_get_contents($filePath);
            $logContent .= "\n\n";
        }
    }
    
    // Create backup directory if it doesn't exist
    if (!is_dir($backupDir)) {
        mkdir($backupDir, 0755, true);
        // Secure the folder from being viewed directly on Hostinger
        file_put_contents($backupDir . '/.htaccess', "Deny from all");
    }
    
    // Save to Hostinger server
    $filename = 'logger_backup_' . date('Ymd_His') . '.txt';
    $filePath = $backupDir . '/' . $filename;
    file_put_contents($filePath, $logContent);
    
    // Send success response with download link
    echo json_encode(['success' => true, 'download_url' => '?download=' . urlencode($filename)]);
    exit;
}

// ========================================================
// 4. Helper: Build HTML Tree for the Frontend
// ========================================================
function buildHtmlTree($dir, $baseDir = '') {
    global $backupDirName;
    $html = '<ul class="tree-list">';
    $items = scandir($dir);
    natcasesort($items); // sort naturally (folders and files)
    
    foreach ($items as $item) {
        if ($item === '.' || $item === '..' || $item === $backupDirName) continue;
        
        $path = $dir . '/' . $item;
        $relPath = $baseDir ? $baseDir . '/' . $item : $item;
        
        // Hide this script from the UI
        if ($relPath === 'logger.php') continue;
        
        if (is_dir($path)) {
            $html .= '<li>';
            $html .= '<label class="folder-label">';
            $html .= '<input type="checkbox" class="folder-checkbox"> <span class="icon">📁</span> ' . htmlspecialchars($item);
            $html .= '</label>';
            $html .= buildHtmlTree($path, $relPath); // Recursive call for nested folders
            $html .= '</li>';
        } else {
            $html .= '<li>';
            $html .= '<label class="file-label">';
            $html .= '<input type="checkbox" class="file-checkbox" value="' . htmlspecialchars($relPath) . '"> <span class="icon">📄</span> ' . htmlspecialchars($item);
            $html .= '</label>';
            $html .= '</li>';
        }
    }
    $html .= '</ul>';
    return $html;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Source Code Logger</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 30px; }
        .container { max-width: 900px; margin: 0 auto; background: #fff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h1 { font-size: 24px; border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-top: 0; color: #007bff; }
        .tree-container { background: #fafafa; border: 1px solid #ddd; padding: 15px; border-radius: 4px; max-height: 500px; overflow-y: auto; margin-bottom: 20px; }
        ul.tree-list { list-style-type: none; padding-left: 20px; margin: 5px 0;}
        ul.tree-list > li { margin: 6px 0; }
        .tree-list label { cursor: pointer; display: inline-flex; align-items: center; user-select: none; }
        .tree-list label:hover { color: #007bff; }
        .icon { margin: 0 6px; font-size: 16px; }
        .folder-label { font-weight: bold; }
        .btn { background: #007bff; color: #fff; border: none; padding: 12px 24px; font-size: 15px; border-radius: 4px; cursor: pointer; transition: 0.3s; font-weight: bold;}
        .btn:hover { background: #0056b3; }
        .btn:disabled { background: #aaa; cursor: not-allowed; }
        .btn-clear { background: #6c757d; margin-left: 10px; }
        .btn-clear:hover { background: #5a6268; }
        .actions { display: flex; justify-content: space-between; align-items: center; }
        .status { font-size: 15px; color: #28a745; font-weight: bold; }
        .warning { background: #fff3cd; color: #856404; padding: 12px; border-left: 4px solid #ffeeba; margin-bottom: 20px; border-radius: 4px; font-size: 14px; }
    </style>
</head>
<body>

<div class="container">
    <h1>Source Code Logger</h1>
    <div class="warning">
        <strong>Security Notice:</strong> Keep this file safe! It exposes your server's source code. It is highly recommended to rename or delete this file from your Hostinger panel when you are not using it.
    </div>
    <p>Select the folders and files you want to include in the backup. Your selection will be remembered next time you open this page.</p>
    
    <div class="tree-container">
        <!-- Root list without left padding -->
        <ul class="tree-list" style="padding-left: 0;">
            <?php echo buildHtmlTree(__DIR__); ?>
        </ul>
    </div>

    <div class="actions">
        <div>
            <button class="btn" id="generateBtn" onclick="generateBackup()">Generate & Download Log</button>
            <button class="btn btn-clear" onclick="clearSelection()">Clear Selection</button>
        </div>
        <div class="status" id="statusText"></div>
    </div>
</div>

<script>
    const STORE_KEY = 'logger_file_selection';

    document.addEventListener('DOMContentLoaded', () => {
        restoreSelection();

        // When a folder checkbox is clicked -> check/uncheck all files inside it
        document.querySelectorAll('.folder-checkbox').forEach(folder => {
            folder.addEventListener('change', function() {
                const isChecked = this.checked;
                const li = this.closest('li');
                li.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    cb.checked = isChecked;
                });
                saveSelection();
                updateParentFolders();
            });
        });

        // When a single file checkbox is clicked -> save and update folder states
        document.querySelectorAll('.file-checkbox').forEach(file => {
            file.addEventListener('change', function() {
                saveSelection();
                updateParentFolders();
            });
        });
    });

    // Save selected files to browser's LocalStorage
    function saveSelection() {
        const selected = [];
        document.querySelectorAll('.file-checkbox:checked').forEach(cb => {
            selected.push(cb.value);
        });
        localStorage.setItem(STORE_KEY, JSON.stringify(selected));
    }

    // Restore selection on fresh page load
    function restoreSelection() {
        const saved = localStorage.getItem(STORE_KEY);
        if (saved) {
            try {
                const selected = JSON.parse(saved);
                document.querySelectorAll('.file-checkbox').forEach(cb => {
                    if (selected.includes(cb.value)) {
                        cb.checked = true;
                    }
                });
                updateParentFolders();
            } catch(e) { console.error("Could not parse saved selection."); }
        }
    }

    // Smart logic to make folder checkboxes indeterminate [-] or checked [✓] based on contents
    function updateParentFolders() {
        document.querySelectorAll('.folder-checkbox').forEach(folder => {
            const li = folder.closest('li');
            const childFiles = li.querySelectorAll('.file-checkbox');
            if(childFiles.length > 0) {
                const checkedFiles = li.querySelectorAll('.file-checkbox:checked');
                if(checkedFiles.length === 0) {
                    folder.checked = false;
                    folder.indeterminate = false;
                } else if (checkedFiles.length === childFiles.length) {
                    folder.checked = true;
                    folder.indeterminate = false;
                } else {
                    folder.checked = false;
                    folder.indeterminate = true; // Shows as a dash [-] in modern browsers
                }
            }
        });
    }

    // Clear all checkboxes
    function clearSelection() {
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
            cb.indeterminate = false;
        });
        localStorage.removeItem(STORE_KEY);
    }

    // AJAX call to send files to PHP, save to Hostinger, and download
    function generateBackup() {
        const selected = [];
        document.querySelectorAll('.file-checkbox:checked').forEach(cb => {
            selected.push(cb.value);
        });

        if (selected.length === 0) {
            alert('Please select at least one file to backup.');
            return;
        }

        const btn = document.getElementById('generateBtn');
        const status = document.getElementById('statusText');
        
        btn.disabled = true;
        btn.innerText = 'Generating...';
        status.innerText = 'Processing your files on server...';

        const formData = new FormData();
        formData.append('action', 'backup');
        selected.forEach(file => { formData.append('files[]', file); });

        // Send to itself (logger.php)
        fetch('logger.php', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            btn.disabled = false;
            btn.innerText = 'Generate & Download Log';
            if (data.success) {
                status.innerText = 'Download started!';
                // Trigger file download in browser
                window.location.href = data.download_url;
                setTimeout(() => { status.innerText = ''; }, 4000);
            } else {
                alert('Error generating backup.');
                status.innerText = '';
            }
        })
        .catch(err => {
            console.error(err);
            alert('An error occurred. Check browser console.');
            btn.disabled = false;
            btn.innerText = 'Generate & Download Log';
            status.innerText = '';
        });
    }
</script>
</body>
</html>
<?php
declare(strict_types=1);
// Optional migration bridge. CLI only; never served by the Flask app.
if (PHP_SAPI !== 'cli') { http_response_code(404); exit('Page Not Found'); }
if ($argc !== 3) { fwrite(STDERR,"Usage: php export_mysql.php OLD_PROJECT_FOLDER PRIVATE_OUTPUT.json\n"); exit(1); }
try {
    $root=realpath($argv[1]);
    if ($root===false || !is_file($root.'/config.php')) { throw new RuntimeException(); }
    if (file_exists($argv[2])) { fwrite(STDERR,"Output already exists; choose a new private filename.\n"); exit(1); }
    $config=require $root.'/config.php';
    $db=$config['database'];
    $pdo=new PDO('mysql:host='.$db['host'].';port='.($db['port']??3306).';dbname='.$db['name'].';charset=utf8mb4',$db['username'],$db['password'],[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
    $pdo->exec('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ');
    $pdo->beginTransaction();
    $export=['format'=>'pejour-mysql-v1','encryption_key'=>$config['encryption_key'],'tables'=>[]];
    // Fixed allowlist: no browser or CLI value is inserted into an SQL query.
    foreach (['users','security_answers','password_history','activity_log','security_flags','ip_blocks','otps','journal_entries'] as $table) {
        $queries=['users'=>'SELECT * FROM users','security_answers'=>'SELECT * FROM security_answers','password_history'=>'SELECT * FROM password_history','activity_log'=>'SELECT * FROM activity_log','security_flags'=>'SELECT * FROM security_flags','ip_blocks'=>'SELECT * FROM ip_blocks','otps'=>'SELECT * FROM otps','journal_entries'=>'SELECT * FROM journal_entries'];
        $statement=$pdo->prepare($queries[$table]);$statement->execute();$export['tables'][$table]=$statement->fetchAll();
    }
    // Older builds may not have the ninth table; users' counters remain available.
    try {$statement=$pdo->prepare('SELECT * FROM login_attempt_state');$statement->execute();$export['tables']['login_attempt_state']=$statement->fetchAll();} catch(PDOException $error) {$export['tables']['login_attempt_state']=[];}
    $pdo->commit();
    file_put_contents($argv[2],json_encode($export,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE));
    echo "Private export saved. It includes personal data and an encryption key. Do not share or commit it.\n";
} catch(Throwable $error) {fwrite(STDERR,"Export failed. Check the old config and MySQL connection. No credentials were printed.\n");exit(1);}

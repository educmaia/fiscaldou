Making POST request to: https://inlabs.in.gov.br/logar.php
[DEBUG] Login response status: 200
[DEBUG] Response headers: {'Date': 'Sat, 13 Sep 2025 20:05:53 GMT', 'Content-Type': 'text/html; charset=utf-8', 'Connection': 'keep-alive', 'Vary': 'Accept-Encoding', 'Expires': 'Sat, 26 Jul 1997 05:00:00 GMT', 'Cache-Control': 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0', 'Pragma': 'no-cache', 'Content-Encoding': 'gzip', 'Transfer-Encoding': 'chunked'}
[DEBUG] Response cookies: {'PHPSESSID': 'rrg6jek9nk5nhih1fglcngam4g', 'inlabs*session_cookie': 'b3d1b54fdc53ccf9c0e86dc26cd20aa5eb562f54', 'TS016f630c': '0123313e820ef74082d51a71d7d64976b1bc5a8ff9b5e21e6347fe53a403727fada9b99bf8e557ba955a63b5418c20cc4c185f958576bac65db1247c02fa224f36ec215380e2f28a1248511dcae38229362a5816c9'}
[DEBUG] ✅ INLABS login successful.
[DEBUG] Testing access to main INLABS interface...
[DEBUG] Main interface status: 200
[DEBUG] ✅ Successfully logged into INLABS interface
[DEBUG] Attempting to download DOU for date: 2025-09-13
[DEBUG] Sections to download: DO1
[DEBUG] Session cookie exists: True
[DEBUG] Cookie length: 40 chars
[DEBUG] Downloading 2025-09-13-DO1.zip...
[DEBUG] Full download URL: https://inlabs.in.gov.br/index.php?p=2025-09-13&dl=2025-09-13-DO1.zip
[DEBUG] All session cookies: PHPSESSID=rrg6jek9nk5nhih1fglcngam4g; inlabs_session_cookie=b3d1b54fdc53ccf9c0e86dc26cd20aa5eb562f54; TS016f630c=0123313e820ef74082d51a71d7d64976b1bc5a8ff9b5e21e6347fe53a403727fada9b99bf8e557ba955a63b5418c20cc4c185f958576bac65db1247c02fa224f36ec215380e2f28a1248511dcae38229362a5816c9
[DEBUG] Headers: {'Cookie': 'PHPSESSID=rrg6jek9nk5nhih1fglcngam4g; inlabs_session_cookie=b3d1b54fdc53ccf9c0e86dc26cd20aa5eb562f54; TS016f630c=0123313e820ef74082d51a71d7d64976b1bc5a8ff9b5e21e6347fe53a403727fada9b99bf8e557ba955a63b5418c20cc4c185f958576bac65db1247c02fa224f36ec215380e2f28a1248511dcae38229362a5816c9', 'origem': '736372697074', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://inlabs.in.gov.br/index.php', 'Accept': 'application/zip,*/\_'}
[DEBUG] Making GET request to INLABS...
[DEBUG] Attempting direct session.get() first...
[DEBUG] Response for DO1: 200, Content-Length: 36091
[DEBUG] Content-Type: text/html; charset=utf-8
[DEBUG] First 50 bytes: b'<!DOCTYPE html>\r\n<html>\r\n<head>\r\n<title>Imprensa N'
[DEBUG] ZIP signature check for DO1: b'<!DO' (should start with PK)
[ERROR] ❌ Downloaded content for DO1 is NOT a valid ZIP file!
[ERROR] Expected: PK signature (50 4B), Got: b'<!DO'
[ERROR] This suggests INLABS returned an error page instead of a ZIP file
[DEBUG] ===== ACTUAL CONTENT RECEIVED =====
[DEBUG] <!DOCTYPE html>

<html>
<head>
<title>Imprensa Nacional - INLABS</title>
<link rel="stylesheet" href="css/bootstrap.min.css">
<script src="js/bootstrap.min.js"></script>
<link rel="icon" href="img/favicon.ico" type="image/x-icon" />
<link rel="shortcut icon" href="img/favicon.ico" type="image/x-icon" />
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
<link rel="stylesheet" href="css/font-awesome.min.css"> 
<link rel="stylesheet" href="css/styles2.css"> 
<link rel="stylesheet" href="css/styles3.css">
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=UA-149577637-4"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'UA-149577637-4');
</script>
</head><body class="navbar-normal">
<div class="container">
<div class="row">
[DEBUG] ===== END CONTENT =====
[ERROR] 🚨 INLABS returned an HTML page instead of ZIP! Trying alternative URLs...
[DEBUG] Trying alternative URL: https://inlabs.in.gov.br/files/2025-09-13-DO1.zip
[DEBUG] Alt URL status: 404
No files downloaded today.

2025-09-13T20:06:12.950Z [info] xpires': 'Sat, 26 Jul 1997 05:00:00 GMT', 'Cache-Control': 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0', 'Pragma': 'no-cache', 'Content-Encoding': 'gzip', 'Transfer-Encoding': 'chunked'}
[DEBUG] Response cookies: {'PHPSESSID': 'b8npf5gi12j6qa4fio1gls3m4f', 'inlabs_session_cookie': 'c4f6e88e97a74fc20bc996a25d740fdc97e9675d', 'TS016f630c': '0123313e82ce5b54b66aeaadb348db764f451376b76669ef1ce694591e7eded04015e9db5cff3478da8029a95f262f25f1bf0f3aedb5f91379eacbc7ff5673bd6485e49e45cc7345662e6f7c6280adc3a35218b31d'}
[DEBUG] ✅ INLABS login successful.
[DEBUG] Testing access to main INLABS interface...
[DEBUG] Main interface status: 200
[DEBUG] ✅ Successfully logged into INLABS interface
[DEBUG] Attempting to download DOU for date: 2025-09-13
[DEBUG] Sections to download: DO1
[DEBUG] Session cookie exists: True
[DEBUG] Cookie length: 40 chars
[DEBUG] Downloading 2025-09-13-DO1.zip...
[DEBUG] Full download URL: https://inlabs.in.gov.br/index.php?p=2025-09-13&dl=2025-09-13-DO1.zip
[DEBUG] All session cookies: PHPSESSID=b8npf5gi12j6qa4fio1gls3m4f; inlabs_session_cookie=c4f6e88e97a74fc20bc996a25d740fdc97e9675d; TS016f630c=0123313e82ce5b54b66aeaadb348db764f451376b76669ef1ce694591e7eded04015e9db5cff3478da8029a95f262f25f1bf0f3aedb5f91379eacbc7ff5673bd6485e49e45cc7345662e6f7c6280adc3a35218b31d
[DEBUG] Headers: {'Cookie': 'PHPSESSID=b8npf5gi12j6qa4fio1gls3m4f; inlabs_session_cookie=c4f6e88e97a74fc20bc996a25d740fdc97e9675d; TS016f630c=0123313e82ce5b54b66aeaadb348db764f451376b76669ef1ce694591e7eded04015e9db5cff3478da8029a95f262f25f1bf0f3aedb5f91379eacbc7ff5673bd6485e49e45cc7345662e6f7c6280adc3a35218b31d', 'origem': '736372697074', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://inlabs.in.gov.br/index.php', 'Accept': 'application/zip,_/_'}
[DEBUG] Making GET request to INLABS...
[DEBUG] Attempting direct session.get() first...
[DEBUG] Response for DO1: 200, Content-Length: 36091
[DEBUG] Content-Type: text/html; charset=utf-8
[DEBUG] First 50 bytes: b'<!DOCTYPE html>\r\n<html>\r\n<head>\r\n<title>Imprensa N'
[DEBUG] ZIP signature check for DO1: b'<!DO' (should start with PK)
[ERROR] ❌ Downloaded content for DO1 is NOT a valid ZIP file!
[ERROR] Expected: PK signature (50 4B), Got: b'<!DO'
[ERROR] This suggests INLABS returned an error page instead of a ZIP file
[DEBUG] ===== ACTUAL CONTENT RECEIVED =====
[DEBUG] <!DOCTYPE html>

<html>
<head>
<title>Imprensa Nacional - INLABS</title>
<link rel="stylesheet" href="css/bootstrap.min.css">
<script src="js/bootstrap.min.js"></script>
<link rel="icon" href="img/favicon.ico" type="image/x-icon" />
<link rel="shortcut icon" href="img/favicon.ico" type="image/x-icon" />
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
<link rel="stylesheet" href="css/font-awesome.min.css"> 
<link rel="stylesheet" href="css/styles2.css"> 
<link rel="stylesheet" href="css/styles3.css">
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=UA-149577637-4"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'UA-149577637-4');
</script>
</head><body class="navbar-normal">
<div class="container">
<div class="row">
[DEBUG] ===== END CONTENT =====
[ERROR] 🚨 INLABS returned an HTML page instead of ZIP! Trying alternative URLs...
[DEBUG] Trying alternative URL: https://inlabs.in.gov.br/files/2025-09-13-DO1.zip
[DEBUG] Alt URL status: 404
No files downloaded today.
[DEBUG] Search completed. Matches: 0, Stats: {'sections_downloaded': 0, 'zip_files_downloaded': 0, 'xml_files_processed': 0, 'total_articles_extracted': 0, 'articles_searched': 0, 'matches_found': 0, 'download_time': 3.69, 'extraction_time': 0, 'search_time': 0}

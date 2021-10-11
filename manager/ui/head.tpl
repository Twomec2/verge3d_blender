  <script>
    // global App Manager JS context
    <% import json %>var appManager = JSON.parse('${json.dumps(jsContext)}');
  </script>

  <link rel="stylesheet" type="text/css" href="/manager/css/fonts.css">
  <link rel="stylesheet" type="text/css" href="/manager/css/common.css">

  % if theme == 'dark':
    <link rel="stylesheet" type="text/css" href="/manager/css/dark.css">
  % endif

  <!-- favicons from realfavicongenerator.net -->
  <link rel="apple-touch-icon" sizes="180x180" href="/manager/img/favicons/apple-touch-icon.png">
  <link rel="icon" type="image/png" sizes="32x32" href="/manager/img/favicons/favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/manager/img/favicons/favicon-16x16.png">
  <link rel="manifest" href="/manager/img/favicons/manifest.json">
  <link rel="mask-icon" href="/manager/img/favicons/safari-pinned-tab.svg" color="#5bbad5 ">
  <meta name="theme-color" content="#ffffff ">

  <script src="/manager/js/common.js"></script>
  <script src="/manager/js/qrcode.js"></script>


<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaCreateNativeApp</%block>

<%block name="blkDialogHeader">
  Create Desktop/Mobile App Template
</%block>

<%!
  import os
%>

<%block name="blkDialogContent">
  <form action="" class="TODO" id="createNativeAppForm">

    <input type="hidden" name="app" value="${app['name']}">

    <div class="dialog-text">Template:</div>

    <div title="Create desktop application with Electron framework">
      <input type="radio" name="templateName" value="electron" checked>Desktop App (Electron)
    </div>

    <div title="Create mobile application with Apache Cordova framework">
      <input type="radio" name="templateName" value="cordova">Mobile App (Cordova)
    </div>

    <div id="targetPlatformCont" title="Download Electron binaries and produce a ready-to-use app for the target platform">
      <div class="dialog-text">Target Platform:</div>

      <select name="targetPlatform" class="target-platform">
        <option value="none" selected>None</option>
        <option value="win32-x64">Windows (64-bit)</option>
        % if os.name != 'nt':
          <option value="darwin-x64">macOS (64-bit)</option>
          <option value="mas-x64">macOS App Store (64-bit)</option>
        % endif
        <option value="linux-x64">Linux (64-bit)</option>
        <option value="win32-arm64">Windows (ARM)</option>
        % if os.name != 'nt':
          <option value="darwin-arm64">macOS (ARM)</option>
          <option value="mas-arm64">macOS App Store (ARM)</option>
        % endif
        <option value="linux-arm64">Linux (ARM)</option>
        <option value="win32-ia32">Windows (32-bit)</option>
        <option value="linux-ia32">Linux (32-bit)</option>
      </select>
    </div>

    <div class="dialog-text">App Name:</div>
    <span title="Application name"><input type="text" name="appName" value="${app['title']}" class="dialog-semi-wide-input"></span>

    <div class="dialog-text">App ID:</div>
    <span title="Application ID in reverse domain name notation"><input type="text" id="appID" name="appID" value="com.example.${app['title'].replace(' ', '')}" class="dialog-semi-wide-input"></span>

    <div class="dialog-text">App Version:</div>
    <span title="Application version"><input type="text" name="appVersion" value="0.1.0" class="dialog-semi-wide-input"></span>

    <div class="dialog-text">Description:</div>
    <span title="Application description"><input type="text" name="appDescription" value="My Awesome App" class="dialog-semi-wide-input"></span>

    <div class="dialog-text">Author Name:</div>
    <span title="Author name"><input type="text" id="authorName" name="authorName" value="John Smith" class="dialog-semi-wide-input"></span>

    <div id="authorExtended">
      <div class="dialog-text">Author Email:</div>
      <span title="Author email"><input type="text" id="authorEmail" name="authorEmail" value="author@example.com" class="dialog-semi-wide-input"></span>

      <div class="dialog-text">Author Website:</div>
      <span title="Author website URL"><input type="text" id="authorWebsite" name="authorWebsite" value="https://www.example.com" class="dialog-semi-wide-input"></span>
    </div>

    <input type="submit" value="Create App" class="button">

  </form>

  <div class="spinner-preloader-cont" id="creatingNativeAppPercentageCont">
    <div class="spinner-preloader"></div>
    <div class="dialog-text-creating-native-app">Creating the App...</div>
  </div>

</%block>

<%block name="blkDialogScript">

    function switchNativeAppDiaMode(mode) {
        if (mode == 'form') {
            createNativeAppForm.style.display = 'block';
            creatingNativeAppPercentageCont.style.display = 'none';
        } else {
            createNativeAppForm.style.display = 'none';
            creatingNativeAppPercentageCont.style.display = 'block';
        }
    }
    switchNativeAppDiaMode('form');

    diaCreateNativeAppClose.addEventListener('click', function() {
        switchNativeAppDiaMode('form');
        closeDialog('diaCreateNativeApp');
    });

    createNativeAppForm.addEventListener('submit', function(event) {
        var newAppFormData = new FormData(createNativeAppForm);

        makeRequest('/create_native_app/', newAppFormData, function(response) {
            switchNativeAppDiaMode('form');
            closeDialog('diaCreateNativeApp');

            var dia = appendDialog(response);
            openDialog(dia);
        });

        switchNativeAppDiaMode('preloader');
        event.preventDefault();
    });

    function templateChangedCb(event) {
        var template = event.currentTarget.value;

        switch (template) {
        case 'electron':
            targetPlatformCont.style.display = 'block';
            authorExtended.style.display = 'none';
            break;

        case 'cordova':
            targetPlatformCont.style.display = 'none';
            authorExtended.style.display = 'block';
            break;
        }
    };

    createNativeAppForm.templateName.forEach(function(elem) {
        elem.addEventListener('change', templateChangedCb);
    });

    templateChangedCb({currentTarget: {value: 'electron'}});

</%block>

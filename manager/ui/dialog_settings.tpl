<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaSettings</%block>

<%block name="blkDialogHeader">
  App Manager Settings
</%block>

<%block name="blkDialogContent">
  <form action="" id="settingsForm" class="settings-cont">
    <div class="dialog-text settings-text">
      <input type="checkbox" name="checkForUpdates" value="" ${'checked' if settings['checkForUpdates'] else ''} class="settings-checker">Notify about Verge3D updates
    </div>
    <div class="dialog-text settings-text">
      <input type="checkbox" name="hideStockApps" value="" ${'checked' if settings['hideStockApps'] else ''} class="settings-checker">Hide stock applications
    </div>
    <div class="dialog-text settings-text">
      <input type="checkbox" name="uploadSources" value="" ${'checked' if settings['uploadSources'] else ''} class="settings-checker">Upload app sources (models, puzzles, backups)
    </div>
    <div class="dialog-text settings-text">
      <input type="checkbox" name="externalInterface" value="" ${'checked' if settings['externalInterface'] else ''} class="settings-checker">Enable external server interface
    </div>

    <div class="dialog-text settings-text">
      Verge3D Network cache age (minutes)
      <input type="number" name="cacheMaxAge" value="${settings['cacheMaxAge']}" class="dialog-num-input">
    </div>

    <div class="dialog-text settings-text">
      External applications directory
      <input type="text" name="extAppsDirectory" value="${settings['extAppsDirectory']}" class="dialog-wide-input">
    </div>

    % if 'externalAddress' in settings:
      <div class="dialog-text settings-text">
        Local network address (copy and paste it to address bar):
        <input type="text" name="externalAddress" value="${settings['externalAddress']}" class="">
      </div>
    % endif

    <hr>

    <div style="dialog-text settings-text">
      Current Theme:

      <select name="theme" class="settings-theme">
        <option value="light" ${'selected' if settings['theme'] == 'light' else ''}>Light</option>
        <option value="dark" ${'selected' if settings['theme'] == 'dark' else ''}>Dark</option>
      </select>
    </div>

    <input type="submit" id="settingsSave" value="Apply Changes" class="button settings-button">
  </form>
</%block>

<%block name="blkDialogScript">
  diaSettingsClose.addEventListener('click', function() {
      destroyDialog('diaSettings');
  });

  settingsForm.addEventListener('submit', function(event) {

      var data = {};

      settingsForm.querySelectorAll('input').forEach(function(elem) {
          switch (elem.type) {
              case 'checkbox':
                  data[elem.name] = elem.checked;
                  break;
              case 'text':
                  data[elem.name] = elem.value;
                  break;
              case 'number':
                  data[elem.name] = Number(elem.value);
                  break;
          }
      });

      settingsForm.querySelectorAll('select').forEach(function(elem) {
          elem.querySelectorAll('option').forEach(function(elemOpt) {
              if (elemOpt.selected)
                  data[elem.name] = elemOpt.value;
          });
      });

      var jsonData = JSON.stringify(data);

      makeRequest('/settings/save', jsonData, function(response) {

          makeRequest('/restart');

          // wait some time for server to restart
          setTimeout(function() {
              destroyDialog('diaSettings');
              document.location.reload(true);
          }, 500);
      });

      event.preventDefault();
  });

  focusElem('settingsSave');
</%block>

<div class="toolbar-app">
  % if app['puzzles']:
    % if app['puzzles']['logicExists']:
      <a href="${app['puzzles']['url']}" target="_blank" class="toolbar-app-icon toolbar-app-icon-puzzles-edit" title="Edit Puzzles"></a>
    % else:
      <a href="${app['puzzles']['url']}" target="_blank" class="toolbar-app-icon toolbar-app-icon-puzzles-new" title="Create Puzzles"></a>
    % endif
  % endif

  <a href="javascript:void(0);" onclick=openFile("${app['url']}") class="toolbar-app-icon toolbar-app-icon-open-folder" title="Open app folder"></a>

  <a href="javascript:void(0);" onclick=publishApp("${app['name'] | u}",false) class="toolbar-app-icon toolbar-app-icon-publish-dir" title="Publish on the Web using Verge3D Network"></a>

  <a href="javascript:void(0);" onclick=publishApp("${app['name'] | u}",true) class="toolbar-app-icon toolbar-app-icon-publish-zip" title="Publish project ZIP using Verge3D Network"></a>

  <a href="javascript:void(0);" onclick=createNativeApp("${app['name'] | u}") class="toolbar-app-icon toolbar-app-icon-create-native-app" title="Create desktop/mobile application template"></a>

  <a href="javascript:void(0);" onclick=deleteApp("${app['name'] | u}") class="toolbar-app-icon toolbar-app-icon-delete" title="Delete the app"></a>

  % if app['needsUpdate']:
    <a href="javascript:void(0);" onclick=updateApp("${app['name'] | u}",this) class="toolbar-app-icon toolbar-app-icon-update" title="Update application"></a>
  % endif

</div>


<%include file="dialog_create_native_app.tpl"/>

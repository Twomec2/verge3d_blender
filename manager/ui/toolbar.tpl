<div class="toolbar">
  <a href="/" class="toolbar-icon toolbar-icon-home" title="Home Page"></a>
  <a href="javascript:void(0);" onclick=openDialog("diaNewApp") class="toolbar-icon toolbar-icon-new-app" title="Create new App"></a>
  <a href="javascript:void(0);" onclick=openSettingsDialog(true) class="toolbar-icon toolbar-icon-templates" title="Manage App Templates"></a>
  <a href="javascript:void(0);" onclick=openSettingsDialog(false) class="toolbar-icon toolbar-icon-settings" title="Change App Manager Settings"></a>
  <a href="/storage/net/?req=status" class="toolbar-icon toolbar-icon-network" title="Open Verge3D Network directory"></a>
  <a href="javascript:void(0);" onclick=openDialog("diaLicense") class="toolbar-icon toolbar-icon-license" title="Open Verge3D Licensing Manager">
    % if not licenseInfo['maintenance']:
      <div class="toolbar-icon-dot-red"></div>
    % endif
  </a>
  <a href="javascript:void(0);" onclick=openDialog("diaHelp") class="toolbar-icon toolbar-icon-help" title="Get Help"></a>
  <a href="javascript:void(0);" onclick=openDialog("diaAbout") class="toolbar-icon toolbar-icon-about" title="Open About Dialog"><div class="toolbar-icon-dot-orange hidden" id="newVersionAvailDot"></div></a>
</div>

<script>
    setActiveToolbar();
</script>

<%include file="dialog_new_app.tpl"/>
<%include file="dialog_license.tpl"/>
<%include file="dialog_license_key.tpl"/>
<%include file="dialog_help.tpl"/>
<%include file="dialog_about.tpl"/>

